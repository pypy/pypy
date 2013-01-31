"""
Minimal (and limited) RPython version of some functions contained in os.path.
"""

import os.path
from rpython.rlib import rposix

if os.name == 'posix':
    # the posix version is already RPython, just use it
    rabspath = os.path.abspath
elif os.name == 'nt':
    def rabspath(path):
        if path == '':
            path = os.getcwd()
        try:
            return rposix._getfullpathname(path)
        except OSError:
            return path
else:
    raise ImportError('Unsupported os: %s' % os.name)
