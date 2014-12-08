import greenlet
import sys
from collections import deque

from . import hubs
from .timeout import Timeout
from .hubs import get_hub

__all__ = ['Event', 'TEvent', 'AsyncResult']


class _NONE:
    __slots__ = []

    def __repr__(self):
        return '<_NONE>'


_NONE = _NONE()


class Event:
    """An abstraction where an arbitrary number of greenlets can wait for one event from another

    Events are similar to a Queue that can only hold one item, but differ
    in two important ways:

    1. Calling :meth:`send` never unschedules the current GreenThread
    2. :meth:`send` can only be called once; create a new event to send again.

    They are good for communicating results between greenlets, and are the basis for how
    :meth:`GreenThread.wait() <guv.GreenThread.GreenThread.wait>` is implemented.

    >>> from guv import event
    >>> import guv
    >>> evt = event.Event()
    >>> def baz(b):
    ...     evt.send(b + 1)
    ...
    >>> _ = guv.spawn_n(baz, 3)
    >>> evt.wait()
    4
    """
    _result = None
    _exc = None

    def __init__(self):
        self._waiters = set()
        self.reset()

    def __str__(self):
        params = (self.__class__.__name__, hex(id(self)),
                  self._result, self._exc, len(self._waiters))
        return '<%s at %s result=%r _exc=%r _waiters[%d]>' % params

    def reset(self):
        # this is kind of a misfeature and doesn't work perfectly well,
        # it's better to create a new event rather than reset an old one
        # removing documentation so that we don't get new use cases for it
        assert self._result is not _NONE, 'Trying to re-reset() a fresh event.'
        self._result = _NONE
        self._exc = None

    def ready(self):
        """Return true if the :meth:`wait` call will return immediately

        Used to avoid waiting for things that might take a while to time out. For example, you can
        put a bunch of events into a list, and then visit them all repeatedly, calling :meth:`ready`
        until one returns ``True``, and then you can :meth:`wait` on that one
        """
        return self._result is not _NONE

    def has_exception(self):
        return self._exc is not None

    def has_result(self):
        return self._result is not _NONE and self._exc is None

    def poll(self, notready=None):
        if self.ready():
            return self.wait()
        return notready

    # QQQ make it return tuple (type, value, tb) instead of raising
    # because
    # 1) "poll" does not imply raising
    # 2) it's better not to screw up caller's sys.exc_info() by default
    #    (e.g. if caller wants to calls the function in except or finally)
    def poll_exception(self, notready=None):
        if self.has_exception():
            return self.wait()
        return notready

    def poll_result(self, notready=None):
        if self.has_result():
            return self.wait()
        return notready

    def wait(self):
        """Wait until another greenthread calls :meth:`send`

        Returns the value the other coroutine passed to :meth:`send`.

        Returns immediately if the event has already occurred.

        >>> from guv import event
        >>> import guv
        >>> evt = event.Event()
        >>> def wait_on():
        ...    retval = evt.wait()
        ...    print("waited for {0}".format(retval))
        >>> _ = guv.spawn(wait_on)
        >>> evt.send('result')
        >>> guv.sleep(0)
        waited for result

        >>> evt.wait()
        'result'
        """
        current = greenlet.getcurrent()
        if self._result is _NONE:
            self._waiters.add(current)
            try:
                return hubs.get_hub().switch()
            finally:
                self._waiters.discard(current)
        if self._exc is not None:
            current.throw(*self._exc)
        return self._result

    def send(self, result=None, exc=None):
        """Make arrangements for the waiters to be woken with the result and then return immediately
        to the parent

        >>> from guv import event
        >>> import guv
        >>> evt = event.Event()
        >>> def waiter():
        ...     print('about to wait')
        ...     result = evt.wait()
        ...     print('waited for {0}'.format(result))
        >>> _ = guv.spawn(waiter)
        >>> guv.sleep(0)
        about to wait
        >>> evt.send('a')
        >>> guv.sleep(0)
        waited for a

        It is an error to call :meth:`send` multiple times on the same event.

        >>> evt.send('whoops')
        Traceback (most recent call last):
        ...
        AssertionError: Trying to re-send() an already-triggered event.

        Use :meth:`reset` between :meth:`send` s to reuse an event object.
        """
        assert self._result is _NONE, 'Trying to re-send() an already-triggered event.'
        self._result = result
        if exc is not None and not isinstance(exc, tuple):
            exc = (exc, )
        self._exc = exc
        hub = hubs.get_hub()
        for waiter in self._waiters:
            hub.schedule_call_global(
                0, self._do_send, self._result, self._exc, waiter)

    def _do_send(self, result, exc, waiter):
        if waiter in self._waiters:
            if exc is None:
                waiter.switch(result)
            else:
                waiter.throw(*exc)

    def send_exception(self, *args):
        """Same as :meth:`send`, but sends an exception to waiters.

        The arguments to send_exception are the same as the arguments
        to ``raise``.  If a single exception object is passed in, it
        will be re-raised when :meth:`wait` is called, generating a
        new stacktrace.

           >>> from guv import event
           >>> evt = event.Event()
           >>> evt.send_exception(RuntimeError())
           >>> evt.wait()
           Traceback (most recent call last):
             File "<stdin>", line 1, in <module>
             File "guv/event.py", line 120, in wait
               current.throw(*self._exc)
           RuntimeError

        If it's important to preserve the entire original stack trace,
        you must pass in the entire :func:`sys.exc_info` tuple.

           >>> import sys
           >>> evt = event.Event()
           >>> try:
           ...     raise RuntimeError()
           ... except RuntimeError:
           ...     evt.send_exception(*sys.exc_info())
           ...
           >>> evt.wait()
           Traceback (most recent call last):
             File "<stdin>", line 1, in <module>
             File "guv/event.py", line 120, in wait
               current.throw(*self._exc)
             File "<stdin>", line 2, in <module>
           RuntimeError

        Note that doing so stores a traceback object directly on the
        Event object, which may cause reference cycles. See the
        :func:`sys.exc_info` documentation.
        """
        # the arguments and the same as for greenlet.throw
        return self.send(None, args)


class TEvent:
    """A synchronization primitive that allows one greenlet to wake up one or more others. It has
    the same interface as :class:`threading.Event` but works across greenlets.

    An event object manages an internal flag that can be set to true with the :meth:`set` method and
    reset to false with the :meth:`clear` method. The :meth:`wait` method blocks until the flag is
    true.
    """

    def __init__(self):
        self._links = set()
        self._todo = set()
        self._flag = False
        self.hub = get_hub()
        self._notifier = None

    def __str__(self):
        return '<%s %s _links[%s]>' % (
            self.__class__.__name__, (self._flag and 'set') or 'clear', len(self._links))

    def is_set(self):
        """Return true if and only if the internal flag is true."""
        return self._flag

    isSet = is_set  # makes it a better drop-in replacement for threading.Event
    ready = is_set  # makes it compatible with AsyncResult and Greenlet (for example in wait())

    def set(self):
        """Set the internal flag to true. All greenlets waiting for it to become true are awakened.
        Greenlets that call :meth:`wait` once the flag is true will not block at all.
        """
        self._flag = True
        self._todo.update(self._links)
        if self._todo and not self._notifier:
            self._notifier = True
            self.hub.schedule_call_now(self._notify_links)

    def clear(self):
        """Reset the internal flag to false.
        Subsequently, threads calling :meth:`wait`
        will block until :meth:`set` is called to set the internal flag to true again.
        """
        self._flag = False

    def wait(self, timeout=None):
        """Block until the internal flag is true.
        If the internal flag is true on entry, return immediately. Otherwise,
        block until another thread calls :meth:`set` to set the flag to true,
        or until the optional timeout occurs.

        When the *timeout* argument is present and not ``None``, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        Return the value of the internal flag (``True`` or ``False``).
        """
        if self._flag:
            return self._flag
        else:
            switch = greenlet.getcurrent().switch
            self.rawlink(switch)
            try:
                timer = Timeout(timeout)
                try:
                    try:
                        self.hub.switch()
                        # assert result is self, 'Invalid switch into Event.wait(): %r' % (result, )
                    except Timeout as ex:
                        if ex is not timer:
                            raise
                finally:
                    timer.cancel()
            finally:
                self.unlink(switch)
        return self._flag

    def rawlink(self, callback):
        """Register a callback to call when the internal flag is set to true

        *callback* will be called in the :class:`Hub <gevent.hub.Hub>`, so it must not use blocking
        *gevent API. callback* will be passed one argument: this instance.
        """
        if not callable(callback):
            raise TypeError('Expected callable: %r' % (callback, ))
        self._links.add(callback)
        if self._flag and not self._notifier:
            self._todo.add(callback)
            self._notifier = True
            self.hub.schedule_call_now(self._notify_links)

    def unlink(self, callback):
        """Remove the callback set by :meth:`rawlink`"""
        try:
            self._links.remove(callback)
        except ValueError:
            pass

    def _notify_links(self):
        while self._todo:
            link = self._todo.pop()
            if link in self._links:
                # check that link was not notified yet and was not removed by the client
                try:
                    link(self)
                except:
                    self.hub.handle_error((link, self), *sys.exc_info())

    def _reset_internal_locks(self):
        """For compatibility with threading.Event (only in case of patch_all(Event=True),
        by default Event is not patched)

        Exception AttributeError: AttributeError("'Event' object has no attribute
        '_reset_internal_locks'",)
        in <module 'threading' from '/usr/lib/python2.7/threading.pyc'> ignored
        """
        pass


class AsyncResult:
    """A one-time event that stores a value or an exception

    Like :class:`Event` it wakes up all the waiters when :meth:`set` or :meth:`set_exception` method
    is called. Waiters may receive the passed value or exception by calling :meth:`get` method
    instead of :meth:`wait`. An :class:`AsyncResult` instance cannot be reset.

    To pass a value call :meth:`set`. Calls to :meth:`get` (those that currently blocking as well as
    those made in the future) will return the value:

        >>> result = AsyncResult()
        >>> result.set(100)
        >>> result.get()
        100

    To pass an exception call :meth:`set_exception`. This will cause :meth:`get` to raise that
    exception:

        >>> result = AsyncResult()
        >>> result.set_exception(RuntimeError('failure'))
        >>> result.get()
        Traceback (most recent call last):
         ...
        RuntimeError: failure

    :class:`AsyncResult` implements :meth:`__call__` and thus can be used as :meth:`link` target:

        >>> import gevent
        >>> result = AsyncResult()
        >>> gevent.spawn(lambda : 1/0).link(result)
        >>> try:
        ...     result.get()
        ... except ZeroDivisionError:
        ...     print 'ZeroDivisionError'
        ZeroDivisionError
    """

    def __init__(self):
        self._links = deque()
        self.value = None
        self._exception = _NONE
        self.hub = get_hub()
        self._notifier = None

    def __str__(self):
        result = '<%s ' % (self.__class__.__name__, )
        if self.value is not None or self._exception is not _NONE:
            result += 'value=%r ' % self.value
        if self._exception is not None and self._exception is not _NONE:
            result += 'exception=%r ' % self._exception
        if self._exception is _NONE:
            result += 'unset '
        return result + ' _links[%s]>' % len(self._links)

    def ready(self):
        """Return true if and only if it holds a value or an exception"""
        return self._exception is not _NONE

    def successful(self):
        """Return true if and only if it is ready and holds a value"""
        return self._exception is None

    @property
    def exception(self):
        """Holds the exception instance passed to :meth:`set_exception` if :meth:`set_exception`
        was called.
        Otherwise ``None``."""
        if self._exception is not _NONE:
            return self._exception

    def set(self, value=None):
        """Store the value. Wake up the waiters.

        All greenlets blocking on :meth:`get` or :meth:`wait` are woken up.
        Sequential calls to :meth:`wait` and :meth:`get` will not block at all.
        """
        self.value = value
        self._exception = None
        if self._links and not self._notifier:
            self._notifier = self.hub.loop.run_callback(self._notify_links)

    def set_exception(self, exception):
        """Store the exception. Wake up the waiters.

        All greenlets blocking on :meth:`get` or :meth:`wait` are woken up.
        Sequential calls to :meth:`wait` and :meth:`get` will not block at all.
        """
        self._exception = exception
        if self._links and not self._notifier:
            self._notifier = self.hub.loop.run_callback(self._notify_links)

    def get(self, block=True, timeout=None):
        """Return the stored value or raise the exception.

        If this instance already holds a value / an exception, return / raise it immediatelly.
        Otherwise, block until another greenlet calls :meth:`set` or :meth:`set_exception` or
        until the optional timeout occurs.

        When the *timeout* argument is present and not ``None``, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).
        """
        if self._exception is not _NONE:
            if self._exception is None:
                return self.value
            raise self._exception
        elif block:
            switch = greenlet.getcurrent().switch
            self.rawlink(switch)
            try:
                timer = Timeout(timeout)
                try:
                    result = self.hub.switch()
                    assert result is self, 'Invalid switch into AsyncResult.get(): %r' % (result, )
                finally:
                    timer.cancel()
            except:
                self.unlink(switch)
                raise
            if self._exception is None:
                return self.value
            raise self._exception
        else:
            raise Timeout

    def get_nowait(self):
        """Return the value or raise the exception without blocking.

        If nothing is available, raise :class:`gevent.Timeout` immediatelly.
        """
        return self.get(block=False)

    def wait(self, timeout=None):
        """Block until the instance is ready.

        If this instance already holds a value / an exception, return immediatelly.
        Otherwise, block until another thread calls :meth:`set` or :meth:`set_exception` or
        until the optional timeout occurs.

        When the *timeout* argument is present and not ``None``, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        Return :attr:`value`.
        """
        if self._exception is not _NONE:
            return self.value
        else:
            switch = greenlet.getcurrent().switch
            self.rawlink(switch)
            try:
                timer = Timeout(timeout)
                try:
                    result = self.hub.switch()
                    assert result is self, 'Invalid switch into AsyncResult.wait(): %r' % (result, )
                finally:
                    timer.cancel()
            except Timeout as exc:
                self.unlink(switch)
                if exc is not timer:
                    raise
            except:
                self.unlink(switch)
                raise
                # not calling unlink() in non-exception case, because if switch()
                # finished normally, link was already removed in _notify_links
        return self.value

    def _notify_links(self):
        while self._links:
            link = self._links.popleft()
            try:
                link(self)
            except:
                self.hub.handle_error((link, self), *sys.exc_info())

    def rawlink(self, callback):
        """Register a callback to call when a value or an exception is set.

        *callback* will be called in the :class:`Hub <gevent.hub.Hub>`, so it must not use
        blocking gevent API.
        *callback* will be passed one argument: this instance.
        """
        if not callable(callback):
            raise TypeError('Expected callable: %r' % (callback, ))
        self._links.append(callback)
        if self.ready() and not self._notifier:
            self._notifier = self.hub.loop.run_callback(self._notify_links)

    def unlink(self, callback):
        """Remove the callback set by :meth:`rawlink`"""
        try:
            self._links.remove(callback)
        except ValueError:
            pass

    # link protocol
    def __call__(self, source):
        if source.successful():
            self.set(source.value)
        else:
            self.set_exception(source.exception)
