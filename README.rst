guv = greenlets + libuv
=======================

guv is a fast networking library and WSGI server for Python >= 3.2 and pypy3

Multiple event loop backends are provided:

- **epoll** (currently the fastest for pypy3, and very fast on CPython), may
  have a few minor bugs in the Timer.
- **pyuv** (currently the fastest for CPython, not supported on pypy3)
- **pyuv_cffi** (slower than pyuv on CPython, slow and unpredictable on pypy3),
  this is highly-experimental and a work-in-progress. Requires libuv >= 1.0.0

By default, the epoll backend is used due to the development override variable
being set in `guv.hubs.hub.hub_names`.


pyuv_cffi Status
================

- When examples/guv_simple_http_response is run on CPython, the implemented
  features seem to work fine, with no memory leaks. However, using CFFI is
  significantly slower than pyuv. Optimization needs to be done to speed up this
  implementation.
- On pypy3, there seems to be a memory leak.


To do
=====

- Optimize the WSGI server for pypy3. Currently, pypy3 is running the WSGI
  server VERY slow (almost as slow as cPython). However, pypy3 is running the
  simple event TCP handler very fast, so the issue must be with the WSGI server
  implementation.
- Rewrite "greenified" modules

pyuv_cffi:

- Move handle classes into their own modules
- Fully implement the pyuv interface
- Write tests (using py.test)

Stability:

- Rewrite tests using py.test and make sure all tests pass

Event loop backends:

- Implement the asyncio interface
