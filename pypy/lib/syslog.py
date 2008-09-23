# ctypes implementation: Victor Stinner, 2008-05-08
"""
This module provides an interface to the Unix syslog library routines.
Refer to the Unix manual pages for a detailed description of the
syslog facility.
"""

from ctypes_support import standard_c_lib as libc
from ctypes import c_int, c_char_p
from ctypes_configure.configure import (configure,
    ExternalCompilationInfo, ConstantInteger, DefinedConstantInteger)

_CONSTANTS = (
    'LOG_EMERG',
    'LOG_ALERT',
    'LOG_CRIT',
    'LOG_ERR',
    'LOG_WARNING',
    'LOG_NOTICE',
    'LOG_INFO',
    'LOG_DEBUG',

    'LOG_PID',
    'LOG_CONS',
    'LOG_NDELAY',

    'LOG_KERN',
    'LOG_USER',
    'LOG_MAIL',
    'LOG_DAEMON',
    'LOG_AUTH',
    'LOG_LPR',
    'LOG_LOCAL0',
    'LOG_LOCAL1',
    'LOG_LOCAL2',
    'LOG_LOCAL3',
    'LOG_LOCAL4',
    'LOG_LOCAL5',
    'LOG_LOCAL6',
    'LOG_LOCAL7',
)
_OPTIONAL_CONSTANTS = (
    'LOG_NOWAIT',
    'LOG_PERROR',

    'LOG_SYSLOG',
    'LOG_CRON',
    'LOG_UUCP',
    'LOG_NEWS',
)

# Constant aliases if there are not defined
_ALIAS = (
    ('LOG_SYSLOG', 'LOG_DAEMON'),
    ('LOG_CRON', 'LOG_DAEMON'),
    ('LOG_NEWS', 'LOG_MAIL'),
    ('LOG_UUCP', 'LOG_MAIL'),
)

class SyslogConfigure:
    _compilation_info_ = ExternalCompilationInfo(includes=['sys/syslog.h'])
for key in _CONSTANTS:
    setattr(SyslogConfigure, key, ConstantInteger(key))
for key in _OPTIONAL_CONSTANTS:
    setattr(SyslogConfigure, key, DefinedConstantInteger(key))

config = configure(SyslogConfigure)
for key in _CONSTANTS:
    globals()[key] = config[key]
optional_constants = []
for key in _OPTIONAL_CONSTANTS:
    if config[key] is not None:
        globals()[key] = config[key]
        optional_constants.append(key)
for alias, key in _ALIAS:
    if alias in optional_constants:
        continue
    globals()[alias] = globals()[key]
    optional_constants.append(alias)
del config

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

__all__ = _CONSTANTS + tuple(optional_constants) + (
    'openlog', 'syslog', 'closelog', 'setlogmask',
    'LOG_MASK', 'LOG_UPTO')

del optional_constants

