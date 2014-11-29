guv = greenlets + libuv
=======================

guv is a fast networking library and WSGI server for Python >= 3.2 and pypy3

Multiple event loop backends are provided:

- **pyuv_cffi** (supported fully on CPython and pypy3, very fast), this is
  highly-experimental and a work-in-progress. Requires libuv >= 1.0.0
- **pyuv** (complete implementation, not supported on pypy3)
- **epoll** (currently the fastest for pypy3, and very fast on CPython)

In order to select a specific hub type, set the ``GUV_HUB`` environment variable
to a hub name from the above list; default is pyuv_cffi.


pyuv_cffi Status
----------------

- Currently implemented handles: Loop, Handle, Idle, Prepare, Timer, Signal,
  Poll


To do
-----

- Address all ``FIXME`` items (these are critical)
- Rewrite high-priority "greenified" modules: threading and database
- Rewrite greenthread and greenpool
- Check and update remaining "greenified" modules; these may have been broken
  after the core rewrite.
- Rewrite the patcher module
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
