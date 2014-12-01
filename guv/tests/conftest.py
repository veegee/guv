import pytest

from ..greenio import socket


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

