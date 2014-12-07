guv = greenlets + libuv
=======================

:Version: alpha
:Web: http://guv.readthedocs.org/
:Download: http://pypi.python.org/pypi/guv/
:Source: http://github.com/veegee/guv
:Keywords: guv, greenlet, gevent, eventlet


About
-----

guv is a fast networking library and WSGI server (like gevent/eventlet) for
**Python >= 3.2 and pypy3**

The event loop backend is pyuv_cffi_, which aims to be fully compatible with the
pyuv_ interface. pyuv_cffi is fully supported on CPython and pypy3. libuv_
>= 1.0.0 is required.

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

Since guv is currently in alpha release state and under active development, it
is recommended to pull often and install manually::

    git clone https://github.com/veegee/guv.git
    cd guv
    python setup.py install

Note: libuv_ >= 1.0.0 is required. This is the first stable version but is a
recent release and may not be available in Debian/Ubuntu stable repositories, so
you must compile and install manually.

Serve your WSGI app using guv directly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import guv; guv.monkey_patch()
    import guv.wsgi

    app = <your WSGI app>

    if __name__ == '__main__':
        server_sock = guv.listen(('0.0.0.0', 8001))
        guv.wsgi.serve(server_sock, app)

Serve your WSGI app using guv with gunicorn_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    gunicorn -w 4 -b 127.0.0.1:8001 -k guv.GuvWorker wsgi_app:app

Note: you can use wrk_ to benchmark the performance of guv.

Crawl the web: efficiently make multiple "simultaneous" requests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import guv; guv.monkey_patch()
    import requests

    def get_url(url):
        print('get_url({})'.format(url))
        return requests.get(url)

    def main():
        urls = ['http://gnu.org'] * 10
        urls += ['https://eff.org'] * 10

        pool = guv.GreenPool()
        results = pool.starmap(get_url, zip(urls))

        for i, resp in enumerate(results):
            print('{}: done, length: {}'.format(i, len(resp.text)))

    if __name__ == '__main__':
        main()


Guarantees
----------

This library makes the following guarantees:

* `Semantic versioning`_ is strictly followed
* Compatible with Python >= 3.2.0 and PyPy3 >= 2.3.1 (Python 3.2.5)


.. _pyuv: https://github.com/saghul/pyuv
.. _pyuv_cffi: https://github.com/veegee/guv/tree/develop/pyuv_cffi
.. _libuv: https://github.com/libuv/libuv
.. _gunicorn: https://github.com/benoitc/gunicorn
.. _Semantic versioning: http://semver.org
.. _wrk: https://github.com/wg/wrk
