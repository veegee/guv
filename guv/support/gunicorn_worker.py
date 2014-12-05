from functools import partial
import errno
import sys
from datetime import datetime
import socket
import ssl
import greenlet
import logging

from gunicorn import http, util
from gunicorn.http import wsgi
from gunicorn.http.wsgi import sendfile as o_sendfile
from gunicorn.workers import base

import guv
import guv.wsgi
from guv import hubs, greenthread, greenpool, StopServe, trampoline, gyield
from guv.greenio import socket as gsocket
from guv.support import get_errno, reraise
from guv.const import WRITE
from guv.exceptions import BROKEN_SOCK

ALREADY_HANDLED = object()

log = logging.getLogger('guv')


class AsyncWorker(base.Worker):
    """
    This class is a copy of the AsyncWorker included in gunicorn, with a few minor modifications:

    - Removed python 2 support
    - Improved request latency for keep-alive connections by yielding after each request
    - Graceful quit on ctrl-c by overriding handle_quit
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.worker_connections = self.cfg.worker_connections

    def handle_quit(self, sig, frame):
        """
        We override this because sys.exit() shouldn't be called. Instead, we should let the
        worker gracefully quit on its own.
        """
        # sys.stderr.write('handle_quit() frame: {0}, '
        #                  '{0.f_code.co_filename}:{0.f_code.co_name}:{0.f_lineno}\n'
        #                  .format(frame))
        sys.stderr.flush()
        self.alive = False
        # worker_int callback
        self.cfg.worker_int(self)

        # sys.exit(0)

    def timeout_ctx(self):
        raise NotImplementedError()

    def handle(self, server_sock, client_sock, addr):
        """Handle client connection

        The client may send one or more requests.
        """
        req = None
        try:
            parser = http.RequestParser(self.cfg, client_sock)
            try:
                server_name = server_sock.getsockname()
                if not self.cfg.keepalive:
                    req = next(parser)
                    self.handle_request(server_name, req, client_sock, addr)
                else:
                    # keepalive loop
                    while True:
                        req = None
                        with self.timeout_ctx():
                            req = next(parser)
                        if not req:
                            break
                        self.handle_request(server_name, req, client_sock, addr)
                        gyield()
            except http.errors.NoMoreData as e:
                self.log.debug("Ignored premature client disconnection. %s", e)
            except StopIteration as e:
                self.log.debug("Closing connection. %s", e)
            except ssl.SSLError:
                exc_info = sys.exc_info()
                # pass to next try-except level
                reraise(exc_info[0], exc_info[1], exc_info[2])
            except socket.error:
                exc_info = sys.exc_info()
                # pass to next try-except level
                reraise(exc_info[0], exc_info[1], exc_info[2])
            except Exception as e:
                self.handle_error(req, client_sock, addr, e)
        except ssl.SSLError as e:
            if get_errno(e) == ssl.SSL_ERROR_EOF:
                self.log.debug("ssl connection closed")
                client_sock.close()
            else:
                self.log.debug("Error processing SSL request.")
                self.handle_error(req, client_sock, addr, e)
        except socket.error as e:
            if get_errno(e) not in BROKEN_SOCK:
                self.log.exception("Socket error processing request.")
            else:
                if get_errno(e) == errno.ECONNRESET:
                    self.log.debug("Ignoring connection reset")
                else:
                    self.log.debug("Ignoring EPIPE")
        except Exception as e:
            self.handle_error(req, client_sock, addr, e)
        finally:
            util.close(client_sock)

    def handle_request(self, listener_name, req, sock, addr):
        request_start = datetime.now()
        environ = {}
        resp = None
        try:
            self.cfg.pre_request(self, req)
            resp, environ = wsgi.create(req, sock, addr,
                                        listener_name, self.cfg)
            environ["wsgi.multithread"] = True
            self.nr += 1
            if self.alive and self.nr >= self.max_requests:
                self.log.info("Autorestarting worker after current request.")
                resp.force_close()
                self.alive = False

            if not self.cfg.keepalive:
                resp.force_close()

            respiter = self.wsgi(environ, resp.start_response)
            if respiter == ALREADY_HANDLED:
                return False
            try:
                if isinstance(respiter, environ['wsgi.file_wrapper']):
                    resp.write_file(respiter)
                else:
                    for item in respiter:
                        resp.write(item)
                resp.close()
                request_time = datetime.now() - request_start
                self.log.access(resp, req, environ, request_time)
            except socket.error as e:
                # BROKEN_SOCK not interesting here
                if not get_errno(e) in BROKEN_SOCK:
                    raise
            finally:
                if hasattr(respiter, "close"):
                    respiter.close()
            if resp.should_close():
                raise StopIteration()
        except StopIteration:
            raise
        except Exception:
            if resp and resp.headers_sent:
                # If the requests have already been sent, we should close the
                # connection to indicate the error.
                self.log.exception("Error handling request")
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                except socket.error:
                    pass
                raise StopIteration()
            raise
        finally:
            try:
                self.cfg.post_request(self, req, environ, resp)
            except Exception:
                self.log.exception("Exception in post_request hook")
        return True


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


def _guv_serve(sock, handle, concurrency):
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


def _guv_stop(client, server, conn):
    """Stop a greenlet handling a request and close its connection

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
        super().init_process()

    def timeout_ctx(self):
        return guv.Timeout(self.cfg.keepalive or None, False)

    def handle(self, server_sock, client_sock, addr):
        if self.cfg.is_ssl:
            client_sock = guv.wrap_ssl(client_sock, server_side=True, **self.cfg.ssl_options)

        super().handle(server_sock, client_sock, addr)

    def run(self):
        acceptors = []
        for sock in self.sockets:
            gsock = gsocket(sock.FAMILY, socket.SOCK_STREAM, fileno=sock.fileno())
            gsock.setblocking(1)
            hfun = partial(self.handle, gsock)
            acceptor = guv.spawn(_guv_serve, gsock, hfun, self.worker_connections)

            acceptors.append(acceptor)
            guv.gyield()

        try:
            while self.alive:
                self.notify()
                guv.sleep(self.timeout / 2)

        except (KeyboardInterrupt, SystemExit):
            log.debug('KeyboardInterrupt, exiting')

        self.notify()
        try:
            with guv.Timeout(self.cfg.graceful_timeout) as t:
                for a in acceptors:
                    a.kill(guv.StopServe())

                for a in acceptors:
                    a.wait()
        except guv.Timeout as te:
            if te != t:
                raise

            for a in acceptors:
                a.kill()

        log.debug('GuvWorker exited')
