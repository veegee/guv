"""Cassandra database example

This example demonstrates connecting to a Cassandra database and executing a query. Note that
using the database driver remains exactly the same. The only  difference is that we're
monkey-patching everything (including the Cassandra driver), making it guv-friendly.

Adjust this example to your database address, keyspace, and query that you would like to run.
"""
import guv

guv.monkey_patch()

from cassandra.cluster import Cluster
import logging
import logger

logger.configure()
log = logging.getLogger()


def main():
    nodes = ['192.168.20.2']

    cluster = Cluster(nodes, port=9042)
    session = cluster.connect('test')
    log.info('Execute commands')
    rows = session.execute('SELECT * FROM numbers')

    for row in rows:
        log.info(row)

    # FIXME: the current Cassandra support module hangs for unknown reasons, so hit ctrl-c now
    # see: https://github.com/veegee/guv/issues/10
    log.warn('The current Cassandra support module hangs for unknown reasons, so hit ctrl-c now')
    try:
        guv.sleep(600)
    except KeyboardInterrupt:
        pass

    cluster.shutdown()


if __name__ == '__main__':
    main()
