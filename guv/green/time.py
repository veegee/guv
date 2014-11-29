"""Greenified :mod:`time` module

The only thing that needs to be patched from :mod:`time` is :func:`time.sleep` to yield instead
of block the thread.
"""
__time = __import__('time')
from ..patcher import copy_attributes

__patched__ = ['sleep']
copy_attributes(__time, globals(), ignore=__patched__, srckeys=dir(__time))
from .. import greenthread

sleep = greenthread.sleep
