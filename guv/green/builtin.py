"""
In order to detect a filehandle that's been closed, our only clue may be the operating system
returning the same filehandle in response to some other  operation.

The builtins 'file' and 'open' are patched to collaborate with the notify_opened protocol.
"""

builtins_orig = __builtins__

from .. import hubs
from ..patcher import copy_attributes

__all__ = dir(builtins_orig)
__patched__ = ['open']

copy_attributes(builtins_orig, globals(), ignore=__patched__, srckeys=dir(builtins_orig))

# TODO: should this even be here?
hubs.get_hub()

__original_open = open
__opening = False


def open(*args):
    global __opening
    result = __original_open(*args)
    if not __opening:
        # This is incredibly ugly. 'open' is used under the hood by the import process. So, ensure
        # we don't wind up in an infinite loop.
        __opening = True
        hubs.notify_opened(result.fileno())
        __opening = False
    return result
