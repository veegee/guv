"""pyuv_cffi - an implementation of pyuv via CFFI

Compatible with CPython 3 and pypy3
"""
import os
import functools

import cffi
import cffi.verifier
from cffi import VerificationError

__version__ = '0.1.0'
version_info = tuple(map(int, __version__.split('.')))

# clean up old compiled library binaries (not needed in production?)
cffi.verifier.cleanup_tmpdir()

thisdir = os.path.dirname(os.path.realpath(__file__))

# load FFI definitions and custom C code
ffi = cffi.FFI()
with open(os.path.join(thisdir, 'pyuv_cffi_cdef.c')) as f:
    ffi.cdef(f.read())

try:
    with open(os.path.join(thisdir, 'pyuv_cffi.c')) as f:
        libuv = ffi.verify(f.read(), libraries=['uv'])
except VerificationError as e:
    print(e)
    exit(1)

UV_READABLE = libuv.UV_READABLE
UV_WRITABLE = libuv.UV_WRITABLE

UV_RUN_DEFAULT = libuv.UV_RUN_DEFAULT
UV_RUN_ONCE = libuv.UV_RUN_ONCE
UV_RUN_NOWAIT = libuv.UV_RUN_NOWAIT

alive = []


class Loop:
    def __init__(self):
        self.loop_h = ffi.new('uv_loop_t *')
        libuv.uv_loop_init(self.loop_h)

        self._handles = []  # temporary list of Handle objects
        self._ffi_walk_cb = ffi.callback('void (*)(uv_handle_t *handle, void *arg)', self._walk_cb)

    def _walk_cb(self, handle_p, arg):
        """Callback passed to uv_walk()

        Note: the handle_p cdata object is appended to `self._handles`, and the list is destroyed
        afterwards, to prevent storing a reference to the handle.

        :param cdata handle_p: underlying handle pointer
        :param cdata arg: user-defined argument (NULL for our purposes)
        """
        handle_obj = ffi.from_handle(handle_p.data)
        self._handles.append(handle_obj)

    @classmethod
    def default_loop(cls):
        loop = Loop.__new__(cls)
        loop.loop_h = libuv.uv_default_loop()

        loop._handles = []  # temporary list of handle_t pointers
        loop._ffi_walk_cb = ffi.callback('void (*)(uv_handle_t *handle, void *arg)', loop._walk_cb)
        return loop

    @property
    def alive(self):
        return bool(libuv.uv_loop_alive(self.loop_h))

    @property
    def handles(self):
        """List of handles

        :return: list of specific pyuv_cffi Handle objects (Poll, Signal, etc.)
        :rtype: list[Handle]
        """
        libuv.uv_walk(self.loop_h, self._ffi_walk_cb, ffi.NULL)
        handles = self._handles
        self._handles = []  # don't keep references to handles alive in this list
        return handles

    def run(self, mode=UV_RUN_DEFAULT):
        return libuv.uv_run(self.loop_h, mode)

    def stop(self):
        libuv.uv_stop(self.loop_h)


def default_close_cb(uv_handle_t, handle):
    """Remove extra reference to the Handle object when closed

    This is the default handle-close callback that gets called if a callback is not supplied.

    :param uv_handle_t: pointer to the underlying uv_handle_t
    :type: uv_handle_t: cdata
    :param handle: Handle object that owns this callback
    :type handle: Handle
    """
    alive.remove(handle)  # now safe to free resources
    handle._ffi_cb = None
    handle._ffi_close_cb = None


class Handle:
    def __init__(self, handle):
        """
        :param cdata handle: specific handle type (uv_signal_t, uv_poll_t, etc.)
        """
        # uv_handle_t
        self.uv_handle = libuv.cast_handle(handle)
        self._ffi_cb = None
        self._ffi_close_cb = None
        self._close_called = False

        # store a reference to `self` in the underlying `uv_handle_t.data`
        self_h = ffi.new_handle(self)
        self.uv_handle.data = self_h
        self.__self_h = self_h  # keep the cdata object alive as long as `self` is alive

        alive.append(self)  # store a reference to self in the global scope

    def __repr__(self):
        cls = '{}.{}'.format(self.__module__, self.__class__.__name__)
        addr = hex(id(self))
        ref = self.ref
        active = self.active
        return '<{cls} at {addr} ref={ref} active={active}>'.format(**locals())

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

    @property
    def closed(self):
        """
        :return: True if handle is closing or closed, False otherwise
        """
        return bool(libuv.uv_is_closing(self.uv_handle))

    def close(self, callback=None):
        """Close uv handle

        :type callback: Callable(uv_handle: Handle) or None
        """
        if self._close_called:
            return

        if callback:
            def cb_wrapper(uv_handle_t):
                callback(self)

                alive.remove(self)  # now safe to free resources
                self._ffi_cb = None
                self._ffi_close_cb = None
        else:
            cb_wrapper = functools.partial(default_close_cb, handle=self)

        self._ffi_close_cb = ffi.callback('void (*)(uv_handle_t *)', cb_wrapper)
        libuv.uv_close(self.uv_handle, self._ffi_close_cb)

        self._close_called = True


class Idle(Handle):
    def __init__(self, loop):
        """
        :type loop: Loop
        """
        self.loop = loop
        self.handle = ffi.new('uv_idle_t *')
        libuv.uv_idle_init(loop.loop_h, self.handle)
        super().__init__(self.handle)

    def start(self, callback):
        """Start the idle handle

        :type callback: Callable(idle_handle: Idle)
        """

        def cb_wrapper(idle_h):
            callback(self)

        self._ffi_cb = ffi.callback('void (*)(uv_idle_t *)', cb_wrapper)
        libuv.uv_idle_start(self.handle, self._ffi_cb)

    def stop(self):
        libuv.uv_idle_stop(self.handle)


class Prepare(Handle):
    def __init__(self, loop):
        """
        :type loop: Loop
        """
        self.loop = loop
        self.handle = ffi.new('uv_prepare_t *')
        libuv.uv_prepare_init(loop.loop_h, self.handle)
        super().__init__(self.handle)

    def start(self, callback):
        """
        :type callback: Callable(prepare_handle: Prepare)
        """

        def cb_wrapper(prepare_h):
            callback(self)

        self._ffi_cb = ffi.callback('void (*)(uv_prepare_t *)', cb_wrapper)
        libuv.uv_prepare_start(self.handle, self._ffi_cb)

    def stop(self):
        libuv.uv_prepare_stop(self.handle)


class Check(Handle):
    def __init__(self, loop):
        """
        :type loop: Loop
        """
        self.loop = loop
        self.handle = ffi.new('uv_check_t *')
        libuv.uv_check_init(loop.loop_h, self.handle)
        super().__init__(self.handle)

    def start(self, callback):
        """
        :type callback: Callable(check_handle: check)
        """

        def cb_wrapper(check_h):
            callback(self)

        self._ffi_cb = ffi.callback('void (*)(uv_check_t *)', cb_wrapper)
        libuv.uv_check_start(self.handle, self._ffi_cb)

    def stop(self):
        libuv.uv_check_stop(self.handle)


class Timer(Handle):
    def __init__(self, loop):
        """
        :type loop: Loop
        """
        self.loop = loop
        self.handle = ffi.new('uv_timer_t *')
        libuv.uv_timer_init(loop.loop_h, self.handle)
        super().__init__(self.handle)

        self._repeat = None
        self._stop_called = False

    @property
    def repeat(self):
        return self._repeat

    @repeat.setter
    def repeat(self, timeout):
        # TODO implement this method
        self._repeat = timeout
        raise NotImplementedError()

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

        self._ffi_cb = ffi.callback('void (*)(uv_timer_t *)', cb_wrapper)
        libuv.uv_timer_start(self.handle, self._ffi_cb, timeout, repeat)

    def stop(self):
        libuv.uv_timer_stop(self.handle)


class Signal(Handle):
    def __init__(self, loop):
        """
        :type loop: Loop
        """
        self.loop = loop
        self.handle = ffi.new('uv_signal_t *')
        libuv.uv_signal_init(loop.loop_h, self.handle)
        super().__init__(self.handle)

        self._handle_allocated = True

    def start(self, callback, sig_num):
        """Start the signal listener

        :type callback: Callable(sig_handle: Signal, sig_num: int)
        :type sig_num: int
        """

        def cb_wrapper(uv_signal_t, signum):
            callback(self, signum)

        ffi_cb = ffi.callback('void (*)(uv_signal_t *, int)', cb_wrapper)
        self._ffi_cb = ffi_cb  # keep the FFI cdata object alive as long as this instance is alive
        libuv.uv_signal_start(self.handle, ffi_cb, sig_num)

    def stop(self):
        libuv.uv_signal_stop(self.handle)


class Poll(Handle):
    def __init__(self, loop, fd):
        """
        :type loop: Loop
        :type fd: int
        """
        self.loop = loop
        self.fd = fd
        self.handle = ffi.new('uv_poll_t *')
        libuv.uv_poll_init(loop.loop_h, self.handle, fd)
        super().__init__(self.handle)

        self._stop_called = False

    def start(self, events, callback):
        """Start the poll listener

        :param events: UV_READABLE | UV_WRITEABLE
        :param callback: Callable(poll_handle: Poll, status: int, events: int)
        """

        def cb_wrapper(uv_poll_t, status, events):
            callback(self, status, events)

        self._ffi_cb = ffi.callback('void (*)(uv_poll_t *, int, int)', cb_wrapper)
        libuv.uv_poll_start(self.handle, events, self._ffi_cb)

    def stop(self):
        if self._stop_called:
            return

        err = libuv.uv_poll_stop(self.handle)
        self._ffi_cb = None
        if err < 0:
            raise Exception('uv_poll_stop() failed: {}'.format(err))

        self._stop_called = True
