import greenlet

from .hub import get_hub
from ..timeout import Timeout

__all__ = ['gyield', 'trampoline']


def gyield(switch_back=True):
    """Yield to other greenlets

    This is a cooperative yield which suspends the current greenlet and allows other greenlets to
    run by switching to the hub.

    - If `switch_back` is True (default), the current greenlet is resumed at the beginning of the
      next event loop iteration, before the loop polls for I/O and calls any I/O callbacks. This
      is the intended use for this function the vast majority of the time.
    - If `switch_back` is False, the hub will will never resume the current greenlet (use with
      caution). This is mainly useful for situations where other greenlets (not the hub) are
      responsible for switching back to this greenlet. An example is the Event class,
      where waiters are switched to when the event is ready.

    :param bool switch_back: automatically switch back to this greenlet on the next event loop cycle
    """
    current = greenlet.getcurrent()
    hub = get_hub()
    if switch_back:
        hub.schedule_call_now(current.switch)
    hub.switch()


def trampoline(fd, evtype, timeout=None, timeout_exc=Timeout):
    """Jump from the current greenlet to the hub and wait until the given file descriptor is ready
    for I/O, or the specified timeout elapses

    If the specified `timeout` elapses before the socket is ready to read or write, `timeout_exc`
    will be raised instead of :func:`trampoline()` returning normally.

    When the specified file descriptor is ready for I/O, the hub internally calls the callback to
    switch back to the current (this) greenlet.

    Conditions:

    - must not be called from the hub greenlet (can be called from any other greenlet)
    - `evtype` must be either :attr:`~guv.const.READ` or :attr:`~guv.const.WRITE` (not possible to
      watch for  both  simultaneously)

    :param int fd: file descriptor
    :param int evtype: either the constant :attr:`~guv.const.READ` or :attr:`~guv.const.WRITE`
    :param float timeout: (optional) maximum time to wait in seconds
    :param Exception timeout_exc: (optional) timeout Exception class
    """
    #: :type: AbstractHub
    hub = get_hub()
    current = greenlet.getcurrent()

    assert hub is not current, 'do not call blocking functions from the mainloop'
    assert isinstance(fd, int)

    timer = None
    if timeout is not None:
        def _timeout(exc):
            # timeout has passed
            current.throw(exc)

        timer = hub.schedule_call_global(timeout, _timeout, timeout_exc)

    try:
        # add a watcher for this file descriptor
        listener = hub.add(evtype, fd, current.switch, current.throw)

        # switch to the hub
        try:
            return hub.switch()
        finally:
            # log.debug('(trampoline finally) remove listener for fd: {}'.format(fd))
            hub.remove(listener)
    finally:
        if timer is not None:
            timer.cancel()
