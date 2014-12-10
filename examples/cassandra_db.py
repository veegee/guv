"""Cassandra database example

This example demonstrates connecting to a Cassandra database and executing a query. Note that
using the database driver remains exactly the same. The only  difference is that we're
monkey-patching everything (including the Cassandra driver), making it guv-friendly.

Adjust this example to your database address, keyspace, and query that you would like to run.
"""
import guv

guv.monkey_patch()

import logger

logger.configure()

import logging

from cassandra import cluster

log = logging.getLogger()


def main():
    nodes = ['192.168.20.2']

    c = cluster.Cluster(nodes, port=9042)
    session = c.connect('test')
    log.info('Execute commands')
    rows = session.execute('SELECT * FROM numbers')

    for row in rows:
        log.info(row)

    c.shutdown()


if __name__ == '__main__':
    main()

