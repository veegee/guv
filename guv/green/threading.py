"""Greenified threading module
"""
import greenlet
import logging

from .. import patcher
from .. import event, semaphore
from . import time, thread

log = logging.getLogger('guv')

threading_orig = patcher.original('threading')

__patched__ = ['_start_new_thread', '_allocate_lock', '_get_ident', '_sleep', '_after_fork',
               '_shutdown', '_set_sentinel',
               'local', 'stack_size', 'currentThread', 'current_thread', 'Lock', 'Event',
               'Semaphore', 'BoundedSemaphore']

__threadlocal = threading_orig.local()

patcher.inject('threading', globals(), ('thread', thread), ('time', time))

Event = event.TEvent
Semaphore = semaphore.Semaphore
BoundedSemaphore = semaphore.BoundedSemaphore
Lock = semaphore.Semaphore
_start_new_thread = thread.start_new_thread
_allocate_lock = thread.allocate_lock
_set_sentinel = thread._set_sentinel
get_ident = thread.get_ident

_count = 1


class GThread:
    """Wrapper for GreenThread objects to provide Thread-like attributes and methods
    """

    def __init__(self, g):
        """
        :param g: GreenThread object (cannot be a plain greenlet object)
        :type g: GreenThread
        """
        global _count
        self._g = g
        self._name = 'GThread-%d' % _count
        _count += 1

    def __repr__(self):
        return '<GThread(%s, %r)>' % (self._name, self._g)

    def join(self, timeout=None):
        # FIXME: add support for timeouts
        return self._g.wait()

    def get_name(self):
        return self._name

    def set_name(self, value):
        self._name = str(value)

    def is_alive(self):
        return True

    def is_daemon(self):
        return self.daemon

    name = property(get_name, set_name)
    ident = property(lambda self: id(self._g))
    daemon = property(lambda self: True)

    getName = get_name
    setName = set_name
    isAlive = is_alive
    isDaemon = is_daemon


def _cleanup(g):
    active = __threadlocal.active
    del active[id(g)]


def current_thread():
    g = greenlet.getcurrent()
    if not g:
        # not currently in a greenlet, fall back to original function
        return threading_orig.current_thread()

    try:
        active = __threadlocal.active
    except AttributeError:
        active = __threadlocal.active = {}

    try:
        t = active[id(g)]
    except KeyError:
        try:
            g.link(_cleanup)
        except AttributeError:
            # Not a GreenThread type, so there's no way to hook into
            # the green thread exiting. Fall back to the standard
            # function then.
            t = threading_orig.current_thread()
        else:
            t = active[id(g)] = GThread(g)

    return t


currentThread = current_thread
