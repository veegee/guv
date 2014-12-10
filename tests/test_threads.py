from guv.green import threading, time


def f1():
    """A simple function
    """
    print('Hello, world!')


def f2():
    """A simple function that sleeps for a short period of time
    """
    time.sleep(0.1)


class TestThread:
    def test_thread_create(self):
        t = threading.Thread(target=f1)
        assert t

    def test_thread_start(self):
        t = threading.Thread(target=f1)
        t.start()
        assert t

    def test_thread_join(self):
        t = threading.Thread(target=f1)
        t.start()
        t.join()
        assert t

    def test_thread_active(self):
        initial_count = threading.active_count()
        t = threading.Thread(target=f2)
        t.start()
        assert threading.active_count() > initial_count
        t.join()
        assert threading.active_count() == initial_count
