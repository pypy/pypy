# NOT_RPYTHON
"""
The 'sys' module.
"""

from _structseq import structseqtype, structseqfield
import sys
import _imp

def excepthook(exctype, value, traceback):
    """Handle an exception by displaying it with a traceback on sys.stderr."""
    if not isinstance(value, BaseException):
        sys.stderr.write("TypeError: print_exception(): Exception expected for "
                         "value, {} found\n".format(type(value).__name__))
        return

    # Flush stdout as well, both files may refer to the same file
    try:
        sys.stdout.flush()
    except:
        pass

    try:
        from traceback import print_exception
        print_exception(exctype, value, traceback)
    except:
        if not excepthook_failsafe(exctype, value):
            raise

def excepthook_failsafe(exctype, value):
    # This version carefully tries to handle all bad cases (e.g. an
    # ImportError looking for traceback.py), but may still raise.
    # If it does, we get "Error calling sys.excepthook" from app_main.py.
    try:
        # first try to print the exception's class name
        stderr = sys.stderr
        stderr.write(str(getattr(exctype, '__name__', exctype)))
        # then attempt to get the str() of the exception
        try:
            s = str(value)
        except:
            s = '<failure of str() on the exception instance>'
        # then print it
        if s:
            stderr.write(': %s\n' % (s,))
        else:
            stderr.write('\n')
        return True     # successfully printed at least the class and value
    except:
        return False    # got an exception again... ignore, report the original

def exit(exitcode=None):
    """Exit the interpreter by raising SystemExit(exitcode).
If the exitcode is omitted or None, it defaults to zero (i.e., success).
If the exitcode is numeric, it will be used as the system exit status.
If it is another kind of object, it will be printed and the system
exit status will be one (i.e., failure)."""
    # note that we cannot simply use SystemExit(exitcode) here.
    # in the default branch, we use "raise SystemExit, exitcode", 
    # which leads to an extra de-tupelizing
    # in normalize_exception, which is exactly like CPython's.
    if isinstance(exitcode, tuple):
        raise SystemExit(*exitcode)
    raise SystemExit(exitcode)

#import __builtin__

def callstats():
    """Not implemented."""
    return None

copyright_str = """
Copyright 2003-2016 PyPy development team.
All Rights Reserved.
For further information, see <http://pypy.org>

Portions Copyright (c) 2001-2016 Python Software Foundation.
All Rights Reserved.

Portions Copyright (c) 2000 BeOpen.com.
All Rights Reserved.

Portions Copyright (c) 1995-2001 Corporation for National Research Initiatives.
All Rights Reserved.

Portions Copyright (c) 1991-1995 Stichting Mathematisch Centrum, Amsterdam.
All Rights Reserved.
"""


# This is tested in test_app_main.py
class sysflags(metaclass=structseqtype):

    name = "sys.flags"

    debug = structseqfield(0)
    inspect = structseqfield(1)
    interactive = structseqfield(2)
    optimize = structseqfield(3)
    dont_write_bytecode = structseqfield(4)
    no_user_site = structseqfield(5)
    no_site = structseqfield(6)
    ignore_environment = structseqfield(7)
    verbose = structseqfield(8)
    bytes_warning = structseqfield(9)
    quiet = structseqfield(10)
    hash_randomization = structseqfield(11)
    isolated = structseqfield(12)

null_sysflags = sysflags((0,)*13)
null__xoptions = {}


class SimpleNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self, recurse=set()):
        ident = id(self)
        if ident in recurse:
            return "namespace(...)"
        recurse.add(ident)
        try:
            pairs = ('%s=%r' % item for item in sorted(self.__dict__.items()))
            return "namespace(%s)" % ', '.join(pairs)
        finally:
            recurse.remove(ident)

    def __eq__(self, other):
        return (isinstance(other, SimpleNamespace) and
                self.__dict__ == other.__dict__)

# This class is not exposed in sys, but by the types module.
SimpleNamespace.__module__ = 'types'


implementation = SimpleNamespace(
    name='pypy',
    version=sys.version_info,
    hexversion=sys.hexversion,
    cache_tag=_imp.get_tag(),
    )
