import os as os_orig
import errno
import socket

from ..exceptions import IOClosed
from ..support import get_errno
from .. import hubs, greenthread
from ..patcher import copy_attributes
from ..const import READ, WRITE

__all__ = os_orig.__all__
__patched__ = ['read', 'write', 'wait', 'waitpid', 'open']

copy_attributes(os_orig, globals(), ignore=__patched__, srckeys=dir(os_orig))

__open = os_orig.open
__read = os_orig.read
__write = os_orig.write
__waitpid = os_orig.waitpid


def read(fd, n):
    """Wrap os.read
    """
    while True:
        try:
            return __read(fd, n)
        except (OSError, IOError) as e:
            if get_errno(e) != errno.EAGAIN:
                raise
        except socket.error as e:
            if get_errno(e) == errno.EPIPE:
                return ''
            raise
        try:
            hubs.trampoline(fd, READ)
        except IOClosed:
            return ''


def write(fd, data):
    """Wrap os.write
    """
    while True:
        try:
            return __write(fd, data)
        except (OSError, IOError) as e:
            if get_errno(e) != errno.EAGAIN:
                raise
        except socket.error as e:
            if get_errno(e) != errno.EPIPE:
                raise
        hubs.trampoline(fd, WRITE)


def wait():
    """Wait for completion of a child process

    :return: (pid, status)
    """
    return waitpid(0, 0)


def waitpid(pid, options):
    """Wait for completion of a given child process

    :return: (pid, status)
    """
    if options & os_orig.WNOHANG != 0:
        return __waitpid(pid, options)
    else:
        new_options = options | os_orig.WNOHANG
        while True:
            rpid, status = __waitpid(pid, new_options)
            if rpid and status >= 0:
                return rpid, status
            greenthread.sleep(0.01)


def open(file, flags, mode=0o777):
    """Wrap os.open

    This behaves identically, but collaborates with the hub's notify_opened protocol.
    """
    fd = __open(file, flags, mode)
    hubs.notify_opened(fd)
    return fd
