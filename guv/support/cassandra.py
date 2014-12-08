from collections import defaultdict
import logging

from cassandra import OperationTimedOut
from cassandra.connection import Connection, ConnectionShutdown
from cassandra.protocol import RegisterMessage

import guv.hubs
from guv import trampoline
from guv.green import socket, ssl
from guv.event import TEvent
from guv.queue import Queue
from guv.support import get_errno
from guv.exceptions import CONNECT_ERR
from guv.const import READ, WRITE

log = logging.getLogger(__name__)


class GuvConnection(Connection):
    """
    An implementation of :class:`.Connection` that utilizes ``guv``.
    """

    _total_reqd_bytes = 0
    _read_watcher = None
    _write_watcher = None
    _socket = None

    @classmethod
    def factory(cls, *args, **kwargs):
        timeout = kwargs.pop('timeout', 5.0)
        conn = cls(*args, **kwargs)
        conn.connected_event.wait(timeout)
        if conn.last_error:
            raise conn.last_error
        elif not conn.connected_event.is_set():
            conn.close()
            raise OperationTimedOut('Timed out creating connection')
        else:
            return conn

    def __init__(self, *args, **kwargs):
        guv.hubs.get_hub()

        super().__init__(*args, **kwargs)

        self.connected_event = TEvent()
        self._write_queue = Queue()

        self._callbacks = {}
        self._push_watchers = defaultdict(set)

        sockerr = None
        addresses = socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for (af, socktype, proto, canonname, sockaddr) in addresses:
            try:
                self._socket = socket.socket(af, socktype, proto)
                if self.ssl_options:
                    self._socket = ssl.wrap_socket(self._socket, **self.ssl_options)
                self._socket.settimeout(1.0)
                self._socket.connect(sockaddr)
                sockerr = None
                break
            except socket.error as err:
                sockerr = err
        if sockerr:
            msg = 'Tried connecting to {}. Last error: {}'.format([a[4] for a in addresses],
                                                                  sockerr.strerror)
            raise socket.error(sockerr.errno, msg)

        if self.sockopts:
            for args in self.sockopts:
                self._socket.setsockopt(*args)

        self._read_watcher = guv.spawn(self.handle_read)
        self._write_watcher = guv.spawn(self.handle_write)
        self._send_options_message()

        log.debug('Create Cassandra GuvConnection ({})'.format(id(self)))

    def close(self):
        with self.lock:
            if self.is_closed:
                return
            self.is_closed = True

        log.debug('Closing connection (%s) to %s' % (id(self), self.host))
        if self._read_watcher:
            self._read_watcher.kill()
        if self._write_watcher:
            self._write_watcher.kill()
        if self._socket:
            self._socket.close()
        log.debug('Closed socket to %s' % (self.host,))

        if not self.is_defunct:
            self.error_all_callbacks(ConnectionShutdown('Connection to %s was closed' % self.host))
            # don't leave in-progress operations hanging
            self.connected_event.set()

    def handle_close(self):
        log.debug('connection closed by server')
        self.close()

    def handle_write(self):
        while True:
            try:
                next_msg = self._write_queue.get()
                # FIXME: trampoline with WRITE here causes a core dump (why???)
                # python: src/unix/core.c:823: uv__io_stop: Assertion `loop->watchers[w->fd] ==
                # w' failed.
                # [1]    9736 abort (core dumped)  python cassandra_db.py
                # log.debug('Trampoline on fd: {}, WRITE'.format(self._socket.fileno()))
                # trampoline(self._socket.fileno(), WRITE)
            except Exception as e:
                if not self.is_closed:
                    log.debug('Exception during write trampoline() for %s: %s', self, e)
                    self.defunct(e)
                return

            try:
                self._socket.sendall(next_msg)
            except socket.error as err:
                log.debug('Exception during socket sendall for %s: %s', self, err)
                self.defunct(err)
                return  # leave the write loop

    def handle_read(self):
        while True:
            try:
                log.debug('Trampoline on fd: {}, READ'.format(self._socket.fileno()))
                trampoline(self._socket.fileno(), READ)
            except Exception as exc:
                if not self.is_closed:
                    log.debug("Exception during read trampoline() for %s: %s", self, exc)
                    self.defunct(exc)
                    return

            try:
                while True:
                    buf = self._socket.recv(self.in_buffer_size)
                    self._iobuf.write(buf)
                    if len(buf) < self.in_buffer_size:
                        break
            except socket.error as err:
                if not get_errno(err) in CONNECT_ERR:
                    log.debug('Exception during socket recv for %s: %s', self, err)
                    self.defunct(err)
                    return  # leave the read loop

            if self._iobuf.tell():
                self.process_io_buffer()
            else:
                log.debug('Connection %s closed by server', self)
                self.close()
                return

    def push(self, data):
        chunk_size = self.out_buffer_size
        for i in range(0, len(data), chunk_size):
            self._write_queue.put(data[i:i + chunk_size])

    def register_watcher(self, event_type, callback, register_timeout=None):
        self._push_watchers[event_type].add(callback)
        self.wait_for_response(RegisterMessage(event_list=[event_type]),
                               timeout=register_timeout)

    def register_watchers(self, type_callback_dict, register_timeout=None):
        for event_type, callback in type_callback_dict.items():
            self._push_watchers[event_type].add(callback)

        self.wait_for_response(RegisterMessage(event_list=type_callback_dict.keys()),
                               timeout=register_timeout)
