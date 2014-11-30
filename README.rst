guv = greenlets + libuv
=======================

guv is a fast networking library and WSGI server for Python >= 3.3

libuv (via pyuv) is used as the event loop backend, allowing for a clean, simple
event-loop implementation.

To do
=====

- Rename the library?

Stability:

- Clean up the WSGI server
- Rewrite tests using py.test and make sure all tests pass

Event loop backends:

- Implement an epoll backend (which may be a simpler way of supporting pypy3
- Implement the asyncio interface

pypy3 support:

- Port to pypy3 either by adding Python 3.2 support, or waiting for pypy3 based
  on Python 3.3 to be released
- Port pyuv to pypy3 by implementing the pyuv interface via CFFI
