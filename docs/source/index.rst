guv Documentation
=================

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

**This project is under heavy, active development and any help is
appreciated.**

This library is actively maintained and has a zero bug policy. Please submit
issues and pull requests, and bugs will be fixed immediately.


Guarantees
----------

This library makes the following guarantees:

* `Semantic versioning`_ is strictly followed
* Compatible with Python >= 3.2.0 and PyPy3 >= 2.3.1 (Python 3.2.5)


Testing
=======

guv uses the excellent **tox** and **pytest** frameworks. To run all tests, run
in the project root::

    $ pip install pytest
    $ py.test


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _Semantic versioning: http://semver.org
