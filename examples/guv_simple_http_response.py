import guv

guv.monkey_patch()
import guv.server
import logging
import time

from util import create_example
import logger
try:
    from pympler import tracker

    tr = tracker.SummaryTracker()
except ImportError:
    tr = None

if not hasattr(time, 'perf_counter'):
    time.perf_counter = time.clock

logger.configure()
log = logging.getLogger()


def handle(sock, addr):
    # client connected
    sock.sendall(create_example())
    sock.close()


if __name__ == '__main__':
    pool = guv.GreenPool()

    try:
        log.debug('Start')
        server_sock = guv.listen(('0.0.0.0', 8001))
        server = guv.server.Server(server_sock, handle, pool, 'spawn_n')
        server.start()
    except (SystemExit, KeyboardInterrupt):
        if tr:
            tr.print_diff()
        log.debug('Bye!')
