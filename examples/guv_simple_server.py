"""Simple low-level network server

This module demonstrates how to use guv to create fast network servers. In addition, it can be
used to serve valid HTTP (as far as ``wrk`` is concerned) to benchmark concurrency and requests/sec.

Three basic client handlers are provided:

- :func:`handle_http_10` acts as an HTTP 1.0 server which sends a static message and closes the
  connection (HTTP header ``Connection: close``, which is default for HTTP 1.0).
- :func:`handle_http_11` acts as an HTTP 1.1 server which sends a static message, but keeps the
  connection alive (HTTP header ``Connection: keep-alive``, which is default for HTTP 1.1).
- :func:`handle_http` is a slightly more complex client handler which actually reads the client's
  request and decides to either close or keep-alive the connection based on the HTTP version and
  what the client wants. If the connection is to be kept alive, this handler cooperatively yields
  control to other greenlets after every request, which significantly improves request/response
  latency (as reported by wrk).
"""
import guv
guv.monkey_patch()

import guv.server
import guv.hubs
import guv.greenio
from guv import gyield
from guv.support import PYPY

import logging

import logger

logger.configure()
log = logging.getLogger()

if PYPY:
    from http_parser.pyparser import HttpParser

    log.debug('Using pure-Python HTTP parser')
    USING_PYPARSER = True
else:
    from http_parser.parser import HttpParser

    log.debug('Using fast C HTTP parser')
    USING_PYPARSER = False


def create_response(body, headers):
    """Create a simple HTTP response

    :type body: str
    :type headers: dict[str, str]
    :rtype: bytes
    """
    final_headers = {
        'Connection': 'keep-alive',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Encoding': 'UTF-8'
    }

    final_headers.update(headers)

    lines = ['HTTP/1.1 200 OK']
    lines.extend(['%s: %s' % (k, v) for k, v in final_headers.items()])
    lines.append('Content-Length: %s' % len(body))

    resp = ('\r\n'.join(lines)).encode('latin-1')
    resp += ('\r\n\r\n' + body).encode(final_headers['Content-Encoding'])

    return resp


def handle_http_10(sock, addr):
    """Very minimal client handler for HTTP 1.0 (Connection: close)
    """
    data = sock.recv(4096)
    if not data:
        return
    resp = create_response('Hello, world!', {'Connection': 'close'})
    sock.sendall(resp)

    sock.close()


def handle_http_11(sock, addr):
    """Very minimal client handler for HTTP 1.1 (Connection: keep-alive)
    """
    while True:
        data = sock.recv(4096)
        if not data:
            break
        resp = create_response('Hello, world!', {'Connection': 'keep-alive'})
        sock.sendall(resp)

    sock.close()


def handle_http(sock, addr):
    """A more complicated handler which detects HTTP headers
    """

    def recv_request(p):
        while True:
            data = sock.recv(8192)

            if not data:
                return False

            nb = len(data)
            nparsed = p.execute(data, nb)
            assert nparsed == nb

            if USING_PYPARSER and p.is_headers_complete():
                h = p.get_headers()
                if not (h.get('content-length') or h.get('transfer-length')):
                    # pass length=0 to signal end of body
                    # TODO: pyparser requires this, but not the C parser for some reason
                    p.execute(data, 0)
                    return True

            if p.is_message_complete():
                return True

    # main request loop
    while True:
        p = HttpParser()

        if not recv_request(p):
            break

        h = p.get_headers()
        ka = p.should_keep_alive()
        h_connection = 'keep-alive' if ka else 'close'

        resp = create_response('Hello, world!', {'Connection': h_connection})
        sock.sendall(resp)

        if not ka:
            break
        else:
            # we should keep-alive, but yield to drastically improve overall request/response
            # latency
            gyield()

    sock.close()


handle = handle_http


def main():
    try:
        log.debug('Start')
        server_sock = guv.listen(('0.0.0.0', 8001))
        server = guv.server.Server(server_sock, handle, None, None)
        server.start()
    except (SystemExit, KeyboardInterrupt):
        log.debug('Bye!')


if __name__ == '__main__':
    main()
