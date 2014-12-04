"""Greenified :mod:`time` module

The only thing that needs to be patched from :mod:`time` is :func:`time.sleep` to yield instead
of block the thread.
"""
import time as time_orig
from ..patcher import copy_attributes

__patched__ = ['sleep']
copy_attributes(time_orig, globals(), ignore=__patched__, srckeys=dir(time_orig))
from .. import greenthread

sleep = greenthread.sleep
