import guv

guv.monkey_patch()
import guv.server
import guv.hubs
import logging
import time
import cProfile
import pstats

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
    #main()
    hub_name = guv.hubs.get_hub().__module__.split('.')[2]
    profile_fname = 'guv_{}.profile'.format(hub_name)
    stats_fname = 'guv_{}.stats'.format(hub_name)

    cProfile.run('main()', profile_fname)

    p = pstats.Stats(profile_fname)
    stats = p.strip_dirs().sort_stats('time', 'cumulative')
    stats.print_stats(40)
    stats.dump_stats(stats_fname)
