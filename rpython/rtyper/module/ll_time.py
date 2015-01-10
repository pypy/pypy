"""
Low-level implementations for the external functions of the 'time' module.
"""

import time, sys, math
from errno import EINTR
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.extfunc import BaseLazyRegistering, registering, extdef
from rpython.rlib import rposix
from rpython.rlib.rarithmetic import intmask, UINT_MAX
from rpython.translator.tool.cbuild import ExternalCompilationInfo

if sys.platform == 'win32':
    TIME_H = 'time.h'
    FTIME = '_ftime64'
    STRUCT_TIMEB = 'struct __timeb64'
    includes = ['winsock2.h', 'windows.h',
                TIME_H, 'sys/types.h', 'sys/timeb.h']
    need_rusage = False
else:
    TIME_H = 'sys/time.h'
    FTIME = 'ftime'
    STRUCT_TIMEB = 'struct timeb'
    includes = [TIME_H, 'time.h', 'errno.h', 'sys/select.h',
                'sys/types.h', 'unistd.h',
                'sys/time.h', 'sys/resource.h']

    if not sys.platform.startswith("openbsd"):
        includes.append('sys/timeb.h')

    need_rusage = True


class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=includes
    )
    TIMEVAL = platform.Struct('struct timeval', [('tv_sec', rffi.INT),
                                                 ('tv_usec', rffi.INT)])
    HAVE_GETTIMEOFDAY = platform.Has('gettimeofday')
    HAVE_FTIME = platform.Has(FTIME)
    if need_rusage:
        RUSAGE = platform.Struct('struct rusage', [('ru_utime', TIMEVAL),
                                                   ('ru_stime', TIMEVAL)])

if sys.platform.startswith('freebsd') or sys.platform.startswith('netbsd'):
    libraries = ['compat']
elif sys.platform == 'linux2':
    libraries = ['rt']
else:
    libraries = []

class CConfigForFTime:
    _compilation_info_ = ExternalCompilationInfo(
        includes=[TIME_H, 'sys/timeb.h'],
        libraries=libraries
    )
    TIMEB = platform.Struct(STRUCT_TIMEB, [('time', rffi.INT),
                                           ('millitm', rffi.INT)])

class CConfigForClockGetTime:
    _compilation_info_ = ExternalCompilationInfo(
        includes=['time.h'],
        libraries=libraries
    )
    TIMESPEC = platform.Struct('struct timespec', [('tv_sec', rffi.LONG),
                                                   ('tv_nsec', rffi.LONG)])

constant_names = ['RUSAGE_SELF', 'EINTR', 'CLOCK_PROCESS_CPUTIME_ID']
for const in constant_names:
    setattr(CConfig, const, platform.DefinedConstantInteger(const))
defs_names = ['GETTIMEOFDAY_NO_TZ']
for const in defs_names:
    setattr(CConfig, const, platform.Defined(const))

def decode_timeval(t):
    return (float(rffi.getintfield(t, 'c_tv_sec')) +
            float(rffi.getintfield(t, 'c_tv_usec')) * 0.000001)

class RegisterTime(BaseLazyRegistering):
    def __init__(self):
        self.configure(CConfig)
        self.TIMEVALP = lltype.Ptr(self.TIMEVAL)

