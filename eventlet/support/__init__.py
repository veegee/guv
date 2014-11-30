import sys
from contextlib import contextmanager
import io


def get_errno(exc):
    """Get the error code out of socket.error objects
    """
    try:
        if exc.errno is not None:
            return exc.errno
    except AttributeError:
        pass
    try:
        return exc.args[0]
    except IndexError:
        return None


def bytes_to_str(b, encoding='ascii'):
    return b.decode(encoding)


PY33 = sys.version_info[:2] == (3, 3)


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
