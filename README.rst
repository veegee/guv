guv = greenlets + libuv
=======================

guv is a fast networking library and WSGI server for Python >= 3.2

libuv (via pyuv) is used as the event loop backend, allowing for a clean, simple
event-loop implementation. If pyuv isn't available (such as for pypy3), a custom
epoll loop is used instead.

A pyuv implementation using cffi is currently being implemented.


To do
=====

Stability:

- Rewrite tests using py.test and make sure all tests pass

Event loop backends:

- Implement pyuv via CFFI
- Implement the asyncio interface
