import guv

guv.monkey_patch()

from guv import gyield, sleep
import threading
import greenlet

greenlet_ids = {}


def debug(i):
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
    debug(3)

    print('m: 1')
    gyield()
    print('m: 2')
    gyield()
    print('m: 3')


if __name__ == '__main__':
    main()
