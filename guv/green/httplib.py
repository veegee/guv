from guv import patcher
from guv.green import socket

to_patch = [('socket', socket)]

try:
    from guv.green import ssl

    to_patch.append(('ssl', ssl))
except ImportError:
    pass

patcher.inject('http.client', globals(), *to_patch)
