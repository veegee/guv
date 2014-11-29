import imp
import sys

__all__ = ['inject', 'import_patched', 'monkey_patch', 'is_monkey_patched']

__exclude = {'__builtins__', '__file__', '__name__'}


class SysModulesSaver(object):
    """Class that captures some subset of the current state of sys.modules
    """

    def __init__(self, module_names=()):
        """
        :param module_names: iterator of module names
        """
        self._saved = {}
        imp.acquire_lock()
        self.save(*module_names)

    def save(self, *module_names):
        """Saves the named modules to the object."""
        for modname in module_names:
            self._saved[modname] = sys.modules.get(modname, None)

    def restore(self):
        """Restores the modules that the saver knows about into
        sys.modules.
        """
        try:
            for modname, mod in self._saved.items():
                if mod is not None:
                    sys.modules[modname] = mod
                else:
                    try:
                        del sys.modules[modname]
                    except KeyError:
                        pass
        finally:
            imp.release_lock()


def inject(module_name, new_globals, *additional_modules):
    """Inject greenified modules into an imported module

    This method imports the module specified in `module_name`, arranging things so that the
    already-imported modules in `additional_modules` are used when `module_name` makes its imports.

    `new_globals` is either None or a globals dictionary that gets populated with the contents of
    the `module_name` module. This is useful when creating a "green" version of some other module.

    `additional_modules` should be a collection of two-element tuples, of the form
    `(name: str,  module: str)`. If it's not specified, a default selection of name/module pairs
    is used, which should cover all use cases but may be slower because there are inevitably
    redundant or unnecessary imports.
    """
    patched_name = '__patched_module_' + module_name
    if patched_name in sys.modules:
        # returning already-patched module so as not to destroy existing
        # references to patched modules
        return sys.modules[patched_name]

    if not additional_modules:
        # supply some defaults
        additional_modules = (
            _green_os_modules() +
            _green_select_modules() +
            _green_socket_modules() +
            _green_thread_modules() +
            _green_time_modules()
        )

    # after this, we will be modifying sys.modules, so save the state
    # of all modules that will be modified, and lock
    saver = SysModulesSaver([name for name, m in additional_modules])
    saver.save(module_name)

    # cover the target modules, so that when you import the module, it will import
    # the patched version
    for name, mod in additional_modules:
        sys.modules[name] = mod

    # remove the old module from sys.modules and reimport it while
    # the specified modules are in place
    sys.modules.pop(module_name, None)
    try:
        module = __import__(module_name, {}, {}, module_name.split('.')[:-1])

        if new_globals is not None:
            # update the given globals dictionary with everything from this new module
            for name in dir(module):
                if name not in __exclude:
                    new_globals[name] = getattr(module, name)

        # keep a reference to the new module to prevent it from dying
        sys.modules[patched_name] = module
    finally:
        saver.restore()  # Put the original modules back

    return module


def import_patched(module_name, *additional_modules, **kw_additional_modules):
    """Import patched version of module

    :param str module_name: name of module to import
    """
    return inject(module_name, None, *additional_modules + tuple(kw_additional_modules.items()))


def patch_function(func, *additional_modules):
    """Decorator that returns a version of the function that patches some modules for the
    duration of the function call.

    This should only be used for functions that import network libraries within their function
    bodies that there is no way of getting around.
    """
    if not additional_modules:
        # supply some defaults
        additional_modules = (
            _green_os_modules() +
            _green_select_modules() +
            _green_socket_modules() +
            _green_thread_modules() +
            _green_time_modules()
        )

    def patched(*args, **kw):
        saver = SysModulesSaver()
        for name, mod in additional_modules:
            saver.save(name)
            sys.modules[name] = mod
        try:
            return func(*args, **kw)
        finally:
            saver.restore()

    return patched


def _original_patch_function(func, *module_names):
    """Opposite of :func:`patch_function`

    Decorates a function such that when it's called, sys.modules is populated only with the
    unpatched versions of the specified modules. Unlike patch_function, only the names of the
    modules need be supplied, and there are no defaults.
    """

    def patched(*args, **kw):
        saver = SysModulesSaver(module_names)
        for name in module_names:
            sys.modules[name] = original(name)
        try:
            return func(*args, **kw)
        finally:
            saver.restore()

    return patched


def original(modname):
    """Return an unpatched version of a module

    This is useful for guv itself.
    """
    # note that it's not necessary to temporarily install unpatched
    # versions of all patchable modules during the import of the
    # module; this is because none of them import each other, except
    # for threading which imports thread
    original_name = '__original_module_' + modname
    if original_name in sys.modules:
        return sys.modules.get(original_name)

    # re-import the "pure" module and store it in the global _originals
    # dict; be sure to restore whatever module had that name already
    saver = SysModulesSaver((modname,))
    sys.modules.pop(modname, None)
    # some rudimentary dependency checking; fortunately the modules
    # we're working on don't have many dependencies so we can just do
    # some special-casing here
    deps = {'threading': '_thread', 'queue': 'threading'}
    if modname in deps:
        dependency = deps[modname]
        saver.save(dependency)
        sys.modules[dependency] = original(dependency)

    try:
        real_mod = __import__(modname, {}, {}, modname.split('.')[:-1])
        # save a reference to the unpatched module so it doesn't get lost
        sys.modules[original_name] = real_mod
    finally:
        saver.restore()

    return sys.modules[original_name]


already_patched = {}


def monkey_patch(**on):
    """Globally patch certain system modules to be greenlet-friendly

    The keyword arguments afford some control over which modules are patched.
    If no keyword arguments are supplied, all possible modules are patched.
    If keywords are set to True, only the specified modules are patched.  E.g.,
    ``monkey_patch(socket=True, select=True)`` patches only the select and
    socket modules.  Most arguments patch the single module of the same name
    (os, time, select).  The exceptions are socket, which also patches the ssl
    module if present; and thread, which patches thread, threading, and Queue.

    It's safe to call monkey_patch multiple times.
    """
    accepted_args = {'os', 'select', 'socket', 'thread', 'time', 'psycopg', '__builtin__'}
    default_on = on.pop('all', None)
    for k in on.keys():
        if k not in accepted_args:
            raise TypeError('monkey_patch() got an unexpected keyword argument %r' % k)
    if default_on is None:
        default_on = not (True in on.values())
    for modname in accepted_args:
        if modname == '__builtin__':
            on.setdefault(modname, False)
        on.setdefault(modname, default_on)

    modules_to_patch = []
    if on['os'] and not already_patched.get('os'):
        modules_to_patch += _green_os_modules()
        already_patched['os'] = True
    if on['select'] and not already_patched.get('select'):
        modules_to_patch += _green_select_modules()
        already_patched['select'] = True
    if on['socket'] and not already_patched.get('socket'):
        modules_to_patch += _green_socket_modules()
        already_patched['socket'] = True
    if on['thread'] and not already_patched.get('thread'):
        modules_to_patch += _green_thread_modules()
        already_patched['thread'] = True
    if on['time'] and not already_patched.get('time'):
        modules_to_patch += _green_time_modules()
        already_patched['time'] = True
    if on.get('__builtin__') and not already_patched.get('__builtin__'):
        modules_to_patch += _green_builtins()
        already_patched['__builtin__'] = True
    if on['psycopg'] and not already_patched.get('psycopg'):
        try:
            from guv.support import psycopg2_patcher

            psycopg2_patcher.make_psycopg_green()
            already_patched['psycopg'] = True
        except ImportError:
            # note that if we get an importerror from trying to
            # monkeypatch psycopg, we will continually retry it
            # whenever monkey_patch is called; this should not be a
            # performance problem but it allows is_monkey_patched to
            # tell us whether or not we succeeded
            pass

    imp.acquire_lock()
    try:
        for name, mod in modules_to_patch:
            orig_mod = sys.modules.get(name)
            if orig_mod is None:
                orig_mod = __import__(name)
            for attr_name in mod.__patched__:
                patched_attr = getattr(mod, attr_name, None)
                if patched_attr is not None:
                    setattr(orig_mod, attr_name, patched_attr)
    finally:
        imp.release_lock()


def is_monkey_patched(module):
    """Check if the specified module is currently patched

    Based entirely off the name of the module, so if you import a module some other way than with
    the import keyword (including import_patched), this might not be correct about that particular
    module

    :param module: module to check (moduble object itself, or its name str)
    :type module: module or str
    :return: True if the module is patched else False
    :rtype: bool
    """
    return module in already_patched or getattr(module, '__name__', None) in already_patched


def copy_attributes(source, destination, ignore=[], srckeys=None):
    """Copy properties from `source` to `destination`

    :param module source: source module
    :param dict destination: destination dict
    :param list ignore: list of properties that should not be copied
    :param list srckeys: list of keys to copy, if the source's __all__ is untrustworthy
    """
    if srckeys is None:
        srckeys = source.__all__

    d = {name: getattr(source, name) for name in srckeys
         if not (name.startswith('__') or name in ignore)}
    destination.update(d)


def _green_os_modules():
    from guv.green import os

    return [('os', os)]


def _green_select_modules():
    from guv.green import select

    return [('select', select)]


def _green_socket_modules():
    from guv.green import socket

    try:
        from guv.green import ssl

        return [('socket', socket), ('ssl', ssl)]
    except ImportError:
        return [('socket', socket)]


def _green_thread_modules():
    from guv.green import Queue
    from guv.green import thread
    from guv.green import threading

    return [('queue', Queue), ('_thread', thread), ('threading', threading)]


def _green_time_modules():
    from guv.green import time

    return [('time', time)]


def _green_builtins():
    try:
        from guv.green import builtin

        return [('__builtin__', builtin)]
    except ImportError:
        return []
