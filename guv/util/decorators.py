import logging
from functools import wraps
import inspect
import re

log = logging.getLogger('guv')

use_newlines = False
indent = '    '  # indent character(s)
max_param_len = 20
log_function_start = True  # log when the function is called
log_function_exit = True  # log when the function exits

# colour constants
RESET = '\x1B[0m'  # INFO
RED = '\x1B[31m'  # ERROR, CRITICAL, FATAL
GREEN = '\x1B[32m'  # INFO
YELLOW = '\x1B[33m'  # WARNING
BLUE = '\x1B[34m'  # INFO
MAGENTA = '\x1B[35m'  # INFO
CYAN = '\x1B[36m'  # INFO
WHITE = '\x1B[37m'  # INFO
BRGREEN = '\x1B[01;32m'  # DEBUG (grey in solarized for terminals)

# regex for extracting from <bound method A.sayhi of <__main__.A object at 0x7fc54e28be80>>
r_of = re.compile('<.*(?= of <)')

# regex for extracting from <__main__.A object at 0x7fc54e28be80>
r_at = re.compile('<.*(?= at )')


def parse_repr(obj):
    if inspect.ismethod(obj):
        pat = r_of
    else:
        pat = r_at

    s = repr(obj)
    m = re.search(pat, s)
    if m:
        return '{}>'.format(m.group())
    else:
        return s


def format_arg(arg):
    """Convert `arg` to a string

    If arg is a simple object,
    """
    s = str(arg)
    if type(arg) is type:
        # convert to string directly; the string isn't very long
        return s
    elif isinstance(arg, object) and len(s) > max_param_len:
        # format into a shorter representation
        return parse_repr(arg)
    else:
        # the string representation of `arg` is short enough to display directly
        return s


def func_name(f):
    """Get qualified name of function

    :param f: function
    """
    if hasattr(f, '__qualname__'):
        # for Python >= 3.3
        qualname = RESET + f.__qualname__ + BRGREEN
    else:
        # for Python < 3.3
        qualname = RESET + f.__name__ + BRGREEN

    return qualname


def log_start(f, args, kwargs):
    argspec = inspect.getargspec(f)

    # check if this is a function or a method
    method = False
    if argspec.args and argspec.args[0] == 'self':
        method = True

    qualname = func_name(f)

    f_name = '.'.join([f.__module__, qualname])

    if method:
        args_list = ['(self=){}'.format(format_arg(args[0]))]
    else:
        args_list = []

    # function args
    if method:
        args_list += list(map(format_arg, args[1:]))
    else:
        args_list += list(map(format_arg, args))

    # function kwargs
    args_list += list(map(lambda key: '{}={}'.format(key, format_arg(kwargs[key])), kwargs))

    if use_newlines:
        f_args = ',\n{i}{i}'.format(i=indent).join(args_list)
        if f_args:
            log.debug('\n{i}{f_name}(\n{i}{i}{f_args}\n{i})'
                      .format(i=indent, f_name=f_name, f_args=f_args))
        else:
            log.debug('\n{i}{f_name}()'.format(i=indent, f_name=f_name))
    else:
        f_args = ', '.join(args_list)
        log.debug('{f_name}({f_args})'.format(f_name=f_name, f_args=f_args))


def log_exit(f):
    f_name = '.'.join([f.__module__, func_name(f)])

    log.debug('..done: {}'.format(f_name))


def logged(f):
    """Decorator which logs the name of the function called"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if log_function_start:
            log_start(f, args, kwargs)

        ret = f(*args, **kwargs)

        if log_function_exit:
            log_exit(f)

        return ret

    return wrapper
