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


pyuv_cffi Status
----------------

- Currently implemented handles: Loop, Handle, Idle, Prepare, Timer, Signal,
  Poll


To do
-----

- Add docs
- Address all ``FIXME`` items (these are critical)
- Rewrite high-priority "greenified" modules: threading and database
- Ensure that SSL is fully supported
- Rewrite greenthread and greenpool
- Check and update remaining "greenified" modules; these may have been broken
  after the core rewrite.

- Optimize the WSGI server by using ``http-parser`` and removing the dependency
  of socket.makefile(), which seems to be slow on Python 3.
- Speed up program startup. The initial delay may be caused by CFFI and the
  patcher module.

**pyuv_cffi**

- Move handle classes into their own modules
- Fully implement the pyuv interface
- Write tests using py.test, include checks for proper releasing of resources
  and memory leaks

**Stability**

- Rewrite tests using py.test and make sure all tests pass

**Event loop backends**

- Implement the asyncio interface
