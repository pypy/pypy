from ctypes_support import standard_c_lib as libc
from ctypes_support import get_errno
from ctypes import Structure, c_int, c_long, byref
from errno import EINVAL, EPERM
from ctypes_configure.configure import (configure,
    ExternalCompilationInfo, ConstantInteger, DefinedConstantInteger,
    SimpleType)

_CONSTANTS = (
    'RLIM_INFINITY',
    'RLIM_NLIMITS',
)
_OPTIONAL_CONSTANTS = (
    'RLIMIT_CPU',
    'RLIMIT_FSIZE',
    'RLIMIT_DATA',
    'RLIMIT_STACK',
    'RLIMIT_CORE',
    'RLIMIT_RSS',
    'RLIMIT_NPROC',
    'RLIMIT_NOFILE',
    'RLIMIT_OFILE',
    'RLIMIT_MEMLOCK',
    'RLIMIT_AS',
    'RLIMIT_LOCKS',
    'RLIMIT_SIGPENDING',
    'RLIMIT_MSGQUEUE',
    'RLIMIT_NICE',
    'RLIMIT_RTPRIO',
    'RLIMIT_VMEM',

    'RUSAGE_BOTH',
    'RUSAGE_SELF',
    'RUSAGE_CHILDREN',
)

# Read required libc functions
_getrusage = libc.getrusage
_getrlimit = libc.getrlimit
_setrlimit = libc.setrlimit
try:
    _getpagesize = libc.getpagesize
except AttributeError:
    from os import sysconf
    _getpagesize = None

# Setup our configure
class ResourceConfigure:
    _compilation_info_ = ExternalCompilationInfo(includes=['sys/resource.h'])
    rlim_t = SimpleType('rlim_t')
for key in _CONSTANTS:
    setattr(ResourceConfigure, key, ConstantInteger(key))
for key in _OPTIONAL_CONSTANTS:
    setattr(ResourceConfigure, key, DefinedConstantInteger(key))

# Configure constants and types
config = configure(ResourceConfigure)
rlim_t = config['rlim_t']
for key in _CONSTANTS:
    globals()[key] = config[key]
optional_constants = []
for key in _OPTIONAL_CONSTANTS:
    if config[key] is not None:
        globals()[key] = config[key]
        optional_constants.append(key)
del config

class ResourceError(OSError):
    def __init__(self, errno):
        OSError.__init__(self, errno)

class timeval(Structure):
    _fields_ = (
        ("tv_sec", c_int),
        ("tv_usec", c_int),
    )
    def __str__(self):
        return "(%s, %s)" % (self.tv_sec, self.tv_usec)

    def __float__(self):
        return self.tv_sec + self.tv_usec/1000000.0

class _struct_rusage(Structure):
    _fields_ = (
        ("ru_utime", timeval),
        ("ru_stime", timeval),
        ("ru_maxrss", c_long),
        ("ru_ixrss", c_long),
        ("ru_idrss", c_long),
        ("ru_isrss", c_long),
        ("ru_minflt", c_long),
        ("ru_majflt", c_long),
        ("ru_nswap", c_long),
        ("ru_inblock", c_long),
        ("ru_oublock", c_long),
        ("ru_msgsnd", c_long),
        ("ru_msgrcv", c_long),
        ("ru_nsignals", c_long),
        ("ru_nvcsw", c_long),
        ("ru_nivcsw", c_long),
    )

class struct_rusage:
    def __init__(self, ru):
        self.ru_utime = float(ru.ru_utime)
        self.ru_stime = float(ru.ru_stime)
        self.ru_maxrss = ru.ru_maxrss
        self.ru_ixrss = ru.ru_ixrss
        self.ru_idrss = ru.ru_idrss
        self.ru_isrss = ru.ru_isrss
        self.ru_minflt = ru.ru_minflt
        self.ru_majflt = ru.ru_majflt
        self.ru_nswap = ru.ru_nswap
        self.ru_inblock = ru.ru_inblock
        self.ru_oublock = ru.ru_oublock
        self.ru_msgsnd = ru.ru_msgsnd
        self.ru_msgrcv = ru.ru_msgrcv
        self.ru_nsignals = ru.ru_nsignals
        self.ru_nvcsw = ru.ru_nvcsw
        self.ru_nivcsw = ru.ru_nivcsw

class rlimit(Structure):
    _fields_ = (
        ("rlim_cur", rlim_t),
        ("rlim_max", rlim_t),
    )

def getrusage(who):
    ru = _struct_rusage()
    ret = _getrusage(who, byref(ru))
    if ret == -1:
        errno = get_errno()
        if errno == EINVAL:
            raise ValueError("invalid who parameter")
        raise ResourceError(errno)
    return struct_rusage(ru)

def getrlimit(resource):
    if not(0 <= resource < RLIM_NLIMITS):
        return ValueError("invalid resource specified")

    rlim = rlimit()
    ret = _getrlimit(resource, byref(rlim))
    if ret == -1:
        errno = get_errno()
        raise ResourceError(errno)
    return (rlim.rlim_cur, rlim.rlim_max)

def setrlimit(resource, rlim):
    if not(0 <= resource < RLIM_NLIMITS):
        return ValueError("invalid resource specified")
    rlim = rlimit(rlim[0], rlim[1])

    ret = _setrlimit(resource, byref(rlim))
    if ret == -1:
        errno = get_errno()
        if errno == EINVAL:
            return ValueError("current limit exceeds maximum limit")
        elif errno == EPERM:
            return ValueError("not allowed to raise maximum limit")
        else:
            raise ResourceError(errno)

def getpagesize():
    pagesize = 0
    if _getpagesize:
        return _getpagesize()
    else:
        try:
            return sysconf("SC_PAGE_SIZE")
        except ValueError:
            # Irix 5.3 has _SC_PAGESIZE, but not _SC_PAGE_SIZE
            return sysconf("SC_PAGESIZE")

__all__ = _CONSTANTS + tuple(optional_constants) + (
    'ResourceError', 'timeval', 'struct_rusage', 'rlimit',
    'getrusage', 'getrlimit', 'setrlimit', 'getpagesize',
)

del optional_constants

