import sys
import logging
from abc import ABCMeta, abstractmethod

from . import greenpool, patcher, greenthread
from .green import socket, ssl
from .hubs import get_hub

original_socket = patcher.original('socket')

log = logging.getLogger('guv')


def serve(sock, handle, concurrency=1000):
    pool = greenpool.GreenPool(concurrency)
    server = Server(sock, handle, pool, 'spawn_n')
    server.start()


def listen(addr, family=socket.AF_INET, backlog=511):
    server_sock = socket.socket(family, socket.SOCK_STREAM)

    if sys.platform[:3] != 'win':
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_sock.bind(addr)
    server_sock.listen(backlog)

    return server_sock


def connect(addr, family=socket.AF_INET, bind=None):
    """Convenience function for opening client sockets.

    :param addr: Address of the server to connect to.  For TCP sockets, this is a (host,
    port) tuple.
    :param family: Socket family, optional.  See :mod:`socket` documentation for available families.
    :param bind: Local address to bind to, optional.
    :return: The connected green socket object.
    """
    sock = socket.socket(family, socket.SOCK_STREAM)
    if bind is not None:
        sock.bind(bind)
    sock.connect(addr)
    return sock


def wrap_ssl(sock, *a, **kw):
    """Convenience function for converting a regular socket into an SSL socket

    The preferred idiom is to call wrap_ssl directly on the creation method, e.g.,
    ``wrap_ssl(connect(addr))`` or ``wrap_ssl(listen(addr), server_side=True)``. This way there is
    no "naked" socket sitting around to accidentally corrupt the SSL session.

    :return Green SSL socket
    """
    return ssl.wrap_socket(sock, *a, **kw)


class StopServe(Exception):
    """Exception class used for quitting :func:`~guv.serve` gracefully
    """
    pass


class AbstractServer(metaclass=ABCMeta):
    def __init__(self, server_sock, client_handler_cb, pool=None, spawn=None):
        """
        If pool and spawn are None (default), bare greenlets will be used and the spawn mechanism
        will be greenlet.switch(). This is the simplest and most direct way to spawn greenlets to
        handle client requests, however it is not the most stable.

        If more control is desired over client handlers, specify a greenlet pool class such as
        `GreenPool`, and specify a spawn mechanism. If specifying a pool class, the the name of the
        spawn method must be passed as well.

        The signature of client_handler_cb is as follows::

            Callable(sock: socket, addr: tuple[str, int]) -> None

        :param pool: greenlet pool class or None
        :param spawn: 'spawn', or 'spawn_n', or None
        :type spawn: str or None
        """
        self.server_sock = server_sock
        self.client_handler_cb = client_handler_cb

        if pool is None:
            # use bare greenlets
            self.pool = None
            log.debug('Server: use fast spawn_n')
        else:
            # create a pool instance
            self.pool = pool
            self.spawn = getattr(self.pool, spawn)
            log.debug('Server: use {}.{}'.format(pool, spawn))

        self.hub = get_hub()

        self.address = server_sock.getsockname()[:2]

    @abstractmethod
    def start(self):
        """Start the server
        """
        pass

    @abstractmethod
    def stop(self):
        """Stop the server
        """

    def handle_error(self, msg, level=logging.ERROR, exc_info=True):
        log.log(level, '{0}: {1} --> closing'.format(self, msg), exc_info=exc_info)
        self.stop()

    def _spawn(self, client_sock, addr):
        """Spawn a client handler using the appropriate spawn mechanism

        :param client_sock: client socket
        :type client_sock: socket.socket
        :param addr: address tuple
        :type addr: tuple[str, int]
        """
        if self.pool is None:
            greenthread.spawn_n(self.client_handler_cb, client_sock, addr)
        else:
            self.spawn(self.client_handler_cb, client_sock, addr)


class Server(AbstractServer):
    """Standard server implementation not directly dependent on pyuv
    """

    def start(self):
        log.debug('{0.__class__.__name__} started on {0.address}'.format(self))
        while True:
            try:
                client_sock, addr = self.server_sock.accept()
                self._spawn(client_sock, addr)
            except StopServe:
                log.debug('{0} stopped'.format(self))
                return

    def stop(self):
        log.debug('{0}: stopping'.format(self))
