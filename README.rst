guv = greenlets + libuv
=======================

guv is a fast networking library and WSGI server for Python >= 3.2

libuv (via pyuv) is used as the event loop backend, allowing for a clean,
simple event-loop implementation.

A pyuv implementation using cffi is currently being implemented. This will
allow guv to be used with pypy3.

- Requires libuv >= 1.0.0


pyuv_cffi Status
================

When examples/guv_simple_http_response is run on CPython, the implemented
features seem to work fine, with no memory leaks. However, using CFFI is
significantly slower than pyuv. Optimization needs to be done to speed up this
implementation.

On pypy3, there seems to be a memory leak.


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
