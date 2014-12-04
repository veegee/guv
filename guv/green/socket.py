import os
import logging

log = logging.getLogger('guv')

from ..green import _socket3 as gsocket

__all__ = gsocket.__all__
__patched__ = gsocket.__patched__ + ['gethostbyname', 'getaddrinfo', 'create_connection']

from ..patcher import copy_attributes

copy_attributes(gsocket, globals(), srckeys=dir(gsocket))

# explicitly define globals to silence IDE errors
SOCK_STREAM = gsocket.SOCK_STREAM
socket = gsocket.socket
error = gsocket.error
_GLOBAL_DEFAULT_TIMEOUT = gsocket._GLOBAL_DEFAULT_TIMEOUT

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
            msg = e
            if sock is not None:
                sock.close()

    raise error(msg)
