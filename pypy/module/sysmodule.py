"""
The 'sys' module.
"""

__interplevel__execfile('sysinterp.py')

# Common data structures
from __interplevel__ import path, modules, argv
from __interplevel__ import warnoptions, builtin_module_names

# Objects from interpreter-level
from __interplevel__ import stdin, stdout, stderr, maxint
from __interplevel__ import hexversion, platform

# Functions from interpreter-level
from __interplevel__ import displayhook, _getframe
