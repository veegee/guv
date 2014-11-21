"""
Monkey-patch the standard library to backport certain features to older Python versions
"""
import time


def patch():
    if not hasattr(time, 'monotonic'):
        time.monotonic = time.time
