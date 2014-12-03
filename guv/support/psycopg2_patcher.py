"""A wait callback to allow psycopg2 cooperation with guv

Use :func:`make_psycopg_green()` to enable guv support in psycopg2.
"""

import psycopg2
from psycopg2 import extensions

from ..hubs import trampoline
from ..const import READ, WRITE


def psycopg2_wait_cb(conn, timeout=-1):
    """A wait callback to trigger a yield while waiting for the database to respond
    """
    while True:
        state = conn.poll()
        if state == extensions.POLL_OK:
            break
        elif state == extensions.POLL_READ:
            trampoline(conn.fileno(), READ)
        elif state == extensions.POLL_WRITE:
            trampoline(conn.fileno(), WRITE)
        else:
            raise psycopg2.OperationalError('Bad result from poll: {}'.format(state))


def make_psycopg_green():
    """Configure psycopg2 to call our wait function
    """
    if not hasattr(extensions, 'set_wait_callback'):
        raise ImportError('support for coroutines not available in this psycopg version ({})'
                          .format(psycopg2.__version__))

    extensions.set_wait_callback(psycopg2_wait_cb)

