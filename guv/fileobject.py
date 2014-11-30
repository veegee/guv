"""Greenified file class implementing standard file operations

Not supported on Windows.
"""
import os
from socket import SocketIO
from errno import EBADF, EAGAIN, EINTR

import fcntl
from .hubs import get_hub
from .support import PYPY
from .green.os import read, write
from .exceptions import FileObjectClosed

__all__ = ['FileObjectPosix', 'FileObject']

IGNORED_ERRORS = {EAGAIN, EINTR}


def set_nonblocking(fd):
    """Set the file descriptor to non-blocking mode

    :param int fd: file descriptor
    """
    flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
    if not bool(flags & os.O_NONBLOCK):
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        return True


class SocketAdapter:
    """Socket-like API on top of a file descriptor.

    The main purpose of it is to re-use _fileobject to create proper cooperative file objects
    from file descriptors on POSIX platforms.
    """

    def __init__(self, fileno, mode=None, close=True):
        if not isinstance(fileno, int):
            raise TypeError('fileno must be int: %r' % fileno)
        self._fileno = fileno
        self._mode = mode or 'rb'
        self._close = close
        self._translate = 'U' in self._mode
        set_nonblocking(fileno)
        self._eat_newline = False
        self.hub = get_hub()
        io = self.hub.loop.io
        self._read_event = io(fileno, 1)
        self._write_event = io(fileno, 2)
        self._refcount = 1

    def __repr__(self):
        if self._fileno is None:
            return '<%s at 0x%x closed>' % (self.__class__.__name__, id(self))
        else:
            args = (self.__class__.__name__, id(self), getattr(self, '_fileno', 'N/A'),
                    getattr(self, '_mode', 'N/A'))
            return '<%s at 0x%x (%r, %r)>' % args

    def makefile(self, *args, **kwargs):
        return SocketIO(self, *args, **kwargs)

    def fileno(self):
        result = self._fileno
        if result is None:
            raise IOError(EBADF, 'Bad file descriptor (SocketAdapter object is closed')
        return result

    def detach(self):
        x = self._fileno
        self._fileno = None
        return x

    def _reuse(self):
        self._refcount += 1

    def _drop(self):
        self._refcount -= 1
        if self._refcount <= 0:
            self._realclose()

    def close(self):
        self._drop()

    def _realclose(self):
        # TODO: should we notify the hub that this fd is closed?
        fileno = self._fileno
        if fileno is not None:
            self._fileno = None
            if self._close:
                os.close(fileno)

    def sendall(self, data):
        fileno = self.fileno()
        bytes_total = len(data)
        bytes_written = 0
        while True:
            try:
                bytes_written += write(fileno, memoryview(data)[bytes_written:])
            except (IOError, OSError) as ex:
                code = ex.args[0]
                if code not in IGNORED_ERRORS:
                    raise
            if bytes_written >= bytes_total:
                return
            self.hub.wait(self._write_event)

    def recv(self, size):
        while True:
            try:
                data = read(self.fileno(), size)
            except (IOError, OSError) as ex:
                code = ex.args[0]
                if code not in IGNORED_ERRORS:
                    raise
            else:
                if not self._translate or not data:
                    return data
                if self._eat_newline:
                    self._eat_newline = False
                    if data.startswith('\n'):
                        data = data[1:]
                        if not data:
                            return self.recv(size)
                if data.endswith('\r'):
                    self._eat_newline = True
                return self._translate_newlines(data)
            self.hub.wait(self._read_event)

    def _translate_newlines(self, data):
        data = data.replace("\r\n", "\n")
        data = data.replace("\r", "\n")
        return data


class FileObjectPosix(SocketIO):
    def __init__(self, fobj, mode='rb', bufsize=-1, close=True):
        if isinstance(fobj, int):
            fileno = fobj
            fobj = None
        else:
            fileno = fobj.fileno()

        sock = SocketAdapter(fileno, mode, close=close)
        self._fobj = fobj
        self._closed = False
        super().__init__(sock, mode)
        if PYPY:
            sock._drop()

    def __repr__(self):
        if self._sock is None:
            return '<%s closed>' % self.__class__.__name__
        elif self._fobj is None:
            return '<%s %s>' % (self.__class__.__name__, self._sock)
        else:
            return '<%s %s _fobj=%r>' % (self.__class__.__name__, self._sock, self._fobj)

    def close(self):
        if self._closed:
            # make sure close() is only ran once when called concurrently
            # cannot rely on self._sock for this because we need to keep that until flush()
            # is done
            return
        self._closed = True
        sock = self._sock
        if sock is None:
            return
        try:
            self.flush()
        finally:
            if self._fobj is not None or not self._close:
                sock.detach()
            else:
                sock._drop()
            self._sock = None
            self._fobj = None

    def __getattr__(self, item):
        assert item != '_fobj'
        if self._fobj is None:
            raise FileObjectClosed
        return getattr(self._fobj, item)


FileObject = FileObjectPosix
