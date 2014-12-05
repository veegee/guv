# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

from functools import partial
import errno
import sys

try:
    import guv
except ImportError:
    raise RuntimeError("You need guv installed to use this worker.")

_socket = __import__("socket")
from guv import hubs, greenthread, greenpool, StopServe, trampoline
from guv.greenio import socket as gsocket
from guv.support import get_errno
from guv.const import READ, WRITE
import greenlet

from gunicorn.http.wsgi import sendfile as o_sendfile
from gunicorn.workers.async import AsyncWorker


def _guv_sendfile(fdout, fdin, offset, nbytes):
    while True:
        try:
            return o_sendfile(fdout, fdin, offset, nbytes)
        except OSError as e:
            if get_errno(e) == errno.EAGAIN:
                if not isinstance(fdout, int):
                    fd = fdout.fileno()
                else:
                    fd = fdout
                trampoline(fd, WRITE)
            else:
                raise


def _guv_serve_slow(sock, handle, concurrency):
    """
    Serve requests forever.

    This code is nearly identical to ``eventlet.convenience.serve`` except
    that it attempts to join the pool at the end, which allows for gunicorn
    graceful shutdowns.
    """
    pool = greenpool.GreenPool(concurrency)
    server_gt = greenlet.getcurrent()

    while True:
        try:
            conn, addr = sock.accept()
            gt = pool.spawn(handle, conn, addr)
            gt.link(_guv_stop, server_gt, conn)
            conn, addr, gt = None, None, None
        except StopServe:
            pool.waitall()
            return


def _guv_serve(sock, handle, concurrency):
    """
    Serve requests forever.

    This code is nearly identical to ``eventlet.convenience.serve`` except
    that it attempts to join the pool at the end, which allows for gunicorn
    graceful shutdowns.
    """
    while True:
        try:
            conn, addr = sock.accept()
            gt = greenthread.spawn_n(handle, conn, addr)
            conn, addr, gt = None, None, None
        except StopServe:
            return


def _guv_stop(client, server, conn):
    """
    Stop a greenlet handling a request and close its connection.

    This code is lifted from eventlet so as not to depend on undocumented
    functions in the library.
    """
    try:
        try:
            client.wait()
        finally:
            conn.close()
    except greenlet.GreenletExit:
        pass
    except Exception:
        greenthread.kill(server, *sys.exc_info())


def patch_sendfile():
    from gunicorn.http import wsgi

    if o_sendfile is not None:
        setattr(wsgi, "sendfile", _guv_sendfile)


class GuvWorker(AsyncWorker):
    def patch(self):
        guv.monkey_patch(os=False)
        patch_sendfile()

    def init_process(self):
        hubs.use_hub()
        self.patch()
        super(GuvWorker, self).init_process()

    def timeout_ctx(self):
        return guv.Timeout(self.cfg.keepalive or None, False)

    def handle(self, listener, client, addr):
        if self.cfg.is_ssl:
            client = guv.wrap_ssl(client, server_side=True,
                                  **self.cfg.ssl_options)

        super(GuvWorker, self).handle(listener, client, addr)

    def run(self):
        acceptors = []
        for sock in self.sockets:
            gsock = gsocket(sock.FAMILY, _socket.SOCK_STREAM, fileno=sock.fileno())
            gsock.setblocking(1)
            hfun = partial(self.handle, gsock)
            acceptor = guv.spawn(_guv_serve, gsock, hfun, self.worker_connections)

            acceptors.append(acceptor)
            guv.gyield()

        while self.alive:
            self.notify()
            guv.sleep(1.0)

        self.notify()
        try:
            with guv.Timeout(self.cfg.graceful_timeout) as t:
                [a.kill(guv.StopServe()) for a in acceptors]
                [a.wait() for a in acceptors]
        except guv.Timeout as te:
            if te != t:
                raise
            [a.kill() for a in acceptors]
