import traceback
import greenlet

from . import event, greenthread, queue, semaphore

__all__ = ['GreenPool', 'GreenPile']

DEBUG = True


class GreenPool:
    """Pool of greenlets/GreenThreads

    This class manages a pool of greenlets/GreenThreads
    """

    def __init__(self, size=1000):
        """
        :param size: maximum number of active greenlets
        """
        self.size = size
        self.coroutines_running = set()
        self.sem = semaphore.Semaphore(size)
        self.no_coros_running = event.Event()

    def resize(self, new_size):
        """Change the max number of greenthreads doing work at any given time

        If resize is called when there are more than *new_size* greenthreads already working on
        tasks, they will be allowed to complete but no new tasks will be allowed to get launched
        until enough greenthreads finish their tasks to drop the overall quantity below *new_size*.
        Until then, the return value of free() will be negative.
        """
        size_delta = new_size - self.size
        self.sem.counter += size_delta
        self.size = new_size

    def running(self):
        """Return the number of greenthreads that are currently executing functions in the GreenPool
        """
        return len(self.coroutines_running)

    def free(self):
        """Return the number of greenthreads available for use

        If zero or less, the next call to :meth:`spawn` or :meth:`spawn_n` will block the calling
        greenthread until a slot becomes available."""
        return self.sem.counter

    def spawn(self, function, *args, **kwargs):
        """Run the *function* with its arguments in its own green thread

        Returns the :class:`GreenThread <guv.greenthread.GreenThread>` object that is running
        the function, which can be used to retrieve the results.

        If the pool is currently at capacity, ``spawn`` will block until one of the running
        greenthreads completes its task and frees up a slot.

        This function is reentrant; *function* can call ``spawn`` on the same pool without risk of
        deadlocking the whole thing.
        """
        # if reentering an empty pool, don't try to wait on a coroutine freeing
        # itself -- instead, just execute in the current coroutine
        current = greenlet.getcurrent()
        if self.sem.locked() and current in self.coroutines_running:
            # a bit hacky to use the GT without switching to it
            gt = greenthread.GreenThread(current)
            gt.main(function, *args, **kwargs)
            return gt
        else:
            self.sem.acquire()
            gt = greenthread.spawn(function, *args, **kwargs)
            if not self.coroutines_running:
                self.no_coros_running = event.Event()
            self.coroutines_running.add(gt)
            gt.link(self._spawn_done)
        return gt

    def _spawn_n_impl(self, func, args, kwargs, coro):
        try:
            try:
                func(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit, greenlet.GreenletExit):
                raise
            except:
                if DEBUG:
                    traceback.print_exc()
        finally:
            if coro is None:
                return
            else:
                coro = greenlet.getcurrent()
                self._spawn_done(coro)

    def spawn_n(self, function, *args, **kwargs):
        """Create a greenthread to run the `function` like :meth:`spawn`, but return None

        The difference is that :meth:`spawn_n` returns None; the results of `function` are not
        retrievable.
        """
        # if reentering an empty pool, don't try to wait on a coroutine freeing
        # itself -- instead, just execute in the current coroutine
        current = greenlet.getcurrent()
        if self.sem.locked() and current in self.coroutines_running:
            self._spawn_n_impl(function, args, kwargs, None)
        else:
            self.sem.acquire()
            g = greenthread.spawn_n(self._spawn_n_impl, function, args, kwargs, True)
            if not self.coroutines_running:
                self.no_coros_running = event.Event()
            self.coroutines_running.add(g)

    def waitall(self):
        """Wait until all greenthreads in the pool are finished working
        """
        assert greenlet.getcurrent() not in self.coroutines_running, \
            "Calling waitall() from within one of the " \
            "GreenPool's greenthreads will never terminate."
        if self.running():
            self.no_coros_running.wait()

    def _spawn_done(self, coro):
        self.sem.release()
        if coro is not None:
            self.coroutines_running.remove(coro)
        # if done processing (no more work is waiting for processing), we can finish off any
        # waitall() calls that might be pending
        if self.sem.balance == self.size:
            self.no_coros_running.send(None)

    def waiting(self):
        """Return the number of greenthreads waiting to spawn.
        """
        if self.sem.balance < 0:
            return -self.sem.balance
        else:
            return 0

    def _do_map(self, func, it, gi):
        for args in it:
            gi.spawn(func, *args)
        gi.spawn(return_stop_iteration)

    def starmap(self, function, iterable):
        """Apply each item in `iterable` to `function`

        Each item in `iterable` must be an iterable itself, passed to the function as expanded
        positional arguments. This behaves the same way as :func:`itertools.starmap`,  except that
        `func` is executed in a separate green thread for each item, with the concurrency limited by
        the pool's size. In operation, starmap consumes a constant amount of memory, proportional to
        the size of the pool, and is thus suited for iterating over extremely long input lists.
        """
        if function is None:
            function = lambda *args: args

        gi = GreenMap(self.size)
        greenthread.spawn_n(self._do_map, function, iterable, gi)
        return gi


def return_stop_iteration():
    return StopIteration()


class GreenPile:
    """An abstraction representing a set of I/O-related tasks

    Construct a GreenPile with an existing GreenPool object. The GreenPile will then use that
    pool's concurrency as it processes its jobs. There can be many GreenPiles associated with a
    single GreenPool.

    A GreenPile can also be constructed standalone, not associated with any GreenPool. To do this,
    construct it with an integer size parameter instead of a GreenPool.

    It is not advisable to iterate over a GreenPile in a different greenlet than the one which is
    calling spawn.  The iterator will exit early in that situation.
    """

    def __init__(self, size_or_pool=1000):
        """
        :param size_or_pool: either an existing GreenPool object, or the size a new one to create
        :type size_or_pool: int or GreenPool
        """
        if isinstance(size_or_pool, GreenPool):
            self.pool = size_or_pool
        else:
            self.pool = GreenPool(size_or_pool)
        self.waiters = queue.LightQueue()
        self.used = False
        self.counter = 0

    def spawn(self, func, *args, **kwargs):
        """Run `func` in its own GreenThread

        The Result is available by iterating over the GreenPile object.

        :param Callable func: function to call
        :param args: positional args to pass to `func`
        :param kwargs: keyword args to pass to `func`
        """
        self.used = True
        self.counter += 1
        try:
            gt = self.pool.spawn(func, *args, **kwargs)
            self.waiters.put(gt)
        except:
            self.counter -= 1
            raise

    def __iter__(self):
        return self

    def next(self):
        """Wait for the next result, suspending the current GreenThread until it is available

        :raise StopIteration: when there are no more results.
        """
        if self.counter == 0 and self.used:
            raise StopIteration()
        try:
            return self.waiters.get().wait()
        finally:
            self.counter -= 1

    __next__ = next


# this is identical to GreenPile but it blocks on spawn if the results
# aren't consumed, and it doesn't generate its own StopIteration exception,
# instead relying on the spawning process to send one in when it's done
class GreenMap(GreenPile):
    def __init__(self, size_or_pool):
        super(GreenMap, self).__init__(size_or_pool)
        self.waiters = queue.LightQueue(maxsize=self.pool.size)

    def next(self):
        try:
            val = self.waiters.get().wait()
            if isinstance(val, StopIteration):
                raise val
            else:
                return val
        finally:
            self.counter -= 1

    __next__ = next
