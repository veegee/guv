import errno
import time
from types import FunctionType

from .. import patcher, sleep
from ..green import select
from ..fileobject import FileObject

patcher.inject('subprocess', globals(), ('select', select))
import subprocess as subprocess_orig

if getattr(subprocess_orig, 'TimeoutExpired', None) is None:
    # python < 3.3 needs this defined
    class TimeoutExpired(Exception):
        """This exception is raised when the timeout expires while waiting for a child process
        """

        def __init__(self, timeout, cmd, output=None):
            self.cmd = cmd
            self.output = output

        def __str__(self):
            return 'Command "{}" timed out after {} seconds'.format(self.cmd, self.timeout)


class Popen(subprocess_orig.Popen):
    """Greenified :class:`subprocess.Popen`
    """

    def __init__(self, args, bufsize=0, *argss, **kwds):
        if subprocess_orig.mswindows:
            raise Exception('Greenified Popen not supported on Windows')

        self.args = args
        super().__init__(args, 0, *argss, **kwds)

        for attr in 'stdin', 'stdout', 'stderr':
            pipe = getattr(self, attr)
            if pipe is not None and not type(pipe) == FileObject:
                wrapped_pipe = FileObject(pipe, pipe.mode, bufsize)
                setattr(self, attr, wrapped_pipe)

    def wait(self, timeout=None, check_interval=0.01):
        # Instead of a blocking OS call, this version of wait() uses logic
        # borrowed from the guv 0.2 processes.Process.wait() method.
        if timeout is not None:
            endtime = time.time() + timeout
        try:
            while True:
                status = self.poll()
                if status is not None:
                    return status
                if timeout is not None and time.time() > endtime:
                    raise TimeoutExpired(self.args, timeout)
                sleep(check_interval)
        except OSError as e:
            if e.errno == errno.ECHILD:
                # no child process, this happens if the child process
                # already died and has been cleaned up
                return -1
            else:
                raise

        # don't want to rewrite the original _communicate() method, we
        # just want a version that uses guv.green.select.select()
        # instead of select.select().
        _communicate = FunctionType(subprocess_orig.Popen._communicate.__code__, globals())
        try:
            _communicate_with_select = FunctionType(
                subprocess_orig.Popen._communicate_with_select.__code__, globals())
            _communicate_with_poll = FunctionType(
                subprocess_orig.Popen._communicate_with_poll.__code__, globals())
        except AttributeError:
            pass

    __init__.__doc__ = super().__init__.__doc__
    wait.__doc__ = super().wait.__doc__

# Borrow `subprocess.call()` and `check_call()`, but patch them so they reference
# the patched `Popen` class rather than `subprocess.Popen`
call = FunctionType(subprocess_orig.call.__code__, globals())
check_call = FunctionType(subprocess_orig.check_call.__code__, globals())
