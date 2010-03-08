"""
'ctypes_configure' source for syslog.py.
Run this to rebuild _syslog_cache.py.
"""

import autopath
from ctypes_configure.configure import (configure,
    ExternalCompilationInfo, ConstantInteger, DefinedConstantInteger)
from ctypes_configure.dumpcache import dumpcache


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
for key in _OPTIONAL_CONSTANTS:
    if config[key] is None:
        del config[key]
for alias, key in _ALIAS:
    config.setdefault(alias, config[key])

all_constants = config.keys()
all_constants.sort()
config['ALL_CONSTANTS'] = tuple(all_constants)
dumpcache(__file__, '_syslog_cache.py', config)
