import os
import sys
import logging

log = logging.getLogger('guv')

__import__('guv.green._socket_nodns')
__socket = sys.modules['guv.green._socket_nodns']

__all__ = __socket.__all__
__patched__ = __socket.__patched__ + ['gethostbyname', 'getaddrinfo', 'create_connection', ]

from ..patcher import copy_attributes

copy_attributes(__socket, globals(), srckeys=dir(__socket))

greendns = None
if os.environ.get('GUV_NO_GREENDNS') is not None:
    try:
        from ..support import greendns

        log.debug('Using greendns module for non-blocking DNS querying')
    except ImportError as ex:
        log.warn('dnspython3 not found, falling back to blocking DNS querying'.format(ex))

if greendns:
    gethostbyname = greendns.gethostbyname
    getaddrinfo = greendns.getaddrinfo
    gethostbyname_ex = greendns.gethostbyname_ex
    getnameinfo = greendns.getnameinfo
    __patched__ = __patched__ + ['gethostbyname_ex', 'getnameinfo']


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
