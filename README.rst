guv = greenlets + libuv
=======================

guv is a fast networking library and WSGI server for Python >= 3.2 and pypy3

The event loop backend is ``pyuv_cffi``, which aims to be fully compatible with
the ``pyuv`` interface. ``pyuv_cffi`` is fully supported on CPython and pypy3,
but is still experimental and in heavy development. libuv >= 1.0.0 is required

Asynchronous DNS queries are supported via dnspython3 if available (``pip
install dnspython3``). To forcefully disable greendns, set the environment
variable ``GUV_NO_GREENDNS`` to any value.

Currently only runs on POSIX-compliant operating systems (no Windows), but
Windows support is not far off and can be added in the near future if there is a
demand for this.


Installing
----------

Install using pip::

    pip install guv

You can now run the examples in the ``examples`` directory


pyuv_cffi Status
----------------

- Currently implemented handles: Loop, Handle, Idle, Prepare, Timer, Signal,
  Poll


To do
-----

High priority (these must be done before an alpha release):

- Rewrite the following green modules: ``ssl``, ``subprocess``, ``thread``,
  ``threading``
- Ensure ``greenthread`` and ``greenpool`` are fully working

Medium priority:

- Rewrite tests using py.test and make sure all tests pass
- Add docs
- Address all ``FIXME`` items (these are critical)
- Finish implementation of ``pyuv_cffi`` (reorganize modules and write tests)

Low priority:

- Optimize the WSGI server by using ``http-parser`` and removing the dependency
  of socket.makefile(), which seems to be slow on Python 3.
- Speed up importing and monkey-patching. The initial delay may be caused by
  CFFI compiling/verifying and the patcher module.
- Implement the asyncio interface
