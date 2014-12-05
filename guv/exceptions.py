"""Errors and Exceptions

This module is the main module for all errors and exceptions for guv. Platform-specific socket
errors are appropriately configured here.
"""
from errno import (EWOULDBLOCK, EINPROGRESS, EALREADY, EISCONN, EBADF, ENOTCONN, ESHUTDOWN, EAGAIN,
                   ECONNRESET, EPIPE, EINVAL, ECONNABORTED)

from . import patcher

osocket = patcher.original('socket')

from .support import OS_WINDOWS

SYSTEM_ERROR = (KeyboardInterrupt, SystemExit, SystemError)

if OS_WINDOWS:
    # winsock sometimes throws ENOTCONN
    SOCKET_BLOCKING = {EAGAIN, EWOULDBLOCK}
    SOCKET_CLOSED = {ECONNRESET, ESHUTDOWN, ENOTCONN}
    CONNECT_ERR = {EINPROGRESS, EALREADY, EWOULDBLOCK, EINVAL}
else:
    # oddly, on linux/darwin, an unconnected socket is expected to block,
    # so we treat ENOTCONN the same as EWOULDBLOCK
    SOCKET_BLOCKING = {EAGAIN, EWOULDBLOCK, ENOTCONN}
    SOCKET_CLOSED = {ECONNRESET, ESHUTDOWN, EPIPE}
    CONNECT_ERR = {EINPROGRESS, EALREADY, EWOULDBLOCK}

CONNECT_SUCCESS = {0, EISCONN}

BAD_SOCK = {EBADF, ECONNABORTED}
BROKEN_SOCK = {EPIPE, ECONNRESET}

ACCEPT_EXCEPTIONS = {osocket.error}
ACCEPT_ERRNO = {EPIPE, EBADF, ECONNRESET}


class IOClosed(IOError):
    pass


FileObjectClosed = IOError(EBADF, 'Bad file descriptor (FileObject was closed)')
