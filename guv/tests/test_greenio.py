import errno

import pytest

from ..green import socket
from ..greenio import socket as green_socket

TIMEOUT_SMALL = 0.01
BACKLOG = 10


class TestGreenSocket:
    def test_socket_init(self):
        sock = socket.socket()
        assert isinstance(sock, green_socket)

    def test_socket_close(self, gsock):
        gsock.close()

    def test_connect(self, gsock, pub_addr):
        gsock.connect(pub_addr)
        print(gsock.getpeername())
        assert gsock.getpeername()

    def test_connect_timeout(self, gsock, fail_addr):
        gsock.settimeout(TIMEOUT_SMALL)

        with pytest.raises(socket.timeout):
            gsock.connect(fail_addr)

    def test_connect_ex_timeout(self, gsock, fail_addr):
        gsock.settimeout(TIMEOUT_SMALL)

        e = gsock.connect_ex(fail_addr)

        if e not in {errno.EHOSTUNREACH, errno.ENETUNREACH}:
            assert e == errno.EAGAIN

    def test_accept_timeout(self, gsock):
        gsock.settimeout(TIMEOUT_SMALL)
        gsock.bind(('', 0))
        gsock.listen(BACKLOG)

        with pytest.raises(socket.timeout):
            gsock.accept()

    def test_recv_timeout(self, gsock, pub_addr):
        gsock.connect(pub_addr)
        gsock.settimeout(TIMEOUT_SMALL)

        with pytest.raises(socket.timeout) as exc_info:
            gsock.recv(8192)

        assert exc_info.value.args[0] == 'timed out'

    def test_send_to_closed_sock_raises(self, gsock):
        with pytest.raises(BrokenPipeError):
            gsock.send(b'hello')


class TestGreenModule:
    def test_create_connection(self, pub_addr):
        sock = socket.create_connection(pub_addr)

    def test_create_connection_timeout_error(self, fail_addr):
        with pytest.raises(OSError):
            sock = socket.create_connection(fail_addr, timeout=0.01)

