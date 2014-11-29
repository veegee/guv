from .. import patcher
from ..green import socket

to_patch = [('socket', socket)]

try:
    from ..green import ssl

    to_patch.append(('ssl', ssl))
except ImportError:
    pass

patcher.inject('http.client', globals(), *to_patch)
