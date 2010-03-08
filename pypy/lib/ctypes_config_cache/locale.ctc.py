"""
'ctypes_configure' source for _locale.py.
Run this to rebuild _locale_cache.py.
"""

import autopath
from ctypes_configure.configure import (configure, ExternalCompilationInfo,
    ConstantInteger, DefinedConstantInteger, SimpleType)
from ctypes_configure.dumpcache import dumpcache

# ____________________________________________________________

_CONSTANTS = (
    'LC_CTYPE',
    'LC_NUMERIC',
    'LC_TIME',
    'LC_COLLATE',
    'LC_MONETARY',
    'LC_MESSAGES',
    'LC_ALL',
    'LC_PAPER',
    'LC_NAME',
    'LC_ADDRESS',
    'LC_TELEPHONE',
    'LC_MEASUREMENT',
    'LC_IDENTIFICATION',
)

class LocaleConfigure:
    _compilation_info_ = ExternalCompilationInfo(includes=['locale.h'])
for key in _CONSTANTS:
    setattr(LocaleConfigure, key, ConstantInteger(key))

config = configure(LocaleConfigure, noerr=True)

# ____________________________________________________________

HAS_LANGINFO = True    # xxx hard-coded to True for now

if HAS_LANGINFO:
    # this is incomplete list
    langinfo_names = ('CODESET D_T_FMT D_FMT T_FMT RADIXCHAR THOUSEP '
                      'YESEXPR NOEXPR CRNCYSTR').split(" ")
    for i in range(1, 8):
        langinfo_names.append("DAY_%d" % i)
        langinfo_names.append("ABDAY_%d" % i)
    for i in range(1, 13):
        langinfo_names.append("MON_%d" % i)
        langinfo_names.append("ABMON_%d" % i)
    
    class LanginfoConfigure:
        _compilation_info_ = ExternalCompilationInfo(includes=['langinfo.h'])
        nl_item = SimpleType('nl_item')
    for key in langinfo_names:
        setattr(LanginfoConfigure, key, ConstantInteger(key))

    config.update(configure(LanginfoConfigure))
    _CONSTANTS = _CONSTANTS + tuple(langinfo_names)

# ____________________________________________________________

config['ALL_CONSTANTS'] = _CONSTANTS
config['HAS_LANGINFO'] = HAS_LANGINFO
dumpcache(__file__, '_locale_cache.py', config)
