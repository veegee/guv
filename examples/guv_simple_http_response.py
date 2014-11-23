import guv

guv.monkey_patch()
import guv.server
import guv.hubs
import logging
import time
import cProfile
import pstats
import GreenletProfiler

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
        #server = guv.server.Server(server_sock, handle, pool, 'spawn_n')
        server = guv.server.Server(server_sock, handle, None, None)
        server.start()
    except (SystemExit, KeyboardInterrupt):
        log.debug('Bye!')


def cprofile_run():
    hub_name = guv.hubs.get_hub().__module__.split('.')[2]
    profile_fname = 'guv_{}.profile'.format(hub_name)
    stats_fname = 'guv_{}.stats'.format(hub_name)

    cProfile.run('main()', profile_fname)

    p = pstats.Stats(profile_fname)
    stats = p.strip_dirs().sort_stats('tottime', 'cumulative')
    stats.print_stats(40)
    stats.dump_stats(stats_fname)


def greenlet_profile_run():
    hub_name = guv.hubs.get_hub().__module__.split('.')[2]
    profile_fname = 'guv_{}.profile'.format(hub_name)
    stats_fname = 'guv_{}.stats'.format(hub_name)

    GreenletProfiler.set_clock_type('cpu')
    GreenletProfiler.start()
    main()
    GreenletProfiler.stop()
    stats = GreenletProfiler.get_func_stats()
    #stats.print_all()

    p = GreenletProfiler.convert2pstats(stats)
    pstats = p.strip_dirs().sort_stats('tottime', 'cumulative')
    pstats.print_stats(40)
    pstats.dump_stats(stats_fname)


if __name__ == '__main__':
    #greenlet_profile_run()
    main()
