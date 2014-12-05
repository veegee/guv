from abc import ABCMeta, abstractmethod
import greenlet
import sys
import traceback
from greenlet import GreenletExit

from ..const import READ, WRITE
from ..exceptions import SYSTEM_ERROR

NOT_ERROR = (GreenletExit, SystemExit)


class AbstractTimer(metaclass=ABCMeta):
    """Timer interface

    This is required for anything depending on this interface, such as :func:`hubs.trampoline`.
    """

    @abstractmethod
    def cancel(self):
        """Cancel the timer
        """
        pass


class AbstractListener(metaclass=ABCMeta):
    def __init__(self, evtype, fd):
        """
        :param str evtype: the constant hubs.READ or hubs.WRITE
        :param int fd: fileno
        """
        assert evtype in [READ, WRITE]
        self.evtype = evtype
        self.fd = fd
        self.greenlet = greenlet.getcurrent()

    def __repr__(self):
        return '{0}({1.evtype}, {1.fd})'.format(type(self).__name__, self)

    __str__ = __repr__


class AbstractHub(greenlet.greenlet, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()
        self.listeners = {READ: {}, WRITE: {}}
        self.Listener = AbstractListener
        self.stopping = False

        self._debug_exceptions = True

    @abstractmethod
    def run(self, *args, **kwargs):
        """Run event loop
        """

    @abstractmethod
    def abort(self):
        """Stop the runloop
        """
        pass

    @abstractmethod
    def schedule_call_now(self, cb, *args, **kwargs):
        """Schedule a callable to be called on the next event loop iteration

        This is faster than calling :meth:`schedule_call_global(0, ...)`

        :param Callable cb: callback to call after timer fires
        :param args: positional arguments to pass to the callback
        :param kwargs: keyword arguments to pass to the callback
        """
        pass

    @abstractmethod
    def schedule_call_global(self, seconds, cb, *args, **kwargs):
        """Schedule a callable to be called after 'seconds' seconds have elapsed. The timer will NOT
        be canceled if the current greenlet has exited before the timer fires.

        :param float seconds: number of seconds to wait
        :param Callable cb: callback to call after timer fires
        :param args: positional arguments to pass to the callback
        :param kwargs: keyword arguments to pass to the callback
        :return: timer object that can be cancelled
        :rtype: hubs.abc.Timer
        """
        pass

    @abstractmethod
    def add(self, evtype, fd, cb, tb, cb_args=()):
        """Signal the hub to watch the given file descriptor for an I/O event

        When the file descriptor is ready for the specified I/O event type, `cb` is called with
        the specified `cb_args`.

        :param int evtype: either the constant READ or WRITE
        :param int fd: file number of the file of interest
        :param cb: callback which will be called when the file is ready for reading/writing
        :param tb: throwback used to signal (into the greenlet) that the file was closed
        :param tuple cb_args: (optional) callback positional arguments
        :return: listener
        :rtype: self.Listener
        """
        pass

    @abstractmethod
    def remove(self, listener):
        """Remove listener

        This method safely stops and removes the listener, as well as performs any necessary
        cleanup related to the listener.

        :param listener: listener to remove
        :type listener: self.Listener
        """
        pass

    def switch(self):
        """Switch to the hub greenlet
        """
        assert greenlet.getcurrent() is not self, 'Cannot switch to the hub from the hub'
        return super().switch()

    def notify_opened(self, fd):
        """Mark the specified file descriptor as recently opened

        When the OS returns a file descriptor from an `open()` (or something similar), this may be
        the only indication we have that the FD has been closed and then recycled. We let the hub
        know that the old file descriptor is dead; any stuck listeners will be disabled and notified
        in turn.

        :param int fd: file descriptor
        :return: True if found else false
        """
        found = False

        # remove any existing listeners for this file descriptor
        for bucket in self.listeners.values():
            if fd in bucket:
                found = True
                listener = bucket[fd]
                self.remove(listener)

        return found

    def _add_listener(self, listener):
        """Add listener to internal dictionary

        :type listener: abc.AbstractListener
        :raise RuntimeError: if attempting to add multiple listeners with the same `evtype` and `fd`
        """
        evtype = listener.evtype
        fd = listener.fd

        bucket = self.listeners[evtype]
        if fd in bucket:
            raise RuntimeError('Multiple {evtype} on {fd} not supported'
                               .format(evtype=evtype, fd=fd))
        else:
            bucket[fd] = listener

    def _remove_listener(self, listener):
        """Remove listener

        :param listener: listener to remove
        :type listener: self.Listener
        """
        self.listeners[listener.evtype][listener.fd] = None
        del self.listeners[listener.evtype][listener.fd]

    def _squelch_exception(self, exc_info):
        if self._debug_exceptions and not issubclass(exc_info[0], NOT_ERROR):
            traceback.print_exception(*exc_info)
            sys.stderr.flush()

        if issubclass(exc_info[0], SYSTEM_ERROR):
            self._handle_system_error(exc_info)

    def _handle_system_error(self, exc_info):
        current = greenlet.getcurrent()
        if current is self or current is self.parent:
            self.parent.throw(*exc_info)
