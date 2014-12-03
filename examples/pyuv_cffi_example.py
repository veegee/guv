"""A simple example demonstrating basic usage of pyuv_cffi

This example creates a timer handle and a signal handle, then starts the loop. The timer callback is
run after 1 second, and repeating every 1 second thereafter. The signal handle registers a listener
for the INT signal and allows us to exit the loop by pressing ctrl-c.
"""
import signal

from pyuv_cffi import Loop, Timer, Signal


def sig_cb(sig_h, sig_num):
    print('\nsig_cb({}, {})'.format(sig_h, sig_num))
    sig_h.stop()
    sig_h.loop.stop()


def timer_cb(timer_h):
    print('timer_cb({})'.format(timer_h))


def run():
    loop = Loop()

    timer_h = Timer(loop)
    timer_h.start(timer_cb, 1, 1)

    sig_h = Signal(loop)
    sig_h.start(sig_cb, signal.SIGINT)

    status = loop.run()

    timer_h.close()  # we must stop and free any other handles before freeing the loop
    print('loop.run() -> ', status)

    # all handles in pyuv_cffi (including the loop) are automatically freed when they go out of
    # scope


def main():
    run()


if __name__ == '__main__':
    main()
