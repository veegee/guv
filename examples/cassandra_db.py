import guv

guv.monkey_patch()

import guv.hubs
from cassandra.cluster import Cluster
import logging
import logger

logger.configure()
log = logging.getLogger()


def main():
    # h = guv.hubs.get_hub()
    nodes = ['192.168.20.2']

    cluster = Cluster(nodes, port=9042)
    session = cluster.connect('test')
    log.info('Execute command')
    rows = session.execute('SELECT * FROM numbers')

    for row in rows:
        log.info(row)


if __name__ == '__main__':
    main()
