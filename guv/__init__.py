version_info = (0, 20, 0)
__version__ = '.'.join(map(str, version_info))

try:
    from . import greenthread
    from . import greenpool
    from . import queue
    from . import timeout
    from . import patcher
    from . import server
    from .hubs.trampoline import gyield
    import greenlet
    import pyuv_cffi  # only to compile the shared library before monkey-patching

    sleep = greenthread.sleep
    spawn = greenthread.spawn
    spawn_n = greenthread.spawn_n
    spawn_after = greenthread.spawn_after
    kill = greenthread.kill

    Timeout = timeout.Timeout
    with_timeout = timeout.with_timeout

    GreenPool = greenpool.GreenPool
    GreenPile = greenpool.GreenPile

    Queue = queue.Queue

    import_patched = patcher.import_patched
    monkey_patch = patcher.monkey_patch

    serve = server.serve
    listen = server.listen
    connect = server.connect
    StopServe = server.StopServe
    wrap_ssl = server.wrap_ssl

    getcurrent = greenlet.greenlet.getcurrent
except ImportError as e:
    # This is to make Debian packaging easier, it ignores import errors of greenlet so that the
    # packager can still at least access the version. Also this makes easy_install a little quieter
    if 'greenlet' not in str(e):
        # any other exception should be printed
        import traceback

        traceback.print_exc()
