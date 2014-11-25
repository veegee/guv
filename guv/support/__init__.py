import sys
from contextlib import contextmanager
import io


def get_errno(e):
    """Get the error code out of socket.error objects
    """
    return e.args[0]


def bytes_to_str(b, encoding='ascii'):
    return b.decode(encoding)


# TODO: find usages and inline this variable
PY33 = sys.version_info[:2] == (3, 3)

PYPY = 'PyPy' in sys.version


@contextmanager
def capture_stderr():
    stream = io.StringIO
    original = sys.stderr
    try:
        sys.stderr = stream
        yield stream
    finally:
        sys.stderr = original
        stream.seek(0)
