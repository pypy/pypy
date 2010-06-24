# ctypes implementation: Victor Stinner, 2008-05-08
"""
This module provides an interface to the Unix syslog library routines.
Refer to the Unix manual pages for a detailed description of the
syslog facility.
"""

import sys
if sys.platform == 'win32':
    raise ImportError("No syslog on Windows")

# load the platform-specific cache made by running syslog.ctc.py
from ctypes_config_cache._syslog_cache import *

from ctypes_support import standard_c_lib as libc
from ctypes import c_int, c_char_p

# Real prototype is:
# void syslog(int priority, const char *format, ...);
# But we also need format ("%s") and one format argument (message)
_syslog = libc.syslog
_syslog.argtypes = (c_int, c_char_p, c_char_p)
_syslog.restype = None

_openlog = libc.openlog
_openlog.argtypes = (c_char_p, c_int, c_int)
_openlog.restype = None

_closelog = libc.closelog
_closelog.argtypes = None
_closelog.restype = None

_setlogmask = libc.setlogmask
_setlogmask.argtypes = (c_int,)
_setlogmask.restype = c_int

def openlog(ident, option, facility):
    _openlog(ident, option, facility)

def syslog(arg1, arg2=None):
    if arg2 is not None:
        priority, message = arg1, arg2
    else:
        priority, message = LOG_INFO, arg1
    _syslog(priority, "%s", message)

def closelog():
    _closelog()

def setlogmask(mask):
    return _setlogmask(mask)

def LOG_MASK(pri):
    return (1 << pri)

def LOG_UPTO(pri):
    return (1 << (pri + 1)) - 1

__all__ = ALL_CONSTANTS + (
    'openlog', 'syslog', 'closelog', 'setlogmask',
    'LOG_MASK', 'LOG_UPTO')

del ALL_CONSTANTS
