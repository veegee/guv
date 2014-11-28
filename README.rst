guv = greenlets + libuv
=======================

guv is a fast networking library and WSGI server for Python >= 3.2 and pypy3

Multiple event loop backends are provided:

- **pyuv_cffi** (supported fully on CPython and pypy3, very fast), this is
  highly-experimental and a work-in-progress. Requires libuv >= 1.0.0
- **epoll** (currently the fastest for pypy3, and very fast on CPython)
- **pyuv** (complete implementation, not supported on pypy3)

In order to select a specific hub type or list of hub types to try, set the
``GUV_HUBS`` environment variable to one or more comma-separated hub names from
the above list. Default is pyuv_cffi.


pyuv_cffi Status
----------------

- Currently implemented handles: Loop, Handle, Idle, Prepare, Timer, Signal, Poll
- No memory leaks on CPython as well as pypy3


To do
-----

- Address all ``FIXME`` items (these are critical)
- Rewrite greenthread and greenpool
- Rewrite high-priority "greenified" modules: threading
- Optimize the WSGI server by using ``http-parser`` and removing the dependency
  of socket.makefile().

**pyuv_cffi**

- Move handle classes into their own modules
- Fully implement the pyuv interface
- Write tests (using py.test)

**Stability**

- Rewrite tests using py.test and make sure all tests pass

**Event loop backends**

- Implement the asyncio interface
