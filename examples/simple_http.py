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

response_times = []


def get_avg_time():
    global response_times
    times = response_times[-1000:]
    avg = sum(times) / len(times)

    if len(response_times) > 5000:
        response_times = times

    return avg


def handle(sock, addr):
    # client connected
    start_time = time.perf_counter()
    sock.sendall(create_example())
    sock.close()

    total_time = time.perf_counter() - start_time
    response_times.append(total_time)


if __name__ == '__main__':
    pool = guv.GreenPool()

    try:
        log.debug('Start')
        server_sock = guv.listen(('0.0.0.0', 8001))
        server = guv.server.ServerLoop(server_sock, handle, pool, 'spawn_n')
        server.start()
    except (SystemExit, KeyboardInterrupt):
        log.debug('average response time: {}'.format(get_avg_time()))
        log.debug('Bye!')
