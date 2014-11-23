from pyuv_cffi import Loop, Timer, Signal


def sig_cb(sig_h, sig_num):
    print('\nsig_cb({}, {})'.format(sig_h, sig_num))
    sig_h.stop()
    sig_h.loop.stop()


def timer_cb(timer_h):
    print('timer_cb({})'.format(timer_h))


def run():
    import signal

    loop = Loop()

    timer_h = Timer(loop)
    timer_h.start(timer_cb, 1, 1)

    sig_h = Signal(loop)
    sig_h.start(sig_cb, signal.SIGINT)

    status = loop.run()

    timer_h.close()  # stop and free any timers before freeing the loop
    print('loop.run() -> ', status)


def main():
    run()


if __name__ == '__main__':
    main()
