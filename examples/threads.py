import guv

guv.monkey_patch()

import threading
import greenlet

greenlet_ids = {}


def debug(i):
    print('{} greenlet_ids: {}'.format(i, greenlet_ids))


def f():
    greenlet_ids[1] = greenlet.getcurrent()
    debug(2)


def main():
    greenlet_ids[0] = greenlet.getcurrent()
    debug(1)
    t = threading.Thread(target=f)
    t.start()
    debug(3)


if __name__ == '__main__':
    main()
