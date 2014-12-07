from collections import deque
import sys
import greenlet

from . import event, hubs
from .support import reraise

__all__ = ['sleep', 'spawn', 'spawn_n', 'kill', 'spawn_after', 'GreenThread']


def sleep(seconds=0):
    """Yield control to the hub until at least `seconds` have elapsed

    :param float seconds: time to sleep for
    """
    hub = hubs.get_hub()
    current = greenlet.getcurrent()
    assert hub is not current, 'do not call blocking functions from the hub'
    timer = hub.schedule_call_global(seconds, current.switch)
    try:
        hub.switch()
    finally:
        timer.cancel()


def spawn_n(func, *args, **kwargs):
    """Spawn a greenlet

    Execution control returns immediately to the caller; the created greenlet is scheduled to be run
    at the start of the next event loop iteration, after other scheduled greenlets, but before
    greenlets waiting for I/O events.

    This is faster than :func:`spawn`, but it is not possible to retrieve the return value of
    the greenlet, or whether it raised any exceptions. It is fastest if there are no keyword
    arguments.

    If an exception is raised in the function, a stack trace is printed; the print can be
    disabled by calling :func:`guv.debug.hub_exceptions` with False.

    :return: greenlet object
    :rtype: greenlet.greenlet
    """
    hub = hubs.get_hub()
    g = greenlet.greenlet(func, parent=hub)
    hub.schedule_call_now(g.switch, *args, **kwargs)
    return g


def spawn(func, *args, **kwargs):
    """Spawn a GreenThread

    Execution control returns immediately to the caller; the created GreenThread is scheduled to
    be run at the start of the next event loop iteration, after other scheduled greenlets,
    but before greenlets waiting for I/O events.

    :return: GreenThread object which can be used to retrieve the return value of the function
    :rtype: GreenThread
    """
    hub = hubs.get_hub()
    g = GreenThread(hub)
    hub.schedule_call_now(g.switch, func, *args, **kwargs)
    return g


def spawn_after(seconds, func, *args, **kwargs):
    """Spawn a GreenThread after `seconds` have elapsed

    Execution control returns immediately to the caller.

    To cancel the spawn and prevent *func* from being called, call :meth:`GreenThread.cancel` on the
    returned GreenThread. This will not abort the function if it's already started running, which is
    generally the desired behavior. If terminating *func* regardless of whether it's started or not
    is the desired behavior, call :meth:`GreenThread.kill`.

    :return: GreenThread object which can be used to retrieve the return value of the function
    :rtype: GreenThread
    """
    hub = hubs.get_hub()
    g = GreenThread(hub)
    hub.schedule_call_global(seconds, g.switch, func, *args, **kwargs)
    return g


def _spawn_n(seconds, func, args, kwargs):
    hub = hubs.get_hub()
    g = greenlet.greenlet(func, parent=hub)
    t = hub.schedule_call_global(seconds, g.switch, *args, **kwargs)
    return t, g


class GreenThread(greenlet.greenlet):
    """The GreenThread class is a type of Greenlet which has the additional property of being able
    to retrieve the return value of the main function. Do not construct GreenThread objects
    directly; call :func:`spawn` to get one.
    """

    def __init__(self, parent):
        """
        :param parent: parent greenlet
        :type parent: greenlet.greenlet
        """
        greenlet.greenlet.__init__(self, self.main, parent)
        self._exit_event = event.Event()
        self._resolving_links = False

    def wait(self):
        """Return the result of the main function of this GreenThread

        If the result is a normal return value, :meth:`wait` returns it.  If it raised an exception,
        :meth:`wait` will raise the same exception (though the stack trace will unavoidably contain
        some frames from within the GreenThread module).
        """
        return self._exit_event.wait()

    def link(self, func, *curried_args, **curried_kwargs):
        """Set up a function to be called with the results of the GreenThread

        The function must have the following signature::

            func(gt, [curried args/kwargs])

        When the GreenThread finishes its run, it calls *func* with itself and with the `curried
        arguments <http://en.wikipedia.org/wiki/Currying>`_ supplied at link-time.  If the function
        wants to retrieve the result of the GreenThread, it should call wait() on its first
        argument.

        Note that *func* is called within execution context of the GreenThread, so it is possible to
        interfere with other linked functions by doing things like switching explicitly to another
        GreenThread.
        """
        self._exit_funcs = getattr(self, '_exit_funcs', deque())
        self._exit_funcs.append((func, curried_args, curried_kwargs))
        if self._exit_event.ready():
            self._resolve_links()

    def unlink(self, func, *curried_args, **curried_kwargs):
        """Remove linked function set by :meth:`link`

        Remove successfully return True, otherwise False
        """
        if not getattr(self, '_exit_funcs', None):
            return False
        try:
            self._exit_funcs.remove((func, curried_args, curried_kwargs))
            return True
        except ValueError:
            return False

    def main(self, function, *args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except:
            self._exit_event.send_exception(*sys.exc_info())
            self._resolve_links()
            raise
        else:
            self._exit_event.send(result)
            self._resolve_links()

    def _resolve_links(self):
        # ca and ckw are the curried function arguments
        if self._resolving_links:
            return
        self._resolving_links = True
        try:
            exit_funcs = getattr(self, '_exit_funcs', deque())
            while exit_funcs:
                f, ca, ckw = exit_funcs.popleft()
                f(self, *ca, **ckw)
        finally:
            self._resolving_links = False

    def kill(self, *throw_args):
        """Kill the GreenThread using :func:`kill`

        After being killed all calls to :meth:`wait` will raise `throw_args` (which default to
        :class:`greenlet.GreenletExit`).
        """
        return kill(self, *throw_args)

    def cancel(self, *throw_args):
        """Kill the GreenThread using :func:`kill`, but only if it hasn't already started running

        After being canceled, all calls to :meth:`wait` will raise `throw_args` (which default to
        :class:`greenlet.GreenletExit`).
        """
        return cancel(self, *throw_args)


def cancel(g, *throw_args):
    """Cancel the target greenlet/GreenThread if it hasn't already started

    This is like :func:`kill`, but only has an effect if the target greenlet/GreenThread has not
    yet started.
    """
    if not g:
        kill(g, *throw_args)


def kill(g, *throw_args):
    """Terminate the target greenlet/GreenThread by raising an exception into it

    Whatever that GreenThread might be doing, be it waiting for I/O or another primitive, it sees an
    exception right away.

    By default, this exception is GreenletExit, but a specific exception may be specified.
    `throw_args` should be the same as the arguments to raise; either an exception instance or an
    exc_info tuple.

    Calling :func:`kill` causes the calling greenlet to cooperatively yield.

    :param g: target greenlet/GreenThread to kill
    :type g: greenlet.greenlet or GreenThread
    """
    if g.dead:
        return

    hub = hubs.get_hub()
    if not g:
        # greenlet hasn't started yet and therefore throw won't work on its own; semantically we
        # want it to be as though the main method never got called
        def just_raise(*a, **kw):
            if throw_args:
                reraise(throw_args[0], throw_args[1], throw_args[2])
            else:
                raise greenlet.GreenletExit()

        g.run = just_raise
        if isinstance(g, GreenThread):
            # it's a GreenThread object, so we want to call its main method to take advantage of
            # the notification
            try:
                g.main(just_raise, (), {})
            except:
                pass

    current = greenlet.getcurrent()
    if current is not hub:
        # arrange to wake the caller back up immediately
        hub.schedule_call_now(current.switch)

    g.throw(*throw_args)
