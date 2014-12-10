"""Threading example

This example demonstrates the use of the :mod:`threading` module to create thread objects
normally. After monkey-patching, however, these Thread objects are actually wrappers around
GreenThreads (not POSIX threads), so spawning them and switching to them is extremely efficient.

Remember that calling Thread.start() only schedules the Thread to be started on the beginning of
the next event loop iteration, and returns immediately in the calling Thread.
"""
import guv
guv.monkey_patch()

from guv import gyield, patcher
import threading
import greenlet

threading_orig = patcher.original('threading')

greenlet_ids = {}


def debug(i):
    print('current thread: {}'.format(threading.current_thread()))
    print('{} greenlet_ids: {}'.format(i, greenlet_ids))


def f():
    greenlet_ids[1] = greenlet.getcurrent()
    debug(2)

    print('t: 1')
    gyield()
    print('t: 2')
    gyield()
    print('t: 3')


def main():
    greenlet_ids[0] = greenlet.getcurrent()
    debug(1)

    t = threading.Thread(target=f)
    t.start()
    gyield()  # `t` doesn't actually run until we yield
    debug(3)

    print('m: 1')
    gyield()
    print('m: 2')
    gyield()
    print('m: 3')

    t.join()


if __name__ == '__main__':
    main()
