"""
The 'sys' module.
"""

__interplevel__execfile('sysinterp.py')

# Common data structures
from __interplevel__ import initialpath as path
from __interplevel__ import modules, argv
from __interplevel__ import warnoptions, builtin_module_names
from __interplevel__ import maxunicode

# Objects from interpreter-level
from __interplevel__ import stdin, stdout, stderr, maxint
from __interplevel__ import platform, byteorder
from __interplevel__ import pypy_objspaceclass
from __interplevel__ import exec_prefix, prefix

# Functions from interpreter-level
from __interplevel__ import _getframe, exc_info, exc_clear, pypy_getudir
from __interplevel__ import getrecursionlimit, setrecursionlimit
from __interplevel__ import getcheckinterval, setcheckinterval
from __interplevel__ import getdefaultencoding

# Dummy
executable = 'py.py'
api_version = 0
copyright = ''
version = '2.3a0 (pypy build)'
version_info = (2, 3, 0, 'alpha', 0)
hexversion = 0x020300a0
ps1 = '>>>> '
ps2 = '.... '


# XXX not called by the core yet
def excepthook(exctype, value, traceback):
    from traceback import print_exception
    print_exception(exctype, value, traceback)

__excepthook__ = excepthook  # this is exactly like in CPython

def exit(exitcode=0):
    raise SystemExit(exitcode)

def displayhook(obj):
    if obj is not None:
        __builtins__['_'] = obj
        # NB. this is slightly more complicated in CPython,
        # see e.g. the difference with  >>> print 5,; 8
        print `obj`

__displayhook__ = displayhook  # this is exactly like in CPython

def getfilesystemencoding():
    """getfilesystemencoding() -> string

Return the encoding used to convert Unicode filenames in
operating system filenames."""
    
    if platform == "win32":
        encoding = "mbcs"
    elif platform == "darwin":
        encoding = "utf-8"
    else:
        encoding = None
    return encoding
