"""Greenified _thread
"""
import greenlet
import _thread as _thread_orig

from .. import greenthread
from ..semaphore import Semaphore as LockType
from . import lock as _lock

__patched__ = ['get_ident', 'start_new_thread', 'allocate_lock',
               'exit', 'interrupt_main', 'stack_size', '_local',
               'LockType', '_count', '_set_sentinel', 'RLock']

RLock = _lock.RLock

error = _thread_orig.error
__threadcount = 0


def _set_sentinel():
    return allocate_lock()


TIMEOUT_MAX = _thread_orig.TIMEOUT_MAX


def _count():
    return __threadcount


def get_ident(gr=None):
    if gr is None:
        return id(greenlet.getcurrent())
    else:
        return id(gr)


def __thread_body(func, args, kwargs):
    global __threadcount
    __threadcount += 1
    try:
        func(*args, **kwargs)
    finally:
        __threadcount -= 1


def start_new_thread(function, args=(), kwargs=None):
    kwargs = kwargs or {}
    g = greenthread.spawn(__thread_body, function, args, kwargs)
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
    __original_stack_size__ = _thread_orig.stack_size

    def stack_size(size=None):
        if size is None:
            return __original_stack_size__()
        if size > __original_stack_size__():
            return __original_stack_size__(size)
        else:
            pass
            # not going to decrease stack_size, because otherwise other greenlets in
            # this thread will suffer
