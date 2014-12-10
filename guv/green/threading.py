"""Greenified threading module
"""
import greenlet
import logging

from .. import patcher, event, semaphore
from ..greenthread import GreenThread, spawn
from . import time, thread, greenlet_local

log = logging.getLogger('guv')

threading_orig = patcher.original('threading')

__patched__ = ['_start_new_thread', '_allocate_lock', '_get_ident', '_sleep', '_after_fork',
               '_shutdown', '_set_sentinel',
               'local', 'stack_size', 'currentThread', 'current_thread', 'Lock', 'Event',
               'Semaphore', 'BoundedSemaphore', 'Thread']

patcher.inject('threading', globals(), ('thread', thread), ('time', time))

local = greenlet_local.local
Event = event.TEvent
Semaphore = semaphore.Semaphore
BoundedSemaphore = semaphore.BoundedSemaphore
Lock = semaphore.Semaphore
_start_new_thread = thread.start_new_thread
_allocate_lock = thread.allocate_lock
_set_sentinel = thread._set_sentinel
get_ident = thread.get_ident

# active Thread objects dict[greenlet.greenlet: Thread]
active_threads = {}


def active_count() -> int:
    return len(active_threads)


def enumerate():
    return list(active_threads.values())


def main_thread():
    assert isinstance(_main_thread, Thread)
    return _main_thread


def settrace():
    raise NotImplemented('Not implemented for greenlets')


def setprofile():
    raise NotImplemented('Not implemented for greenlets')


def current_thread() -> Thread:
    g = greenlet.getcurrent()
    assert isinstance(g, greenlet.greenlet)

    if g and g not in active_threads:
        # this greenlet was spawned outside of the threading module
        return _main_thread

    return active_threads[g]


def _cleanup(g):
    """Clean up GreenThread

    This function is called when the underlying GreenThread object of a "green" Thread exits.
    """
    del active_threads[g]


class Thread:
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None):
        self._name = name or 'Thread'
        self.daemon = True

        self.target = target or self.run

        self.args = args
        self.kwargs = kwargs

        #: :type: GreenThread
        self._gt = None

    def __repr__(self):
        return '<(green) Thread (%s, %r)>' % (self._name, self._gt)

    def start(self):
        self._gt = spawn(self.target, *self.args, **self.kwargs)
        self._gt.link(_cleanup)

        active_threads[self._gt] = self

    def run(self):
        pass

    def join(self, timeout=None):
        # FIXME: add support for timeouts
        return self._gt.wait()

    def get_name(self):
        return self._name

    def set_name(self, value):
        self._name = str(value)

    def is_alive(self):
        return bool(self._gt)

    def is_daemon(self):
        return self.daemon

    name = property(get_name, set_name)
    ident = property(lambda self: id(self._g))

    getName = get_name
    setName = set_name
    isAlive = is_alive
    isDaemon = is_daemon


_main_thread = Thread()
_main_thread.name = 'MainThread'
_main_thread._gt = greenlet.getcurrent()

active_threads[greenlet.getcurrent()] = _main_thread
