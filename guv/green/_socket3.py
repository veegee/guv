import socket as socket_orig

__all__ = socket_orig.__all__
__patched__ = ['fromfd', 'socketpair', 'ssl', 'socket']

from ..patcher import copy_attributes

copy_attributes(socket_orig, globals(),
                ignore=__patched__, srckeys=dir(socket_orig))

from ..greenio import socket

try:
    _fromfd_orig = socket_orig.fromfd

    def fromfd(*args):
        return socket(_fromfd_orig(*args))
except AttributeError:
    pass

try:
    _socketpair_orig = socket_orig.socketpair

    def socketpair(*args):
        one, two = _socketpair_orig(*args)
        return socket(one), socket(two)
except AttributeError:
    pass
