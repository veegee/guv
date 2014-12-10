Library Support
===============

The goal of guv is to support as many external libraries as possible such that
no modification to application code is necessary. However, note that it is still
required to use certain guv-specific constructs to take advantage of the
concurrency (as demonstrated in the examples directory).

Quick overview:

- If your application code and any library dependencies are pure-python and use
  only standard library components like :mod:`socket`, :mod:`time`, :mod:`os`,
  etc., then your code is guaranteed to be compatible with guv.
- If your application code depends on libraries that make blocking I/O calls
  *from external C code* (such as is the case for many popular database
  drivers), then a support module must be available to make those specific
  libraries cooperative. Such modules can be found in the `guv.support
  <https://github.com/veegee/guv/tree/develop/guv/support>`_ package and are all
  enabled by default if the library is installed.

.. note::

    If your code is using only standard library components and is behaving in a
    non-cooperative way, this is considered a critical bug, which can be fixed
    by greenifying the appropriate standard library modules. Please submit a bug
    report to ensure that this issue is fixed as soon as possible.


List of Known Compatible Libraries
----------------------------------

**Pure-python libraries are guaranteed to be compatible with no additional
support modules**:

- All standard library modules which make blocking calls such as I/O calls on
  file descriptors (including :mod:`socket`, :mod:`smtplib`, etc) are
  automatically supported.
- `boto <https://github.com/boto/boto>`_
- `Cassandra driver <https://github.com/datastax/python-driver>`_
- `gunicorn <https://github.com/benoitc/gunicorn>`_ (use with ``-k
  guv.GuvWorker``)
- `pg8000 <https://github.com/mfenniak/pg8000>`_
- `redis-py <https://github.com/andymccurdy/redis-py>`_
- `requests <https://github.com/kennethreitz/requests>`_
- Many more. This list will be expanded as additional libraries are tested and
  *confirmed* to be compatible

**Libraries containing C extensions which are currently supported**:

- `psycopg2 <https://github.com/psycopg/psycopg2>`_


Writing support modules for external libraries
----------------------------------------------

The idea behind guv is that everything runs in one OS thread (even
monkey-patched :class:`threading.Thread` objects!). Within this single thread,
greenlets are used to switch between various functions efficiently. This means
that any code making blocking calls will block the entire thread and prevent any
other greenlet from running. For this reason, guv provides a monkey-patched
standard library where all functions that can potentially block are replaced
with their "greenified" counterparts that *yield* instead of blocking. The goal
is to ensure that 100% of the standard library is greenified. If you encounter
any part of the standard library that seems to be blocking instead of yielding,
please file a bug report so this can be resolved as soon as possible.

The issue arises when using modules which make calls to compiled code that
cannot be monkey-patched (for example, through C extensions or CFFI). This is
the case for many popular database drivers or other network code which aim for
maximum performance.

Some libraries provide mechanisms for the purpose of facilitating creating
support modules for libraries such as guv. An excellent example is the high
quality ``psycopg2`` database driver for PostgreSQL, written as a C extension.
This library provides a very clean mechanism to call a callback before making
any operations which could potentially block. This allows guv to
:func:`~guv.hubs.switch.trampoline` and register the connection's file
descriptor if the I/O operation would block.

See the `psycopg2 patcher`_ for the implementation.

However, many libraries do not provide such a mechanism to simplify creating a
support module. In such case, there are several strategies for making these
libraries cooperative. In all cases, the end goal is the same: call
:func:`~guv.hubs.switch.trampoline`, which cooperatively yields and waits for
the file descriptor to be ready for I/O.

Note: this section is incomplete.


.. _psycopg2 patcher: https://github.com/veegee/guv/blob/develop/guv/support/psycopg2_patcher.py
