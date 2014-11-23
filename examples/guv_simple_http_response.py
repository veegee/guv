import guv

guv.monkey_patch()
import guv.server
import logging
import time

from util import create_example
import logger

if not hasattr(time, 'perf_counter'):
    time.perf_counter = time.clock

logger.configure()
log = logging.getLogger()


def handle(sock, addr):
    # client connected
    sock.sendall(create_example())
    sock.close()


def main():
    pool = guv.GreenPool()

    try:
        log.debug('Start')
        server_sock = guv.listen(('0.0.0.0', 8001))
        server = guv.server.Server(server_sock, handle, pool, 'spawn_n')
        server.start()
    except (SystemExit, KeyboardInterrupt):
        log.debug('Bye!')


if __name__ == '__main__':
    main()
