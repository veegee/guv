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


Examples
--------

- **examples/crawler.py**: using ``requests`` to crawl the web (both HTTP and HTTPS)
- **examples/wsgi_app.py**: serving a WSGI application (any WSGI application is
  fully supported, since the current WSGI server implementation is heavily based
  on gevent's server).
- **examples/guv_simple_server.py**: a low-level example showing how to create
  very fast TCP servers which can easily handle 10,000+ connections.

With any of these examples, you can use wrk_ to get an idea of guv's performance
in terms of open connections and requests/sec.


Compatibility
-------------

guv aims to be compatible with all libraries which are compatible with the
gevent/eventlet-patched standard library. Out of the box, the provided examples
show how easy it is to use guv.


pyuv_cffi Status
----------------

- Currently implemented handles: Loop, Handle, Idle, Prepare, Timer, Signal,
  Poll
- The remaining handles are trivial to handle, and will be implemented after
  high priority goals are completed.


To do
-----

High priority:

- Rewrite tests using py.test and make sure all tests pass. Tests can be based
  on gevent and eventlet tests.
- Add docs and more examples
- Address all ``FIXME`` items (these are critical)

Medium priority:

- Compatibility with gunicorn
- Finish implementation of ``pyuv_cffi`` (reorganize modules and write tests)

Low priority:

- Optimize the WSGI server by using ``http-parser`` and removing the dependency
  of socket.makefile(), which seems to be slow on Python 3.
- Speed up importing and monkey-patching. The initial delay may be caused by
  CFFI compiling/verifying and the patcher module.
- Implement the asyncio interface
- When we drop Python 3.2 support, we can greatly simplify I/O exceptions by
  using ``BlockingIOError`` rather than ``socket.error`` and checking for
  ``args[0]``. It would be a good idea to patch ``BlockingIOError`` now to ease
  the transition to drop Python 3.2 support later.


.. _wrk: https://github.com/wg/wrk
