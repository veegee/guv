from guv import gyield, spawn
from guv.green import threading, time
from guv.hubs import get_hub


def f1():
    """A simple function
    """
    return 'Hello, world!'


def f2():
    """A simple function that sleeps for a short period of time
    """
    time.sleep(0.1)


class TestThread:
    def test_thread_create(self):
        t = threading.Thread(target=f1)
        assert 'green' in repr(t)

    def test_thread_start(self):
        t = threading.Thread(target=f1)
        assert 'green' in repr(t)
        t.start()

    def test_thread_join(self):
        t = threading.Thread(target=f1)
        assert 'green' in repr(t)
        t.start()
        t.join()

    def test_thread_active(self):
        initial_count = threading.active_count()
        t = threading.Thread(target=f2)
        assert 'green' in repr(t)
        t.start()
        assert threading.active_count() > initial_count
        t.join()
        assert threading.active_count() == initial_count


class TestCondition:
    """
    :class:`threading.Condition` is not explicitly patched, but since its dependencies are patched,
    it shall behave in a cooperative manner.
    """

    def test_condition_init(self):
        cv = threading.Condition()
        assert cv

    def test_condition(self):
        print()
        cv = threading.Condition()
        assert cv._lock.green  # make sure we're using a green lock

        items = []

        def produce():
            print('start produce()')
            with cv:
                for i in range(10):
                    items.append(i)
                    print('yield from produce()')
                    gyield()

                print('notify')
                cv.notify()
            print('done produce()')

        def consume():
            print('start consume()')
            with cv:
                while not len(items) == 10:
                    print('wait ({}/{})'.format(len(items), 10))
                    cv.wait()

                print('items: {}'.format(len(items)))
            print('done consume()')

        spawn(produce)
        spawn(consume)

        print('switch to hub')
        gyield(False)
        print('done test')

