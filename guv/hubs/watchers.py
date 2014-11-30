from guv.hubs.abc import AbstractListener


class PollFdListener(AbstractListener):
    def __init__(self, evtype, fd, cb):
        """
        :param cb: Callable
        """
        super().__init__(evtype, fd)
        self.cb = cb


class UvFdListener(AbstractListener):
    def __init__(self, evtype, fd, handle):
        """
        :param handle: pyuv_cffi Handle object
        :type handle: pyuv_cffi.Handle
        """
        super().__init__(evtype, fd)
        self.handle = handle
