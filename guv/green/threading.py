"""Greenified threading module
"""
import greenlet

from .. import patcher
from ..event import TEvent
from .thread import start_new_thread, allocate_lock, get_ident, local

__patched__ = ['_start_new_thread', '_allocate_lock', '_get_ident',
               'local', 'Lock', 'Event', '_DummyThread']

threading_orig = patcher.original('threading')

_start_new_thread = start_new_thread
_allocate_lock = allocate_lock
_get_ident = get_ident
local = local
Lock = _allocate_lock
Event = TEvent


def _cleanup(g):
    threading_orig._active.pop(id(g))


class _DummyThread(threading_orig._DummyThread):
    # instances of this will cleanup its own entry
    # in ``threading._active``

    def __init__(self):
        super().__init__()
        g = greenlet.getcurrent()
        rawlink = getattr(g, 'rawlink', None)
        if rawlink is not None:
            rawlink(_cleanup)

    def _Thread__stop(self):
        pass
