from guv.green import threading


def f1():
    """A simple function
    """
    print('Hello, world!')


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
