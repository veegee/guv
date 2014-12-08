import guv

guv.monkey_patch()

from guv import gyield, patcher
import threading
import greenlet

threading_orig = patcher.original('threading')

greenlet_ids = {}


def check_thread():
    current = threading_orig.current_thread()
    assert type(current) is threading_orig._MainThread


def debug(i):
    print('current: {}'.format(threading.current_thread()))
    print('{} greenlet_ids: {}'.format(i, greenlet_ids))


def f():
    check_thread()
    greenlet_ids[1] = greenlet.getcurrent()
    debug(2)

    print('t: 1')
    gyield()
    print('t: 2')
    gyield()
    print('t: 3')


def main():
    check_thread()
    greenlet_ids[0] = greenlet.getcurrent()
    debug(1)

    t = threading.Thread(target=f)
    t.start()
    debug(3)

    print('m: 1')
    gyield()
    print('m: 2')
    gyield()
    print('m: 3')


if __name__ == '__main__':
    main()
