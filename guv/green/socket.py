import os
import logging

log = logging.getLogger('guv')

from .. import patcher
from ..green import _socket3 as gsocket

__all__ = gsocket.__all__
__patched__ = gsocket.__patched__ + ['gethostbyname', 'getaddrinfo', 'create_connection']

from ..patcher import copy_attributes

copy_attributes(gsocket, globals(), srckeys=dir(gsocket))

# explicitly define globals to silence IDE errors
socket = gsocket.socket

socket_orig = patcher.original('socket')
SOCK_STREAM = socket_orig.SOCK_STREAM
_GLOBAL_DEFAULT_TIMEOUT = socket_orig._GLOBAL_DEFAULT_TIMEOUT
error = socket_orig.error

if os.environ.get('GUV_NO_GREENDNS') is None:
    try:
        from ..support import greendns

        gethostbyname = greendns.gethostbyname
        getaddrinfo = greendns.getaddrinfo
        gethostbyname_ex = greendns.gethostbyname_ex
        getnameinfo = greendns.getnameinfo
        __patched__ = __patched__ + ['gethostbyname_ex', 'getnameinfo']

        log.debug('Patcher: using greendns module for non-blocking DNS querying')
    except ImportError as ex:
        greendns = None
        log.warn('Patcher: dnspython3 not found, falling back to blocking DNS querying'.format(ex))


def create_connection(address, timeout=_GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    """Connect to `address` and return the socket object
    """
    msg = 'getaddrinfo returns an empty list'
    host, port = address
    err = None
    for res in getaddrinfo(host, port, 0, SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket(af, socktype, proto)
            if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock

        except error as e:
            err = e
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
