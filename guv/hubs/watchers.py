from guv.hubs.abc import AbstractListener


class FdListener(AbstractListener):
    """Default implementation of :cls:`AbstractListener`
    """
    pass


class UvFdListener(AbstractListener):
    def __init__(self, evtype, fd, handle):
        """
        :param handle: underlying pyuv Handle object
        :type handle: pyuv.Handle
        """
        super().__init__(evtype, fd)
        self.handle = handle
