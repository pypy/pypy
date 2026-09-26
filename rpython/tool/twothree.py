"""Helpers for code that has to run on both Python 2 and Python 3.

Everything in here exists because there is no single spelling that works on
both versions.  Where a common spelling *does* exist - and it usually does -
use it directly instead of adding a helper: a version check at a call site is
a fork of the source in miniature, and this module exists so that there is
exactly one place where such a check lives.

Deliberately has no dependencies outside the standard library, because the
translation toolchain has to keep working during bootstrapping.
"""

import sys

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
unichr = getattr(builtins, 'unichr', chr)
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
