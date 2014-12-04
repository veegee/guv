import select as select_orig

error = select_orig.error
from greenlet import getcurrent

from ..hubs import get_hub
from ..const import READ, WRITE

ERROR = 'error'

__patched__ = ['select']


def get_fileno(obj):
    # The purpose of this function is to exactly replicate
    # the behavior of the select module when confronted with
    # abnormal filenos; the details are extensively tested in
    # the stdlib test/test_select.py.
    try:
        f = obj.fileno
    except AttributeError:
        if not isinstance(obj, int):
            raise TypeError("Expected int or long, got " + type(obj))
        return obj
    else:
        rv = f()
        if not isinstance(rv, int):
            raise TypeError("Expected int or long, got " + type(rv))
        return rv


def select(read_list, write_list, error_list, timeout=None):
    # error checking like this is required by the stdlib unit tests
    if timeout is not None:
        try:
            timeout = float(timeout)
        except ValueError:
            raise TypeError('Expected number for timeout')

    hub = get_hub()
    timers = []
    current = getcurrent()
    assert hub is not current, 'do not call blocking functions from the mainloop'
    files = {}  # dict of socket objects or file descriptor integers
    for r in read_list:
        files[get_fileno(r)] = {READ: r}
    for w in write_list:
        files.setdefault(get_fileno(w), {})[WRITE] = w
    for e in error_list:
        files.setdefault(get_fileno(e), {})[ERROR] = e

    listeners = []

    def on_read(d):
        original = files[get_fileno(d)][READ]
        current.switch(([original], [], []))

    def on_write(d):
        original = files[get_fileno(d)][WRITE]
        current.switch(([], [original], []))

    def on_error(d, _err=None):
        original = files[get_fileno(d)][ERROR]
        current.switch(([], [], [original]))

    def on_timeout2():
        current.switch(([], [], []))

    def on_timeout():
        timers.append(hub.schedule_call_global(0, on_timeout2))

    if timeout is not None:
        timers.append(hub.schedule_call_global(timeout, on_timeout))
    try:
        for fd, v in files.items():
            if v.get(READ):
                listeners.append(hub.add(READ, fd, on_read, on_error, (fd,)))
            if v.get(WRITE):
                listeners.append(hub.add(WRITE, fd, on_write, on_error, (fd,)))
        try:
            return hub.switch()
        finally:
            for l in listeners:
                hub.remove(l)
    finally:
        for t in timers:
            t.cancel()
