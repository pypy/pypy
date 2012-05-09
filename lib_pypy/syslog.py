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

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


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

_S_log_open = False
_S_ident_o = None

def _get_argv():
    try:
        import sys
        script = sys.argv[0]
        if isinstance(script, str):
            return script[script.rfind('/')+1:] or None
    except Exception:
        pass
    return None

@builtinify
def openlog(ident=None, logoption=0, facility=LOG_USER):
    global _S_ident_o, _S_log_open
    if ident is None:
        ident = _get_argv()
    _S_ident_o = c_char_p(ident)    # keepalive
    _openlog(_S_ident_o, logoption, facility)
    _S_log_open = True

@builtinify
def syslog(arg1, arg2=None):
    if arg2 is not None:
        priority, message = arg1, arg2
    else:
        priority, message = LOG_INFO, arg1
    # if log is not opened, open it now
    if not _S_log_open:
        openlog()
    _syslog(priority, "%s", message)

@builtinify
def closelog():
    global _S_log_open, S_ident_o
    if _S_log_open:
        _closelog()
        _S_log_open = False
        _S_ident_o = None

@builtinify
def setlogmask(mask):
    return _setlogmask(mask)

@builtinify
def LOG_MASK(pri):
    return (1 << pri)

@builtinify
def LOG_UPTO(pri):
    return (1 << (pri + 1)) - 1

__all__ = ALL_CONSTANTS + (
    'openlog', 'syslog', 'closelog', 'setlogmask',
    'LOG_MASK', 'LOG_UPTO')

del ALL_CONSTANTS
