import io
import time
import os
import _socket
import errno
from errno import (EWOULDBLOCK, EINPROGRESS, EALREADY, EISCONN, EBADF, ENOTCONN, ESHUTDOWN, EAGAIN,
                   ECONNRESET, EPIPE, EINVAL)

from . import patcher
from .hubs import trampoline
from .exceptions import IOClosed
from .support import OS_WINDOWS

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

osocket = patcher.original('socket')
AF_INET = osocket.AF_INET
AF_UNIX = osocket.AF_UNIX
SOCK_STREAM = osocket.SOCK_STREAM
SOL_SOCKET = osocket.SOL_SOCKET
SO_ERROR = osocket.SO_ERROR
O_NONBLOCK = getattr(os, 'O_NONBLOCK', 0)  # Windows doesn't have this

error = osocket.error
dup = osocket.dup
getdefaulttimeout = osocket.getdefaulttimeout
getaddrinfo = osocket.getaddrinfo
cancel_wait_ex = error(EBADF, 'File descriptor was closed in another greenlet')

SocketIO = osocket.SocketIO


class socket(_socket.socket):
    __slots__ = ["__weakref__", "_io_refs", "_closed", "timeout"]

    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, fileno=None):
        super().__init__(family, type, proto, fileno)
        self._io_refs = 0
        self._closed = False
        super().setblocking(False)
        self.timeout = _socket.getdefaulttimeout()

    def _trampoline(self, fd, read=False, write=False, timeout=None, timeout_exc=None):
        """
        We need to trampoline via the event hub. We catch any signal back from the hub indicating
        that the operation we were waiting on was associated with a filehandle that's since been
        invalidated.
        """
        if self._closed:
            # If we did any logging, alerting to a second trampoline attempt on a closed
            # socket here would be useful.
            raise IOClosed()
        try:
            return trampoline(fd, read=read, write=write, timeout=timeout, timeout_exc=timeout_exc)
        except IOClosed:
            self._closed = True
            raise

    @property
    def type(self):
        return _socket.socket.type.__get__(self) & ~O_NONBLOCK

    def dup(self):
        fd = dup(self.fileno())
        sock = socket(self.family, self.type, self.proto, fileno=fd)
        sock.settimeout(self.gettimeout())
        return sock

    def accept(self):
        while True:
            res = self._socket_accept()

            if res is not None:
                # successfully accepted a connection
                fd, addr = res
                client_sock = socket(self.family, self.type, self.proto, fileno=fd)
                return client_sock, addr

            # else: EWOULDBLOCK
            self._trampoline(self.fileno(), read=True, timeout=self.gettimeout(),
                             timeout_exc=osocket.timeout('timed out'))

    def _real_close(self, _ss=_socket.socket):
        # This function should not reference any globals. See Python issue #808164.
        _ss.close(self)

    def close(self):
        self._closed = True
        if self._io_refs <= 0:
            self._real_close()

    @property
    def closed(self):
        return self._closed

    def detach(self):
        self._closed = True
        return super().detach()

    def connect(self, address):
        if self.timeout == 0.0:
            # nonblocking mode
            return super().connect(address)

        if self.gettimeout() is None:
            # blocking mode, no timeout
            while not self._socket_connect(address):
                self._trampoline(self.fileno(), write=True)
                self._socket_checkerr()
        else:
            # blocking mode, with timeout
            end = time.time() + self.gettimeout()
            while True:
                if self._socket_connect(address):
                    return

                if time.time() >= end:
                    raise osocket.timeout("timed out")

                self._trampoline(self.fileno(), write=True, timeout=end - time.time(),
                                 timeout_exc=osocket.timeout("timed out"))
                self._socket_checkerr()

    def connect_ex(self, address):
        try:
            return self.connect(address) or 0
        except osocket.timeout:
            return EAGAIN
        except error as ex:
            if type(ex) is error:
                return ex.args[0]
            else:
                raise  # gaierror is not silented by connect_ex

    def recv(self, *args):
        while True:
            try:
                return super().recv(*args)
            except error as e:
                err = e.args[0]
                if err in SOCKET_BLOCKING:
                    pass
                elif err in SOCKET_CLOSED:
                    return b''
                else:
                    raise

            self._trampoline(self.fileno(), read=True, timeout=self.gettimeout(),
                             timeout_exc=osocket.timeout("timed out"))

    def recvfrom(self, *args):
        while True:
            try:
                return super().recvfrom(*args)
            except error as ex:
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
            self._trampoline(self.fileno(), read=True, timeout=self.gettimeout(),
                             timeout_exc=osocket.timeout("timed out"))

    def recvfrom_into(self, *args):
        while True:
            try:
                return super().recvfrom_into(*args)
            except error as ex:
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
            self._trampoline(self.fileno(), read=True, timeout=self.gettimeout(),
                             timeout_exc=osocket.timeout("timed out"))

    def recv_into(self, *args):
        while True:
            try:
                return super().recv_into(*args)
            except error as ex:
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
            self._trampoline(self.fileno(), read=True, timeout=self.gettimeout(),
                             timeout_exc=osocket.timeout("timed out"))

    def send(self, data, flags=0):
        try:
            return super().send(data, flags)
        except error as e:
            if e.args[0] != EWOULDBLOCK:
                raise

            self._trampoline(self.fileno(), write=True, timeout=self.gettimeout(),
                             timeout_exc=osocket.timeout("timed out"))

            try:
                return super().send(data, flags)
            except error as e2:
                if e2.args[0] == EWOULDBLOCK:
                    return 0
                raise

    def sendall(self, data, flags=0):
        if self.timeout is None:
            data_sent = 0
            while data_sent < len(data):
                data_sent += self.send(memoryview(data)[data_sent:], flags)
        else:
            timeleft = self.timeout
            end = time.time() + timeleft
            data_sent = 0
            while True:
                data_sent += self.send(memoryview(data)[data_sent:], flags, timeout=timeleft)
                if data_sent >= len(data):
                    break
                timeleft = end - time.time()
                if timeleft <= 0:
                    raise osocket.timeout('timed out')

    def sendto(self, *args):
        try:
            return super().sendto(*args)
        except error as ex:
            if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                raise
            self._trampoline(self.fileno(), write=True, timeout=self.gettimeout(),
                             timeout_exc=osocket.timeout("timed out"))
            try:
                return super().sendto(*args)
            except error as ex2:
                if ex2.args[0] == EWOULDBLOCK:
                    return 0
                raise

    def setblocking(self, flag):
        if flag:
            self.timeout = None
        else:
            self.timeout = 0.0

    def settimeout(self, howlong):
        if howlong is not None:
            try:
                f = howlong.__float__
            except AttributeError:
                raise TypeError('a float is required')
            howlong = f()
            if howlong < 0.0:
                raise ValueError('Timeout value out of range')
        self.timeout = howlong

    def gettimeout(self):
        return self.timeout

    def makefile(self, mode="r", buffering=None, *, encoding=None, errors=None, newline=None):
        """makefile(...) -> an I/O stream connected to the socket

        The arguments are as for io.open() after the filename,
        except the only mode characters supported are 'r', 'w' and 'b'.
        The semantics are similar too.  (XXX refactor to share code?)
        """
        for c in mode:
            if c not in {"r", "w", "b"}:
                raise ValueError("invalid mode %r (only r, w, b allowed)")
        writing = "w" in mode
        reading = "r" in mode or not writing
        assert reading or writing
        binary = "b" in mode
        rawmode = ""
        if reading:
            rawmode += "r"
        if writing:
            rawmode += "w"
        raw = SocketIO(self, rawmode)
        self._io_refs += 1
        if buffering is None:
            buffering = -1
        if buffering < 0:
            buffering = io.DEFAULT_BUFFER_SIZE
        if buffering == 0:
            if not binary:
                raise ValueError("unbuffered streams must be binary")
            return raw
        if reading and writing:
            buffer = io.BufferedRWPair(raw, raw, buffering)
        elif reading:
            buffer = io.BufferedReader(raw, buffering)
        else:
            assert writing
            buffer = io.BufferedWriter(raw, buffering)
        if binary:
            return buffer
        text = io.TextIOWrapper(buffer, encoding, errors, newline)
        text.mode = mode
        return text

    def _socket_accept(self):
        """Attempt to accept()

        :return: (fd, address) or None if need to trampoline
        :rtype: tuple[fd, tuple[str, int]] or None
        """
        try:
            fd, addr = self._accept()
            return fd, addr
        except error as e:
            if e.args[0] == errno.EWOULDBLOCK:
                return None
            raise

    def _socket_connect(self, address):
        """Attempt to connect to `address`

        :return: True if successful, None if need to trampoline
        """
        err = self.connect_ex(address)
        if err in CONNECT_ERR:
            return None
        if err not in CONNECT_SUCCESS:
            raise socket.error(err, errno.errorcode[err])
        return True

    def _socket_checkerr(self):
        err = self.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err not in CONNECT_SUCCESS:
            raise socket.error(err, errno.errorcode[err])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self._closed:
            self.close()

    def __repr__(self):
        """Wrap __repr__() to reveal the real class name."""
        s = _socket.socket.__repr__(self)
        if s.startswith("<socket object"):
            s = "<%s.%s%s%s" % (self.__class__.__module__,
                                self.__class__.__name__,
                                getattr(self, '_closed', False) and " [closed] " or "",
                                s[7:])
        return s

    def __getstate__(self):
        raise TypeError('Cannot serialize socket object')

    def _decref_socketios(self):
        if self._io_refs > 0:
            self._io_refs -= 1
        if self._closed:
            self.close()


SocketType = socket


def fromfd(fd, family, type, proto=0):
    """ fromfd(fd, family, type[, proto]) -> socket object

    Create a socket object from a duplicate of the given file
    descriptor.  The remaining arguments are the same as for socket().
    """
    nfd = dup(fd)
    return socket(family, type, proto, nfd)


if hasattr(_socket.socket, "share"):
    def fromshare(info):
        """ fromshare(info) -> socket object

        Create a socket object from a the bytes object returned by
        socket.share(pid).
        """
        return socket(0, 0, 0, info)

if hasattr(_socket, "socketpair"):

    def socketpair(family=None, type=SOCK_STREAM, proto=0):
        """socketpair([family[, type[, proto]]]) -> (socket object, socket object)

        Create a pair of socket objects from the sockets returned by the platform
        socketpair() function.
        The arguments are the same as for socket() except the default family is
        AF_UNIX if defined on the platform; otherwise, the default is AF_INET.
        """
        if family is None:
            try:
                family = AF_UNIX
            except NameError:
                family = AF_INET
        a, b = _socket.socketpair(family, type, proto)
        a = socket(family, type, proto, a.detach())
        b = socket(family, type, proto, b.detach())
        return a, b

try:
    from OpenSSL import SSL
except ImportError:
    # pyOpenSSL not installed, define exceptions anyway for convenience
    class SSL(object):
        class WantWriteError(Exception):
            pass

        class WantReadError(Exception):
            pass

        class ZeroReturnError(Exception):
            pass

        class SysCallError(Exception):
            pass
