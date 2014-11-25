"""epoll loop backend

This module is deprecated and will be removed once pyuv_cffi is fully implemented.
"""
import logging
import heapq
import select
import errno
import greenlet

from .. import patcher
from ..const import READ, WRITE
from ..support import compat, get_errno
from . import abc
from .watchers import PollFdListener
from .timer import Timer

compat.patch()

log = logging.getLogger('guv')

epoll = patcher.original('select').epoll
time = patcher.original('time')
queue = patcher.original('queue')

EXC_MASK = select.POLLERR | select.POLLHUP
READ_MASK = select.POLLIN | select.POLLPRI
WRITE_MASK = select.POLLOUT
SYSTEM_EXCEPTIONS = (KeyboardInterrupt, SystemExit)


class Hub(abc.AbstractHub):
    def __init__(self):
        super().__init__()
        self.Listener = PollFdListener
        self.stopping = False
        self.running = False
        self.timers = []  # heap of timers
        self.callbacks = []  # list of callbacks
        self.epoll = epoll()

    def _fire_timers(self, up_to):
        """Fire timers scheduled to be fire before `up_to`

        :param float up_to: timers scheduled to be fired before this specified absolute time
            (seconds) will be fired
        """
        timers = self.timers

        while timers:
            timer = timers[0]

            if timer.called:
                heapq.heappop(timers)
                continue

            if timer > up_to:
                break

            if timer.absolute_time > time.monotonic():
                break

            # call the timer to call the callback
            timer()

            heapq.heappop(timers)

    def _time_until_next_timer(self):
        """Get number of seconds until next timer has to be fired
        """
        if not self.timers:
            return None

        return self.timers[0].absolute_time - time.monotonic()

    def _remove_descriptor(self, fd):
        #: :type: dict[fd, listener]
        readers = self.listeners[READ]
        #: :type: dict[fd, listener]
        writers = self.listeners[WRITE]

        if fd in readers:
            del readers[fd]

        if fd in writers:
            del writers[fd]

    def _fire_callbacks(self):
        """Fire immediate callbacks
        """
        callbacks = self.callbacks
        self.callbacks = []
        for cb, args, kwargs in callbacks:
            cb(*args, **kwargs)

    def run(self):
        assert self is greenlet.getcurrent()

        if self.stopping:
            return

        if self.running:
            raise RuntimeError("The hub's runloop is already running")

        log.debug('Start runloop')
        try:
            self.running = True
            self.stopping = False
            self._run_loop()
        finally:
            self.running = False
            self.stopping = False

    def _run_loop(self):
        try:
            while True:
                self._fire_timers(time.monotonic())

                # call scheduled callbacks (made via spawn(), etc.)
                self._fire_callbacks()

                # poll for I/O and call I/O callbacks
                self._poll()

        except KeyboardInterrupt:
            self.abort()
            self.greenlet.parent.throw(KeyboardInterrupt)

    def _poll(self):
        # get time until next timer, or 60 seconds if there are no timers
        sleep_time = self._time_until_next_timer()
        if sleep_time is None:
            sleep_time = 60

        readers = self.listeners[READ]
        writers = self.listeners[WRITE]

        # sleep if no I/O listeners are registered
        if not (readers or writers):
            if sleep_time:
                time.sleep(sleep_time)
            return

        # call epoll()
        try:
            poll_result = self.epoll.poll(sleep_time)
        except (IOError, select.error) as e:
            if get_errno(e) == errno.EINTR:
                return
            raise

        # build a set of listeners to process from the results of epoll()
        listeners = set()

        for fd, event in poll_result:
            if event & READ_MASK:
                listeners.add(readers[fd])
            if event & WRITE_MASK:
                listeners.add(writers[fd])
            if event & select.POLLNVAL:
                self._remove_descriptor(fd)
                continue
            if event & EXC_MASK:
                if fd in readers:
                    listeners.add(readers[fd])
                if fd in writers:
                    listeners.add(writers[fd])

        # call listener callbacks
        for listener in listeners:
            try:
                listener.cb()
            except SYSTEM_EXCEPTIONS:
                raise

    def abort(self):
        print()
        log.debug('Abort loop')
        if self.running:
            self.stopping = True

    def schedule_call_now(self, cb, *args, **kwargs):
        self.callbacks.append((cb, args, kwargs))

    def schedule_call_global(self, seconds, cb, *args, **kwargs):
        timer = Timer(seconds, cb, *args, **kwargs)
        heapq.heappush(self.timers, timer)

        return timer

    def add(self, evtype, fd, cb, tb):
        """Signals an intent to or write a particular file descriptor

        Signature of Callable cb: cb(fd: int)

        :param str evtype: either the constant READ or WRITE
        :param int fd: file number of the file of interest
        :param cb: callback which will be called when the file is ready for reading/writing
        :param tb: throwback used to signal (into the greenlet) that the file was closed
        :return: listener
        :rtype: self.Listener
        """
        # create and add listener object
        listener = PollFdListener(evtype, fd, cb)
        self._add_listener(listener)

        # register the fd with the epoll object
        flags = 0
        if evtype == READ:
            flags = select.EPOLLIN | select.EPOLLPRI
        elif evtype == WRITE:
            flags = select.EPOLLOUT

        self.epoll.register(fd, flags)

        return listener

    def remove(self, listener):
        """Remove listener

        :param listener: listener to remove
        :type listener: self.Listener
        """
        super()._remove_listener(listener)
        # log.debug('call w.handle.stop(), fd: {}'.format(listener.handle.fileno()))

        # initiate correct cleanup sequence (these three statements are critical)
        self.epoll.unregister(listener.fd)
        # self.debug()
