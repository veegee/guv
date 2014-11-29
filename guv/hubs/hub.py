import logging
import importlib
import os

from .. import patcher

_threading = patcher.original('threading')
_threadlocal = _threading.local()

log = logging.getLogger('guv')

# set hub_name to a valid loop backend name from an environment variable; None to use default
hub_name = os.environ.get('GUV_HUB')


def notify_opened(fd):
    """Mark the specified file descriptor as recently opened

    Some file descriptors may be closed 'silently' - that is, by the garbage collector, by an
    external library, etc. When the OS returns a file descriptor from an `open()` (or something
    similar), this may be the only indication we have that the FD has been closed and then recycled.
    We let the hub know that the old file descriptor is dead; any stuck listeners will be disabled
    and notified in turn.

    :param int fd: file descriptor
    """
    hub = get_hub()
    hub.notify_opened(fd)


def get_default_hub():
    """Get default hub implementation
    """
    names = [hub_name] if hub_name else ['pyuv_cffi', 'pyuv', 'epoll']

    for name in names:
        try:
            module = importlib.import_module('guv.hubs.{}'.format(name))
            log.debug('Hub: use {}'.format(name))
            return module
        except ImportError:
            # try the next possible hub
            pass


def use_hub(mod=None):
    """Use the module :var:`mod`, containing a class called Hub, as the event hub
    """
    if not mod:
        mod = get_default_hub()

    if hasattr(_threadlocal, 'hub'):
        del _threadlocal.hub

    if hasattr(mod, 'Hub'):
        _threadlocal.Hub = mod.Hub
    else:
        _threadlocal.Hub = mod


def get_hub():
    """Get the current event hub singleton object

    .. note :: |internal|
    """
    try:
        hub = _threadlocal.hub
    except AttributeError:
        # instantiate a Hub
        try:
            _threadlocal.Hub
        except AttributeError:
            use_hub()

        hub = _threadlocal.hub = _threadlocal.Hub()
    return hub
