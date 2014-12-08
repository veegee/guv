"""Greenified :mod:`_thread`
"""
import greenlet
import _thread as _thread_orig

from .. import greenthread
from ..semaphore import Semaphore
from .local import local

__patched__ = ['get_ident', 'start_new_thread', 'allocate_lock',
               'exit', 'interrupt_main', 'stack_size', '_local', 'LockType']

# patch attributes
_local = local
LockType = Semaphore


def get_ident(gr=None):
    if gr is None:
        return id(greenlet.getcurrent())
    else:
        return id(gr)


def start_new_thread(function, args=(), kwargs=None):
    kwargs = kwargs or {}
    g = greenthread.spawn_n(function, args, kwargs)
    return get_ident(g)


def allocate_lock(*a):
    return LockType(1)


def exit():
    raise greenlet.GreenletExit


def interrupt_main():
    curr = greenlet.getcurrent()
    if curr.parent and not curr.parent.dead:
        curr.parent.throw(KeyboardInterrupt())
    else:
        raise KeyboardInterrupt()


if hasattr(_thread_orig, 'stack_size'):
    stack_size_orig = _thread_orig.stack_size

    def stack_size(size=None):
        if size is None:
            return stack_size_orig()
        if size > stack_size_orig():
            return stack_size_orig(size)
        else:
            pass
            # not going to decrease stack_size, because otherwise other greenlets in
            # this thread will suffer
