guv Documentation
=================

.. note::

    The documentation is currently in very active developemnt and not yet
    complete. Please keep checking back for updates and filing issues for
    missing sections or suggestions for enhancement.


Contents
--------

.. toctree::
    :maxdepth: 2
    :titlesonly:

    How does guv work? <howitworks>
    librarysupport
    modules


Introduction
------------

guv is a fast networking library and WSGI server (like gevent/eventlet) for
Python >= 3.2 and pypy3

The event loop backend is ``pyuv_cffi``, which aims to be fully compatible with
the ``pyuv`` interface. ``pyuv_cffi`` is fully supported on CPython and pypy3.
``libuv`` >= 1.0.0 is required.

Asynchronous DNS queries are supported via dnspython3. To forcefully disable
greendns, set the environment variable ``GUV_NO_GREENDNS`` to any value.

guv currently only runs on POSIX-compliant operating systems, but Windows
support is not far off and can be added in the near future if there is a demand
for this.

This library is actively maintained and has a zero bug policy. Please submit
issues and pull requests, and bugs will be fixed immediately.

**This project is under active development and any help is appreciated.**


Quickstart
----------

The following examples serve the sample WSGI app found in the ``examples``
directory.

**Serve your WSGI app using guv directly**:

.. code-block:: python

    if __name__ == '__main__':
        server_sock = guv.listen(('0.0.0.0', 8001))
        guv.wsgi.serve(server_sock, app)

**Serve your WSGI app using guv with gunicorn**::

    gunicorn -w 4 -b 127.0.0.1:8001 -k guv.GuvWorker wsgi_app:app


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


.. _Semantic versioning: http://semver.org
