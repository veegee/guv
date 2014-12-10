import pytest

from guv.greenio import socket
from guv import listen


@pytest.fixture(scope='session')
def pub_addr():
    """A working public address that is considered always available
    """
    return 'gnu.org', 80


@pytest.fixture(scope='session')
def fail_addr():
    """An address that nothing is listening on
    """
    return '192.0.0.0', 1000


@pytest.fixture(scope='function')
def gsock():
    return socket()


@pytest.fixture(scope='function')
def server_sock():
    sock = listen(('', 0))
    return sock

