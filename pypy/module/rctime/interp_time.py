from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError
from ctypes import *
import os

_POSIX = os.name == "posix"

class CConfig:
    _header_ = """
    #include <sys/time.h>
    #include <time.h>
    """
    timeval = ctypes_platform.Struct("struct timeval", [("tv_sec", c_int), ("tv_usec", c_int)])
    CLOCKS_PER_SEC = ctypes_platform.ConstantInteger("CLOCKS_PER_SEC")
    clock_t = ctypes_platform.SimpleType("clock_t", c_ulong)

class cConfig:
    pass
cConfig.__dict__.update(ctypes_platform.configure(CConfig))
cConfig.timeval.__name__ = "ctimeval"

libc.strerror.restype = c_char_p

has_gettimeofday = False
if hasattr(libc, "gettimeofday"):
    libc.gettimeofday.argtypes = [c_void_p, c_void_p]
    libc.gettimeofday.restype = c_int
    has_gettimeofday = True

libc.clock.restype = cConfig.clock_t

def _init_accept2dyear():
    return (1, 0)[bool(os.getenv("PYTHONY2K"))]

def _get_error_msg():
    errno = geterrno()
    return libc.strerror(errno)
    
def _floattime():
    """ _floattime() -> computes time since the Epoch for various platforms.

    Since on some system gettimeofday may fail we fall back on ftime
    or time.

    gettimeofday() has a resolution in microseconds
    ftime() has a resolution in milliseconds and it never fails
    time() has a resolution in seconds
    """

    # if _MS_WINDOWS:
    #     return libc.time(None)
    #
    if has_gettimeofday:
        t = cConfig.timeval()
        if libc.gettimeofday(byref(t), c_void_p(None)) == 0:
            return float(t.tv_sec) + t.tv_usec * 0.000001
    return 0.0


    # elif hasattr(_libc, "ftime"):
    #     t = _timeb()
    #     _libc.ftime.argtypes = [c_void_p]
    #     _libc.ftime(byref(t))
    #     return float(t.time) + float(t.millitm) * 0.001
    # elif hasattr(_libc, "time"):
    #     t = c_long()
    #     _libc.time.argtypes = [c_void_p]
    #     _libc.time(byref(t))
    #     return t.value

def time(space):
    secs = _floattime()
    return space.wrap(secs)

def clock(space):
    """clock() -> floating point number

    Return the CPU time or real time since the start of the process or since
    the first call to clock().  This has as much precision as the system
    records."""

    if _POSIX:
        res = float(float(libc.clock()) / cConfig.CLOCKS_PER_SEC)
        return space.wrap(res)
    # elif _MS_WINDOWS:
    #     divisor = 0.0
    #     ctrStart = _LARGE_INTEGER()
    #     now = _LARGE_INTEGER()
    # 
    #     if divisor == 0.0:
    #         freq = _LARGE_INTEGER()
    #         windll.kernel32.QueryPerformanceCounter(byref(ctrStart))
    #         res = windll.kernel32.QueryPerformanceCounter(byref(freq))
    #         if not res or freq.QuadPart == 0:
    #             return float(windll.msvcrt.clock())
    #         divisor = float(freq.QuadPart)
    # 
    #     windll.kernel32.QueryPerformanceCounter(byref(now))
    #     diff = float(now.QuadPart - ctrStart.QuadPart)
    #     return float(diff / divisor)
