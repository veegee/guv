import pytest

from ..greenio import socket


@pytest.fixture(scope='function')
def gsock():
    return socket()
