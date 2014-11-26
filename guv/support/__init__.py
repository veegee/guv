import sys

PYPY = 'PyPy' in sys.version

OS_WINDOWS = sys.platform == 'win32'


def get_errno(e):
    """Get the error code out of socket.error objects
    """
    return e.args[0]
