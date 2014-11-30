socket_orig = __import__('socket')
os = __import__('os')

__all__ = socket_orig.__all__
__patched__ = ['fromfd', 'socketpair', 'ssl', 'socket']

import ssl

from ..patcher import copy_attributes

copy_attributes(socket_orig, globals(),
                ignore=__patched__, srckeys=dir(socket_orig))

from ..greenio import socket

try:
    _fromfd_orig = socket_orig.fromfd

    def fromfd(*args):
        return socket(_fromfd_orig(*args))
except AttributeError:
    pass

try:
    _socketpair_orig = socket_orig.socketpair

    def socketpair(*args):
        one, two = _socketpair_orig(*args)
        return socket(one), socket(two)
except AttributeError:
    pass


class GreenSSLObject:
    """ Wrapper object around the SSLObjects returned by socket.ssl, which have a
    slightly different interface from SSL.Connection objects. """

    def __init__(self, green_ssl_obj):
        """ Should only be called by a 'green' socket.ssl """
        self.connection = green_ssl_obj
        try:
            # if it's already connected, do the handshake
            self.connection.getpeername()
        except:
            pass
        else:
            try:
                self.connection.do_handshake()
            except ssl.SSLSyscallError as e:
                raise

    def read(self, n=1024):
        """If n is provided, read n bytes from the SSL connection, otherwise read
        until EOF. The return value is a string of the bytes read."""
        try:
            return self.connection.read(n)
        except ssl.SSLZeroReturnError:
            return ''
        except ssl.SSLSyscallError as e:
            raise

    def write(self, s):
        """Writes the string s to the on the object's SSL connection.
        The return value is the number of bytes written. """
        try:
            return self.connection.write(s)
        except ssl.SSLSyscallError as e:
            raise

    def server(self):
        """ Returns a string describing the server's certificate. Useful for debugging
        purposes; do not parse the content of this string because its format can't be
        parsed unambiguously. """
        return str(self.connection.get_peer_certificate().get_subject())

    def issuer(self):
        """Returns a string describing the issuer of the server's certificate. Useful
        for debugging purposes; do not parse the content of this string because its
        format can't be parsed unambiguously."""
        return str(self.connection.get_peer_certificate().get_issuer())
