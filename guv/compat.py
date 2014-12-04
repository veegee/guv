"""
Monkey-patch the standard library to backport certain features to older Python versions
"""
from . import patcher


def patch_time():
    time = patcher.original('time')
    if not hasattr(time, 'monotonic'):
        time.monotonic = time.time

    import time as new_time

    if not hasattr(new_time, 'monotonic'):
        time.monotonic = time.time


def patch():
    patch_time()
