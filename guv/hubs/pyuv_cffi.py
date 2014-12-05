import signal
import logging
import greenlet
import sys

from guv.hubs.abc import AbstractListener
import pyuv_cffi
from . import abc

log = logging.getLogger('guv')


class UvFdListener(AbstractListener):
    def __init__(self, evtype, fd, handle):
        """
        :param handle: pyuv_cffi Handle object
        :type handle: pyuv_cffi.Handle
        """
        super().__init__(evtype, fd)
        self.handle = handle


class Timer(abc.AbstractTimer):
    def __init__(self, timer_handle):
        """
        :type timer_handle: pyuv.Timer
        """
        self.timer_handle = timer_handle

    def cancel(self):
        if not self.timer_handle.closed:
            self.timer_handle.stop()
            self.timer_handle.close()


class Hub(abc.AbstractHub):
    def __init__(self):
        super().__init__()
        self.Listener = UvFdListener
        self.stopping = False
        self.running = False
        self.callbacks = []

        #: :type: pyuv.Loop
        self.loop = pyuv_cffi.Loop.default_loop()

        sig = pyuv_cffi.Signal(self.loop)
        sig.start(self.signal_received, signal.SIGINT)

        # set up a uv_idle handle to help make sure that non-io callbacks get called quickly
        self.idle_h = pyuv_cffi.Idle(self.loop)

        # fire immediate callbacks every loop iteration
        self.prepare = pyuv_cffi.Prepare(self.loop)
        self.prepare.start(self._fire_callbacks)

    def _idle_cb(self, idle_h):
        idle_h.stop()

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
            self.loop.run(pyuv_cffi.UV_RUN_DEFAULT)
        finally:
            self.running = False
            self.stopping = False

    def abort(self):
        print()
        log.debug('Abort loop')
        if self.running:
            self.stopping = True

        self.loop.stop()

    def _fire_callbacks(self, prepare_handle):
        """Fire immediate callbacks
        """
        callbacks = self.callbacks
        self.callbacks = []
        for cb, args, kwargs in callbacks:
            try:
                cb(*args, **kwargs)
            except:
                self._squelch_exception(sys.exc_info())

        # Check if more callbacks have been scheduled. Since these may be non-io callbacks (such
        # as calls to `gyield()` or `schedule_call_now()`, start a uv_async_t handle so that libuv
        # can do a zero-timeout poll and quickly start another loop iteration.
        if self.callbacks:
            self.idle_h.start(self._idle_cb)

    def schedule_call_now(self, cb, *args, **kwargs):
        self.callbacks.append((cb, args, kwargs))

    def schedule_call_global(self, seconds, cb, *args, **kwargs):
        def timer_callback(timer_handle):
            try:
                cb(*args, **kwargs)
            except:
                self._squelch_exception(sys.exc_info())

            # required for cleanup
            if not timer_handle.closed:
                timer_handle.stop()
                timer_handle.close()

        timer_handle = pyuv_cffi.Timer(self.loop)
        timer_handle.start(timer_callback, seconds, 0)

        return Timer(timer_handle)

    def add(self, evtype, fd, cb, tb, cb_args=()):
        poll_h = pyuv_cffi.Poll(self.loop, fd)
        listener = UvFdListener(evtype, fd, poll_h)

        def poll_cb(poll_h, events, errno):
            """Read callback for pyuv

            pyuv requires a callback with this signature

            :type poll_h: pyuv.Poll
            :type events: int
            :type errno: int
            """
            try:
                cb(*cb_args)
            except:
                self._squelch_exception(sys.exc_info())

                try:
                    self.remove(listener)
                except Exception as e:
                    sys.stderr.write('Exception while removing listener: {}\n'.format(e))
                    sys.stderr.flush()

        self._add_listener(listener)

        # start the pyuv Poll object
        # note that UV_READABLE and UV_WRITABLE correspond to const.READ and const.WRITE
        poll_h.start(evtype, poll_cb)

        # self.debug()
        return listener

    def remove(self, listener):
        """Remove listener

        :param listener: listener to remove
        :type listener: self.Listener
        """
        super()._remove_listener(listener)
        # log.debug('call w.handle.stop(), fd: {}'.format(listener.handle.fileno()))

        # initiate correct cleanup sequence (these three statements are critical)
        listener.handle.ref = False
        listener.handle.stop()
        listener.handle.close()
        listener.handle = None
        # self.debug()

    def signal_received(self, sig_handle, signo):
        """Signal handler for pyuv.Signal

        pyuv.Signal requies a callback with the following signature::

            Callable(signal_handle, signal_num)

        :type sig_handle: pyuv.Signal
        :type signo: int
        """
        if signo == signal.SIGINT:
            sig_handle.stop()
            self.abort()
            self.parent.throw(KeyboardInterrupt)
