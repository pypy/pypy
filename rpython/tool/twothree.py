"""Helpers for code that has to run on both Python 2 and Python 3.

Everything in here exists because there is no single spelling that works on
both versions.  Where a common spelling *does* exist - and it usually does -
use it directly instead of adding a helper: a version check at a call site is
a fork of the source in miniature, and this module exists so that there is
exactly one place where such a check lives.

Deliberately has no dependencies outside the standard library, because the
translation toolchain has to keep working during bootstrapping.
"""

import inspect
import sys
import types

try:
    import builtins
except ImportError:
    import __builtin__ as builtins

try:
    # a str buffer on either version: a byte string on Python 2, text on 3
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

try:
    import thread
except ImportError:
    try:
        import _thread as thread
    except ImportError:
        import dummy_thread as thread

try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

try:
    intern = sys.intern
except AttributeError:
    intern = builtins.intern

# The Python 2 built-ins that Python 3 removed.  On Python 2 each name is the
# built-in itself; on Python 3 it is the nearest equivalent there.  Import the
# ones a module uses from here, instead of relying on them being built-ins.
long = getattr(builtins, 'long', int)
unicode = getattr(builtins, 'unicode', str)
if hasattr(builtins, 'unichr'):
    unichr = builtins.unichr
else:
    def unichr(i):
        """chr() on Python 3, but not the same object: RPython's chr()
        makes a Char and its unichr() a UniChar, and the annotator and the
        rtyper key their built-ins by object."""
        return chr(i)
xrange = getattr(builtins, 'xrange', range)
basestring = getattr(builtins, 'basestring', (str, bytes))
buffer = getattr(builtins, 'buffer', memoryview)
raw_input = getattr(builtins, 'raw_input', input)

try:
    cmp = builtins.cmp
except AttributeError:
    def cmp(a, b):
        return (a > b) - (a < b)

try:
    reload = builtins.reload
except AttributeError:
    from importlib import reload

try:
    execfile = builtins.execfile
except AttributeError:
    def execfile(filename, globals=None, locals=None):
        with open(filename) as f:
            code = compile(f.read(), filename, 'exec')
        exec(code, globals, locals)

# The type of classic classes.  Python 3 has none: every class is an
# instance of type, so a check for "type or ClassType" is a check for type.
ClassType = getattr(types, 'ClassType', type)

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


def native_str(data):
    """Bytes from outside the process, such as a subprocess's output, as
    the native str type: unchanged on Python 2, where str is bytes, and
    decoded on Python 3.  surrogateescape keeps undecodable bytes intact."""
    if isinstance(data, str):
        return data
    return data.decode('utf-8', 'surrogateescape')


def native_bytes(data):
    """The inverse of native_str(): a native str as bytes, for writing to
    a binary file or a pipe.  Unchanged on Python 2."""
    if isinstance(data, bytes):
        return data
    return data.encode('utf-8', 'surrogateescape')


def get_function(method):
    """The function behind a method: 'method.im_func' on Python 2.

    Python 3 has no unbound methods, so 'Class.method' is already the
    function there and has no __func__.  A bound method has __func__ on
    both versions, and so does an unbound one on Python 2.
    """
    return getattr(method, '__func__', method)


def is_builtin_type(cls):
    """Whether cls is a built-in type other than an exception class.

    Python 2 keeps the built-in exceptions in a module of their own,
    'exceptions'; Python 3 puts them into builtins with the other types.
    """
    return (cls.__module__ == builtins.__name__ and
            not issubclass(cls, BaseException))


def ordering_from_cmp(cls):
    """Class decorator: the rich comparisons from __cmp__, which Python 3
    ignores.  The class keeps its __hash__."""
    hash_ = cls.__hash__
    cls.__eq__ = lambda self, other: self.__cmp__(other) == 0
    cls.__ne__ = lambda self, other: self.__cmp__(other) != 0
    cls.__lt__ = lambda self, other: self.__cmp__(other) < 0
    cls.__le__ = lambda self, other: self.__cmp__(other) <= 0
    cls.__gt__ = lambda self, other: self.__cmp__(other) > 0
    cls.__ge__ = lambda self, other: self.__cmp__(other) >= 0
    cls.__hash__ = hash_
    return cls


def get_class(method):
    """The class a bound method was looked up on: 'method.im_class' on
    Python 2.  Python 3 does not record it; there it is the class of the
    method's __self__."""
    try:
        return method.im_class
    except AttributeError:
        return type(method.__self__)


if hasattr(inspect, 'getfullargspec'):
    def getargspec(func):
        """inspect.getargspec(), which Python 3.11 removed: the
        (args, varargs, keywords, defaults) of a function."""
        spec = inspect.getfullargspec(func)
        return spec.args, spec.varargs, spec.varkw, spec.defaults
else:
    getargspec = inspect.getargspec


def with_metaclass(meta, *bases):
    """Base class list for a class that 'meta' creates, on both versions.

        class X(with_metaclass(Meta, Base)):
            ...

    Python 2 reads the metaclass from a '__metaclass__' class attribute and
    Python 3 from a 'metaclass=' keyword that Python 2 cannot parse.  The
    temporary class returned here has a metaclass that creates the real
    class with 'meta' and the real bases, so X never inherits from it.
    """
    class metaclass(type):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)

        @classmethod
        def __prepare__(cls, name, this_bases):
            return meta.__prepare__(name, bases)
    return type.__new__(metaclass, 'temporary_class', (), {})


if sys.version_info[0] == 2:
    # 'raise tp, value, tb' is a syntax error on Python 3 and there is no way
    # to write the three-argument form so that both parsers accept it, so it
    # has to be hidden behind exec.
    exec("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")
else:
    def reraise(tp, value, tb=None):
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

reraise.__doc__ = """\
Re-raise an exception with an explicit traceback.

Equivalent to the Python 2 'raise tp, value, tb' statement.  Use it only
where the traceback of the original exception has to be preserved across a
re-raise; a plain 'raise' inside an except block already does that and needs
no helper.
"""
