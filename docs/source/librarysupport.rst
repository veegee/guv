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

- If your application code depends on libriares that make blocking I/O calls
  *from external C code* (such as is the case for many popular database
  drivers), then a support module must be available to make those specific
  libraries cooperative. Such modules can be found in the `guv.support
  <https://github.com/veegee/guv/tree/develop/guv/support>`_ package and are all
  enabled by default if the library is installed.

.. note::

    If your code is using only standard library components and is behaving in a
    non-cooperative way, this is considered a critical bug. Please submit a bug
    report to ensure that this issue is fixed as soon as possible.


List of Known Compatible Libraries
----------------------------------

Pure-python libraries are guaranteed to be compatible with no additional support
modules:

- All standard library modules which make blocking I/O calls on file descriptors
  (such as :mod:`socket`, :mod:`smtplib`, etc), or call :func:`time.sleep`.
- `requests <https://github.com/kennethreitz/requests>`_
- `pg8000 <https://github.com/mfenniak/pg8000>`_
- Many more

This list will be expanded as additional libraries are tested and *confirmed* to
be compaible.

Libraries containing C extensions which are currently suported:

- `psycopg2 <https://github.com/psycopg/psycopg2>`_


Writing Support Modules for External Libraries
----------------------------------------------

Some libraries provide mechanisms for the purpose of facilitating creating
support modules for libraries such as guv. An excellent example is the high
quality ``psycopg2`` database driver for PostgreSQL, written as a C extension.
This library provides a very clean mechanism to call a callback before making
any operations which could potentially block. This allows guv to
:func:`~guv.hubs.switch.trampoline` and register the connection's file descriptor if the I/O
operation would block.

See the `psycopg2 patcher`_ for the implementation.

However, many libraries do not provide such a mechanism to simplify creating a
support module. In such case, there are several strategies for making these
libraries cooperative. In all cases, the end goal is the same: call
:func:`~guv.hubs.switch.trampoline`, which cooperatively yields and waits for the file
descriptor to be ready for I/O.

Note: this section is incomplete.


.. _psycopg2 patcher: https://github.com/veegee/guv/blob/develop/guv/support/psycopg2_patcher.py
