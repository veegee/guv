import traceback
import io
import greenlet
import time
import functools

from . import abc
from guv import compat

_g_debug = False  # if true, captures a stack trace for each timer when constructed, this is useful
# for debugging leaking timers, to find out where the timer was set up

compat.patch()


@functools.total_ordering
class Timer(abc.AbstractTimer):
    """Simple Timer class for setting up a callback to be called after the specified amount of time
    has passed

    Calling the timer object will call the callback
    """

    def __init__(self, seconds, cb, *args, **kwargs):
        """
        :param float seconds: minimum number of seconds to wait before calling
        :param Callable cb: callback to call when the timer has expired
        :param args: positional arguments to pass to cb
        :param kwargs: keyword arguments to pass to cb

        This timer will not be run unless it is scheduled calling :meth:`schedule`.
        """
        self.seconds = seconds
        self.absolute_time = time.monotonic() + seconds  # absolute time to fire the timer
        self.tpl = cb, args, kwargs

        self.called = False

        if _g_debug:
            self.traceback = io.StringIO()
            traceback.print_stack(file=self.traceback)

    @property
    def pending(self):
        return not self.called

    def __repr__(self):
        secs = getattr(self, 'seconds', None)
        cb, args, kw = getattr(self, 'tpl', (None, None, None))
        retval = "Timer(%s, %s, *%s, **%s)" % (
            secs, cb, args, kw)
        if _g_debug and hasattr(self, 'traceback'):
            retval += '\n' + self.traceback.getvalue()
        return retval

    def copy(self):
        cb, args, kw = self.tpl
        return self.__class__(self.seconds, cb, *args, **kw)

    def cancel(self):
        self.called = True

    def __call__(self, *args):
        if not self.called:
            self.called = True
            cb, args, kw = self.tpl
            try:
                cb(*args, **kw)
            finally:
                try:
                    del self.tpl
                except AttributeError:
                    pass

    def __lt__(self, other):
        """
        No default ordering in Python 3.x; heapq uses <

        :type other: Timer
        """
        if isinstance(other, float):
            return self.absolute_time < other
        else:
            return self.absolute_time < other.absolute_time


class LocalTimer(Timer):
    def __init__(self, seconds, cb, *args, **kwargs):
        self.greenlet = greenlet.getcurrent()
        super().__init__(seconds, cb, *args, **kwargs)

    @property
    def pending(self):
        if self.greenlet is None or self.greenlet.dead:
            return False
        return not self.called

    def __call__(self, *args):
        if not self.called:
            self.called = True
            if self.greenlet is not None and self.greenlet.dead:
                return
            cb, args, kw = self.tpl
            cb(*args, **kw)

    def cancel(self):
        self.greenlet = None
        super().cancel()
