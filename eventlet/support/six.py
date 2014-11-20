import operator
import sys
import types
import io

MAXSIZE = sys.maxsize


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)  # Invokes __set__.
        # This is a bit ugly, but it avoids running this again.
        delattr(obj.__class__, self.name)
        return result


class MovedModule(_LazyDescr):
    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if new is None:
            new = name
        self.mod = new

    def _resolve(self):
        return _import_module(self.mod)

    def __getattr__(self, attr):
        # Hack around the Django autoreloader. The reloader tries to get
        # __file__ or __name__ of every module in sys.modules. This doesn't work
        # well if this MovedModule is for an module that is unavailable on this
        # machine (like winreg on Unix systems). Thus, we pretend __file__ and
        # __name__ don't exist if the module hasn't been loaded yet. See issues
        # 51 and #53.
        if attr in ("__file__", "__name__") and self.mod not in sys.modules:
            raise AttributeError
        _module = self._resolve()
        value = getattr(_module, attr)
        setattr(self, attr, value)
        return value


class _LazyModule(types.ModuleType):
    def __init__(self, name):
        super(_LazyModule, self).__init__(name)
        self.__doc__ = self.__class__.__doc__

    def __dir__(self):
        attrs = ["__doc__", "__name__"]
        attrs += [attr.name for attr in self._moved_attributes]
        return attrs

    # Subclasses should override this
    _moved_attributes = []


class MovedAttribute(_LazyDescr):
    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if new_mod is None:
            new_mod = name
        self.mod = new_mod
        if new_attr is None:
            if old_attr is None:
                new_attr = name
            else:
                new_attr = old_attr
        self.attr = new_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)


class _MovedItems(_LazyModule):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("dbm_gnu", "gdbm", "dbm.gnu"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("_thread", "thread", "_thread"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_ttk", "ttk", "tkinter.ttk"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("xmlrpc_client", "xmlrpclib", "xmlrpc.client"),
    MovedModule("xmlrpc_server", "xmlrpclib", "xmlrpc.server"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
    if isinstance(attr, MovedModule):
        sys.modules[__name__ + ".moves." + attr.name] = attr
del attr

_MovedItems._moved_attributes = _moved_attributes

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")


class Module_six_moves_urllib_parse(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("SplitResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

Module_six_moves_urllib_parse._moved_attributes = _urllib_parse_moved_attributes

sys.modules[__name__ + ".moves.urllib_parse"] = sys.modules[__name__ +
                                                            ".moves.urllib.parse"] = \
    Module_six_moves_urllib_parse(
        __name__ + ".moves.urllib_parse")


class Module_six_moves_urllib_error(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

Module_six_moves_urllib_error._moved_attributes = _urllib_error_moved_attributes

sys.modules[__name__ + ".moves.urllib_error"] = sys.modules[__name__ +
                                                            ".moves.urllib.error"] = \
    Module_six_moves_urllib_error(
        __name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
    MovedAttribute("proxy_bypass", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes

sys.modules[__name__ + ".moves.urllib_request"] = sys.modules[__name__ +
                                                              ".moves.urllib.request"] = \
    Module_six_moves_urllib_request(
        __name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

Module_six_moves_urllib_response._moved_attributes = _urllib_response_moved_attributes

sys.modules[__name__ + ".moves.urllib_response"] = sys.modules[__name__ +
                                                               ".moves.urllib.response"] = \
    Module_six_moves_urllib_response(
        __name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

Module_six_moves_urllib_robotparser._moved_attributes = _urllib_robotparser_moved_attributes

sys.modules[__name__ + ".moves.urllib_robotparser"] = sys.modules[__name__ +
                                                                  ".moves.urllib.robotparser"] = \
    Module_six_moves_urllib_robotparser(
        __name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]

    def __dir__(self):
        return ['parse', 'error', 'request', 'response', 'robotparser']


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


_meth_func = "__func__"
_meth_self = "__self__"

_func_closure = "__closure__"
_func_code = "__code__"
_func_defaults = "__defaults__"
_func_globals = "__globals__"

_iterkeys = "keys"
_itervalues = "values"
_iteritems = "items"
_iterlists = "lists"

try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator

try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


def get_unbound_function(unbound):
    return unbound


create_bound_method = types.MethodType

callable = callable
_add_doc(get_unbound_function, """Get the function out of a possibly unbound function""")

get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))


def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))


def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))


def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


def b(s):
    return s.encode("latin-1")


def u(s):
    return s


unichr = chr
if sys.version_info[1] <= 1:
    def int2byte(i):
        return bytes((i,))
else:
    # This is about 2x faster than the implementation above on 3.2+
    int2byte = operator.methodcaller("to_bytes", 1, "big")
byte2int = operator.itemgetter(0)
indexbytes = operator.getitem

StringIO = io.StringIO
BytesIO = io.BytesIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")

exec_ = getattr(moves.builtins, "exec")


def reraise(tp, value, tb=None):
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value


_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""

    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)

    return wrapper
