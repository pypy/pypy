"""Supporting definitions for the Python regression tests."""

'''
if __name__ != 'test.test_support':
    raise ImportError, 'test_support must be imported from the test package'
'''

import sys
from os import unlink

class Error(Exception):
    """Base class for regression test exceptions."""

class TestFailed(Error):
    """Test failed."""

class TestSkipped(Error):
    """Test skipped.

    This can be raised to indicate that a test was deliberatly
    skipped, but not because a feature wasn't available.  For
    example, if some resource can't be used, such as the network
    appears to be unavailable, this should be raised instead of
    TestFailed.
    """

class ResourceDenied(TestSkipped):
    """Test skipped because it requested a disallowed resource.

    This is raised when a test calls requires() for a resource that
    has not be enabled.  It is used to distinguish between expected
    and unexpected skips.
    """

verbose = 1              # Flag set to 0 by regrtest.py
use_resources = None       # Flag set to [] by regrtest.py

# _original_stdout is meant to hold stdout at the time regrtest began.
# This may be "the real" stdout, or IDLE's emulation of stdout, or whatever.
# The point is to have some flavor of stdout the user can actually see.
_original_stdout = None
def record_original_stdout(stdout):
    global _original_stdout
    _original_stdout = stdout

def get_original_stdout():
    return _original_stdout or sys.stdout

def unload(name):
    try:
        del sys.modules[name]
    except KeyError:
        pass

def forget(modname):
    '''"Forget" a module was ever imported by removing it from sys.modules and
    deleting any .pyc and .pyo files.'''
    unload(modname)
    import os
    for dirname in sys.path:
        try:
            os.unlink(os.path.join(dirname, modname + os.extsep + 'pyc'))
        except os.error:
            pass
        # Deleting the .pyo file cannot be within the 'try' for the .pyc since
        # the chance exists that there is no .pyc (and thus the 'try' statement
        # is exited) but there is a .pyo file.
        try:
            os.unlink(os.path.join(dirname, modname + os.extsep + 'pyo'))
        except os.error:
            pass

def is_resource_enabled(resource):
    """Test whether a resource is enabled.  Known resources are set by
    regrtest.py."""
    return use_resources is not None and resource in use_resources

def requires(resource, msg=None):
    """Raise ResourceDenied if the specified resource is not available.

    If the caller's module is __main__ then automatically return True.  The
    possibility of False being returned occurs when regrtest.py is executing."""
    # see if the caller's module is __main__ - if so, treat as if
    # the resource was set
    if sys._getframe().f_back.f_globals.get("__name__") == "__main__":
        return
    if not is_resource_enabled(resource):
        if msg is None:
            msg = "Use of the `%s' resource not enabled" % resource
        raise ResourceDenied(msg)

FUZZ = 1e-6

def fcmp(x, y): # fuzzy comparison function
    if type(x) == type(0.0) or type(y) == type(0.0):
        try:
            x, y = float(x), float(y)
            fuzz = (abs(x) + abs(y)) * FUZZ
            if abs(x-y) <= fuzz:
                return 0
        except:
            pass
    elif type(x) == type(y) and type(x) in (type(()), type([])):
        for i in range(min(len(x), len(y))):
            outcome = fcmp(x[i], y[i])
            if outcome != 0:
                return outcome
        return cmp(len(x), len(y))
    return cmp(x, y)

try:
    unicode
    have_unicode = 0 # XXX UNICODE 1
except NameError:
    have_unicode = 0

is_jython = sys.platform.startswith('java')


TESTFN = '@test'

# Make sure we can write to TESTFN, try in /tmp if we can't
fp = None
try:
    fp = open(TESTFN, 'w+')
except IOError:
    TMP_TESTFN = os.path.join('/tmp', TESTFN)
    try:
        fp = open(TMP_TESTFN, 'w+')
        TESTFN = TMP_TESTFN
        del TMP_TESTFN
    except IOError:
        print ('WARNING: tests will fail, unable to write to: %s or %s' %
                (TESTFN, TMP_TESTFN))
if fp is not None:
    fp.close()
del fp

def findfile(file, here=__file__):
    """Try to find a file on sys.path and the working directory.  If it is not
    found the argument passed to the function is returned (this does not
    necessarily signal failure; could still be the legitimate path)."""
    import os
    if os.path.isabs(file):
        return file
    path = sys.path
    path = [os.path.dirname(here)] + path
    for dn in path:
        fn = os.path.join(dn, file)
        if os.path.exists(fn): return fn
    return file

def verify(condition, reason='test failed'):
    """Verify that condition is true. If not, raise TestFailed.

       The optional argument reason can be given to provide
       a better error text.
    """

    if not condition:
        raise TestFailed(reason)

def vereq(a, b):
    """Raise TestFailed if a == b is false.

    This is better than verify(a == b) because, in case of failure, the
    error message incorporates repr(a) and repr(b) so you can see the
    inputs.

    Note that "not (a == b)" isn't necessarily the same as "a != b"; the
    former is tested.
    """

    if not (a == b):
        raise TestFailed, "%r == %r" % (a, b)

def sortdict(dict):
    "Like repr(dict), but in sorted order."
    items = dict.items()
    items.sort()
    reprpairs = ["%r: %r" % pair for pair in items]
    withcommas = ", ".join(reprpairs)
    return "{%s}" % withcommas

def check_syntax(statement):
    try:
        compile(statement, '<string>', 'exec')
    except SyntaxError:
        pass
    else:
        print 'Missing SyntaxError: "%s"' % statement
