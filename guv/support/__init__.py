import sys

PYPY = hasattr(sys, 'pypy_version_info')

OS_WINDOWS = sys.platform == 'win32'


def get_errno(e):
    """Get the error code out of socket.error objects
    """
    return e.args[0]


def reraise(tp, value, tb=None):
    if value is None:
        value = tp()
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value
