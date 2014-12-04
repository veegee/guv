import sys
from ..patcher import copy_attributes

if sys.version_info >= (3, 3):
    from . import _ssl33

    copy_attributes(_ssl33, globals(), srckeys=dir(_ssl33))
else:
    # Python 3.2
    from . import _ssl32

    copy_attributes(_ssl32, globals(), srckeys=dir(_ssl32))

__patched__ = ['SSLContext', 'SSLSocket', 'wrap_socket', 'get_server_certificate']
