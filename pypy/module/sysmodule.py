"""
The 'sys' module.
"""

__interplevel__execfile('sysinterp.py')

# Common data structures
from __interplevel__ import initialpath as path
from __interplevel__ import modules, argv
from __interplevel__ import warnoptions, builtin_module_names

# Objects from interpreter-level
from __interplevel__ import stdin, stdout, stderr, maxint
from __interplevel__ import hexversion, platform

# Functions from interpreter-level
from __interplevel__ import displayhook, _getframe, exc_info

# Dummy
executable = ''
prefix = ''
version = '0.0.0 (not released yet)'

# XXX not called by the core yet
def excepthook(exctype, value, traceback):
    from traceback import print_exception
    print_exception(exctype, value, traceback)

def exit(exitcode=0):
    raise SystemExit(exitcode)
