import sys
import time
import traceback
import logging
import socket
import wsgiref.headers

from . import version_info, gyield
from .server import Server
from .support import PYPY
from .exceptions import BROKEN_SOCK

if PYPY:
    raise Exception('pypy3 currently not supported; TODO: create CFFI wrapper for http-parser')

from http_parser.parser import HttpParser

log = logging.getLogger('guv.wsgi')
log.setLevel(logging.INFO)

DEFAULT_MAX_SIMULTANEOUS_REQUESTS = 1024
DEFAULT_MAX_HTTP_VERSION = 'HTTP/1.1'
MAX_REQUEST_LINE = 8192
MAX_HEADER_LINE = 8192
MAX_TOTAL_HEADER_SIZE = 65536
MINIMUM_CHUNK_SIZE = 4096

__all__ = ['serve', 'format_date_time']

# weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None,  # dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_INTERNAL_ERROR_STATUS = '500 Internal Server Error'
_INTERNAL_ERROR_BODY = 'Internal Server Error'
_INTERNAL_ERROR_HEADERS = [('Content-Type', 'text/plain'),
                           ('Connection', 'close'),
                           ('Content-Length', str(len(_INTERNAL_ERROR_BODY)))]
_REQUEST_TOO_LONG_RESPONSE = "HTTP/1.1 414 Request URI Too Long\r\n" \
                             "Connection: close\r\nContent-length: 0\r\n\r\n"
_BAD_REQUEST_RESPONSE = "HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-length: 0\r\n\r\n"
_CONTINUE_RESPONSE = "HTTP/1.1 100 Continue\r\n\r\n"


def b(s):
    return s.encode('latin-1')


def format_date_time(timestamp):
    """Format a unix timestamp into an HTTP standard string
    """
    year, month, day, hh, mm, ss, wd, _y, _z = time.gmtime(timestamp)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % \
           (_weekdayname[wd], day, _monthname[month], year, hh, mm, ss)


class Input:
    def __init__(self, rfile, content_length, socket=None, chunked_input=False):
        self.rfile = rfile
        self.content_length = content_length
        self.socket = socket
        self.position = 0
        self.chunked_input = chunked_input
        self.chunk_length = -1

    def _discard(self):
        if self.socket is None and \
                (self.position < (self.content_length or 0) or self.chunked_input):
            # read and discard body
            while 1:
                d = self.read(16384)
                if not d:
                    break

    def _send_100_continue(self):
        if self.socket is not None:
            self.socket.sendall(_CONTINUE_RESPONSE)
            self.socket = None

    def _do_read(self, length=None, use_readline=False):
        if use_readline:
            reader = self.rfile.readline
        else:
            reader = self.rfile.read
        content_length = self.content_length
        if content_length is None:
            # Either Content-Length or "Transfer-Encoding: chunked" must be present in a request
            # with a body if it was chunked, then this function would have not been called
            return ''
        self._send_100_continue()
        left = content_length - self.position
        if length is None:
            length = left
        elif length > left:
            length = left
        if not length:
            return ''
        read = reader(length)
        self.position += len(read)
        if len(read) < length:
            if (use_readline and not read.endswith("\n")) or not use_readline:
                raise IOError("unexpected end of file while reading request at position {}"
                              .format(self.position))

        return read

    def _chunked_read(self, length=None, use_readline=False):
        rfile = self.rfile
        self._send_100_continue()

        if length == 0:
            return ""

        if length < 0:
            length = None

        if use_readline:
            reader = self.rfile.readline
        else:
            reader = self.rfile.read

        response = []
        while self.chunk_length != 0:
            maxreadlen = self.chunk_length - self.position
            if length is not None and length < maxreadlen:
                maxreadlen = length

            if maxreadlen > 0:
                data = reader(maxreadlen)
                if not data:
                    self.chunk_length = 0
                    raise IOError("unexpected end of file while parsing chunked data")

                datalen = len(data)
                response.append(data)

                self.position += datalen
                if self.chunk_length == self.position:
                    rfile.readline()

                if length is not None:
                    length -= datalen
                    if length == 0:
                        break
                if use_readline and data[-1] == "\n":
                    break
            else:
                line = rfile.readline()
                if not line.endswith("\n"):
                    self.chunk_length = 0
                    raise IOError("unexpected end of file while reading chunked data header")
                self.chunk_length = int(line.split(";", 1)[0], 16)
                self.position = 0
                if self.chunk_length == 0:
                    rfile.readline()
        return ''.join(response)

    def read(self, length=None):
        if self.chunked_input:
            return self._chunked_read(length)
        return self._do_read(length)

    def readline(self, size=None):
        if self.chunked_input:
            return self._chunked_read(size, True)
        else:
            return self._do_read(size, use_readline=True)

    def readlines(self, hint=None):
        return list(self)

    def __iter__(self):
        return self

    def next(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line


class WSGIHandler:
    def __init__(self, sock, addr, app, environ):
        """
        :param sock: client socket
        :param addr: address information
        :param app: WSGI application
        :type addr: tuple[str, int]
        :type sock: socket.socket
        :type app: Callable(dict, Callable)
        """
        self.sock = sock
        self.addr = addr
        self.app = app
        self.environ = environ

        # request data
        self.req_headers = {}

        # response data
        self.resp_status = ''
        self.resp_headers = wsgiref.headers.Headers([])

    def create_response(self, body):
        """
        :type body: list[bytes]
        :type headers: dict
        :rtype: str
        """
        lines = ['HTTP/1.1 200 OK']
        lines.extend(['%s: %s' % (k, v) for k, v in self.resp_headers.items()])
        lines.append('Content-Length: %s' % len(body))

        resp = ('\r\n'.join(lines)).encode('latin-1')
        resp += ('\r\n\r\n' + body).encode(final_headers['Content-Encoding'])

        return resp

    def handle(self):
        sock = self.sock

        # main request loop
        while True:
            p = HttpParser()

            if not self.recv_request(p):
                break

            self.req_headers = p.get_headers()
            ka = p.should_keep_alive()
            h_connection = 'keep-alive' if ka else 'close'
            self.resp_headers.add_header('Connection', h_connection)

            # TODO: p.get_wsgi_environ() is very slow for some reason
            self.environ.update(p.get_wsgi_environ())

            result = self.app(self.environ, self.start_response)

            resp = self.create_response(result)
            sock.sendall(resp)

            if not ka:
                break
            else:
                # we should keep-alive, but yield to drastically improve
                # overall request/response latency
                gyield()

        sock.close()

    def recv_request(self, p):
        sock = self.sock

        while True:
            data = sock.recv(8192)

            if not data:
                return False

            nb = len(data)
            nparsed = p.execute(data, nb)
            assert nparsed == nb

            if p.is_message_complete():
                return True

    def start_response(self, status, headers, exc_info=None):
        """Start creating the HTTP response

        This is the method passed to the WSGI application.

        :param status: HTTP status code
        :param headers: list of headers
        :param exc_info: exception info, in the form of sys.exc_info()
        :type status: str
        :type headers: list[tuple[str, str]]
        :type exc_info: tuple or None
        :rtype: Callable
        """
        self.resp_status = status

        for k, v in headers:
            self.resp_headers.add_header(k, v)

        return self.write

    def write(self, data):
        self.sock.send(data)


class WSGIServer(Server):
    #: :type: tuple
    server_version = version_info[:2] + sys.version_info[:2]

    base_env = {
        'SERVER_SOFTWARE': 'guv/%d.%d Python/%d.%d' % server_version,
        'SCRIPT_NAME': '',
        'wsgi.version': (1, 0),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False
    }

    def __init__(self, server_sock, application=None, environ=None):
        super().__init__(server_sock, self.handle_client)

        self.application = application
        self.environ = None

        self.set_environ(environ)

    def set_environ(self, environ=None):
        if environ is not None:
            self.environ = environ

        environ_update = getattr(self, 'environ', None)
        self.environ = self.base_env.copy()
        self.environ['wsgi.url_scheme'] = 'http'

        if environ_update is not None:
            self.environ.update(environ_update)

        if self.environ.get('wsgi.errors') is None:
            self.environ['wsgi.errors'] = sys.stderr

        address = self.address
        if isinstance(address, tuple):
            if 'SERVER_NAME' not in self.environ:
                try:
                    name = socket.getfqdn(address[0])
                except socket.error:
                    name = str(address[0])
                self.environ['SERVER_NAME'] = name
            self.environ.setdefault('SERVER_PORT', str(address[1]))
        else:
            self.environ.setdefault('SERVER_NAME', '')
            self.environ.setdefault('SERVER_PORT', '')

    def get_environ(self):
        return self.environ.copy()

    def handle_client(self, client_sock, address):
        handler = WSGIHandler(client_sock, address, self.application, self.get_environ())
        handler.handle()


def serve(server_sock, app):
    """Start up a WSGI server handling requests from the supplied server socket

    This function loops forever. The `sock` object will be closed after server exits, but the
    underlying file descriptor will remain open, so if you have a dup() of *sock*, it will remain
    usable.

    :param server_sock: server socket, must be already bound to a port and listening
    :param app: WSGI application callable
    """
    try:
        host, port = server_sock.getsockname()[:2]
        log.info('WSGI server starting up on {}:{}'.format(host, port))

        wsgi_server = WSGIServer(server_sock, app)
        wsgi_server.start()

    except (KeyboardInterrupt, SystemExit):
        log.debug('KeyboardInterrupt, exiting')
    finally:
        log.debug('WSGI server exited')
        try:
            server_sock.close()
        except socket.error as e:
            if e.args[0] not in BROKEN_SOCK:
                traceback.print_exc()
