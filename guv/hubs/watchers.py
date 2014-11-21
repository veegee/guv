from guv.hubs.abc import AbstractListener


class PollFdListener(AbstractListener):
    def __init__(self, evtype, fd, cb):
        """
        :param cb: Callable
        :param args: tuple of arguments to be passed to cb
        """
        super().__init__(evtype, fd)
        self.cb = cb


class UvFdListener(AbstractListener):
    def __init__(self, evtype, fd, handle):
        """
        :param handle: underlying pyuv Handle object
        :type handle: pyuv.Handle
        """
        super().__init__(evtype, fd)
        self.handle = handle
