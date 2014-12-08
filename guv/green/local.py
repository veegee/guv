"""greenlet-local objects
"""
from weakref import WeakKeyDictionary
from copy import copy
from gevent.lock import RLock
from greenlet import getcurrent

__all__ = ["local"]


class _localbase:
    __slots__ = '_local__args', '_local__lock', '_local__dicts'

    def __new__(cls, *args, **kw):
        self = object.__new__(cls)
        object.__setattr__(self, '_local__args', (args, kw))
        object.__setattr__(self, '_local__lock', RLock())
        dicts = WeakKeyDictionary()
        object.__setattr__(self, '_local__dicts', dicts)

        # We need to create the greenlet dict in anticipation of
        # __init__ being called, to make sure we don't call it again ourselves.
        dict = object.__getattribute__(self, '__dict__')
        dicts[getcurrent()] = dict
        return self


def _init_locals(self):
    d = {}
    dicts = object.__getattribute__(self, '_local__dicts')
    dicts[getcurrent()] = d
    object.__setattr__(self, '__dict__', d)

    # we have a new instance dict, so call out __init__ if we have one
    cls = type(self)
    if cls.__init__ is not object.__init__:
        args, kw = object.__getattribute__(self, '_local__args')
        cls.__init__(self, *args, **kw)


class local(_localbase):
    def __getattribute__(self, name):
        d = object.__getattribute__(self, '_local__dicts').get(getcurrent())
        if d is None:
            # it's OK to acquire the lock here and not earlier, because the above code won't
            # switch out
            # however, subclassed __init__ might switch, so we do need to acquire the lock here
            lock = object.__getattribute__(self, '_local__lock')
            lock.acquire()
            try:
                _init_locals(self)
                return object.__getattribute__(self, name)
            finally:
                lock.release()
        else:
            object.__setattr__(self, '__dict__', d)
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name == '__dict__':
            raise AttributeError(
                "%r object attribute '__dict__' is read-only" % self.__class__.__name__)
        d = object.__getattribute__(self, '_local__dicts').get(getcurrent())
        if d is None:
            lock = object.__getattribute__(self, '_local__lock')
            lock.acquire()
            try:
                _init_locals(self)
                return object.__setattr__(self, name, value)
            finally:
                lock.release()
        else:
            object.__setattr__(self, '__dict__', d)
            return object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name == '__dict__':
            raise AttributeError(
                "%r object attribute '__dict__' is read-only" % self.__class__.__name__)
        d = object.__getattribute__(self, '_local__dicts').get(getcurrent())
        if d is None:
            lock = object.__getattribute__(self, '_local__lock')
            lock.acquire()
            try:
                _init_locals(self)
                return object.__delattr__(self, name)
            finally:
                lock.release()
        else:
            object.__setattr__(self, '__dict__', d)
            return object.__delattr__(self, name)

    def __copy__(self):
        currentId = getcurrent()
        d = object.__getattribute__(self, '_local__dicts').get(currentId)
        duplicate = copy(d)

        cls = type(self)
        if cls.__init__ is not object.__init__:
            args, kw = object.__getattribute__(self, '_local__args')
            instance = cls(*args, **kw)
        else:
            instance = cls()

        object.__setattr__(instance, '_local__dicts', {
            currentId: duplicate
        })

        return instance
