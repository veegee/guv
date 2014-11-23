"""pyuv_cffi - an implementation of pyuv via CFFI

Compatible with Python 3 and pypy3
"""
import os

import cffi
import cffi.verifier

__version__ = '0.1.0'
version_info = tuple(map(int, __version__.split('.')))

# clean up old compiled library binaries (not needed in production?)
cffi.verifier.cleanup_tmpdir()

# load FFI definitions and custom C code
ffi = cffi.FFI()
with open(os.path.join(os.path.dirname(__file__), 'pyuv_cffi_cdef.c')) as f:
    ffi.cdef(f.read())

with open(os.path.join(os.path.dirname(__file__), 'pyuv_cffi.c')) as f:
    libuv = ffi.verify(f.read(), libraries=['uv'])


class Loop:
    def __init__(self):
        self.loop_h = libuv.pyuv_loop_new()
        self._loop_h_allocated = True
        self._handles = []

    @classmethod
    def default_loop(cls):
        loop = Loop.__new__(cls)
        loop.loop_h = libuv.uv_default_loop()
        loop.loop_h_allocated = False  # the default loop can't be freed
        return loop

    @property
    def alive(self):
        return bool(libuv.uv_loop_alive(self.loop_h))

    @property
    def handles(self):
        # TODO: implement this method
        return self._handles

    def run(self, mode=libuv.UV_RUN_DEFAULT):
        return libuv.uv_run(self.loop_h, mode)

    def stop(self):
        libuv.uv_stop(self.loop_h)

    def _free(self):
        if self._loop_h_allocated:
            libuv.pyuv_loop_del(self.loop_h)
            self._loop_h_allocated = False

    def __del__(self):
        # free the memory allocated by libuv.pyuv_loop_new()
        self._free()


class Handle:
    def __init__(self, handle):
        #: uv_handle_t
        self.uv_handle = libuv.cast_handle(handle)

        self._ffi_close_cb = None

    @property
    def ref(self):
        return bool(libuv.uv_has_ref(self.uv_handle))

    @ref.setter
    def ref(self, value):
        if value:
            libuv.uv_ref(self.uv_handle)
        else:
            libuv.uv_unref(self.uv_handle)

    @property
    def active(self):
        return bool(libuv.uv_is_active(self.uv_handle))

    @property
    def closing(self):
        """
        :return: True if handle is closing or closed, False otherwise
        """
        return bool(libuv.uv_is_closing(self.uv_handle))

    def close(self, callback=None):
        """Close uv handle

        :type callback: Callable(uv_handle: Handle) or None
        """
        if self.closing:
            return

        def cb_wrapper(uv_handle_t):
            if callback:
                callback(self)

        self._ffi_close_cb = ffi.callback('void(*)(uv_handle_t *)', cb_wrapper)
        libuv.uv_close(self.uv_handle, self._ffi_close_cb)


class Timer(Handle):
    def __init__(self, loop):
        self.loop = loop
        self.handle = libuv.pyuv_timer_new(loop.loop_h)
        super().__init__(self.handle)

        self._handle_allocated = True
        self._repeat = None
        self._ffi_cb = None

    @property
    def repeat(self):
        # TODO: implement this method
        return self._repeat

    @repeat.setter
    def repeat(self, timeout):
        # TODO implement this method
        self._repeat = timeout

    def start(self, callback, timeout, repeat):
        """
        :type callback: Callable(timer_handle: Timer)
        :param float timeout: initial timeout (seconds) before first alarm
        :param float repeat: repeat interval (seconds); 0 to disable
        """
        timeout = int(timeout * 1000)
        repeat = int(repeat * 1000)

        def cb_wrapper(timer_h):
            callback(self)

        ffi_cb = ffi.callback('void(*)(uv_timer_t *)', cb_wrapper)
        self._ffi_cb = ffi_cb
        libuv.uv_timer_start(self.handle, ffi_cb, timeout, repeat)

    def stop(self):
        self._ffi_cb = None
        libuv.uv_timer_stop(self.handle)

    def _free(self):
        self.stop()
        self.close()
        self._ffi_cb = None
        if self._handle_allocated:
            libuv.pyuv_timer_del(self.handle)
            self._handle_allocated = False

    def __del__(self):
        self._free()


class Signal(Handle):
    def __init__(self, loop):
        self.loop = loop
        self.handle = libuv.pyuv_signal_new(loop.loop_h)
        super().__init__(self.handle)

        self._handle_allocated = True
        self._ffi_cb = None  # FFI callbacks need to be kept alive in order to be valid

    def start(self, callback, sig_num):
        """Start the signal listener

        :type callback: Callable(sig_handle: Signal, sig_num: int)
        :type sig_num: int
        """

        def cb_wrapper(uv_signal_t, signum):
            callback(self, signum)

        ffi_cb = ffi.callback('void(*)(uv_signal_t *, int)', cb_wrapper)
        self._ffi_cb = ffi_cb  # keep the FFI cdata object alive as long as this instance is alive
        libuv.uv_signal_start(self.handle, ffi_cb, sig_num)

    def stop(self):
        self._ffi_cb = None  # remove reference to the cdata object (it will be freed automatically)
        libuv.uv_signal_stop(self.handle)

    def _free(self):
        self.stop()
        self._ffi_cb = None
        if self._handle_allocated:
            libuv.pyuv_signal_del(self.handle)
            self._handle_allocated = False

    def __del__(self):
        self.stop()
        self._free()


class Poll(Handle):
    def __init__(self, loop, fd):
        super().__init__()
        self._poll_handle = libuv.pyuv_poll_new(loop.loop_h, fd)

    def start(self, events, cb):
        return NotImplemented

    def stop(self):
        return NotImplemented


def sig_cb(sig_h, sig_num):
    print('\nsig_cb({}, {})'.format(sig_h, sig_num))
    sig_h.stop()
    sig_h.loop.stop()


def timer_cb(timer_h):
    print('timer_cb({})'.format(timer_h))


def run():
    import signal

    loop = Loop()

    timer_h = Timer(loop)
    timer_h.start(timer_cb, 1, 1)

    sig_h = Signal(loop)
    sig_h.start(sig_cb, signal.SIGINT)

    status = loop.run()

    timer_h.close()  # stop and free any timers before freeing the loop
    print('loop.run() -> ', status)
