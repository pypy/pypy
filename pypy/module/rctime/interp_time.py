from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.gateway import W_Root
from ctypes import *
import os
import math

_POSIX = os.name == "posix"

class CConfig:
    _header_ = """
    #include <sys/time.h>
    #include <time.h>
    """
    timeval = ctypes_platform.Struct("struct timeval", [("tv_sec", c_int),
        ("tv_usec", c_int)])
    tm = ctypes_platform.Struct("struct tm", [("tm_sec", c_int),
        ("tm_min", c_int), ("tm_hour", c_int), ("tm_mday", c_int),
        ("tm_mon", c_int), ("tm_year", c_int), ("tm_wday", c_int),
        ("tm_yday", c_int), ("tm_isdst", c_int), ("tm_gmtoff", c_long),
        ("tm_zone", c_char_p)])
    CLOCKS_PER_SEC = ctypes_platform.ConstantInteger("CLOCKS_PER_SEC")
    clock_t = ctypes_platform.SimpleType("clock_t", c_ulong)
    time_t = ctypes_platform.SimpleType("time_t", c_long)

class cConfig:
    pass
cConfig.__dict__.update(ctypes_platform.configure(CConfig))
cConfig.timeval.__name__ = "ctimeval"
cConfig.tm.__name__ = "ctm"

libc.strerror.restype = c_char_p

has_gettimeofday = False
if hasattr(libc, "gettimeofday"):
    libc.gettimeofday.argtypes = [c_void_p, c_void_p]
    libc.gettimeofday.restype = c_int
    has_gettimeofday = True

libc.clock.restype = cConfig.clock_t
libc.time.argtypes = [POINTER(cConfig.time_t)]
libc.time.restype = cConfig.time_t
libc.ctime.argtypes = [POINTER(cConfig.time_t)]
libc.ctime.restype = c_char_p
libc.gmtime.argtypes = [POINTER(cConfig.time_t)]
libc.gmtime.restype = POINTER(cConfig.tm)
libc.localtime.argtypes = [POINTER(cConfig.time_t)]
libc.localtime.restype = POINTER(cConfig.tm)
libc.mktime.argtypes = [POINTER(cConfig.tm)]
libc.mktime.restype = cConfig.time_t

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

def _check_float(space, seconds):
    w_check_float = _get_app_object(space, "_check_float")
    space.call_function(w_check_float, space.wrap(seconds))
    
def _get_app_object(space, obj_name):
    w_module = space.getbuiltinmodule('rctime')
    w_obj = space.getattr(w_module, space.wrap(obj_name))
    return w_obj

def _get_floattime(space, w_seconds):
    # this check is done because None will be automatically wrapped
    if space.is_w(w_seconds, space.w_None):
        seconds = _floattime()
    else:
        seconds = space.float_w(w_seconds)
        _check_float(space, seconds)
    return seconds

def _tm_to_tuple(space, t):
    time_tuple = []

    time_tuple.append(space.wrap(t.tm_year + 1900))
    time_tuple.append(space.wrap(t.tm_mon + 1)) # want january == 1
    time_tuple.append(space.wrap(t.tm_mday))
    time_tuple.append(space.wrap(t.tm_hour))
    time_tuple.append(space.wrap(t.tm_min))
    time_tuple.append(space.wrap(t.tm_sec))
    time_tuple.append(space.wrap((t.tm_wday + 6) % 7)) # want monday == 0
    time_tuple.append(space.wrap(t.tm_yday + 1)) # want january, 1 == 1
    time_tuple.append(space.wrap(t.tm_isdst))
    
    w_struct_time = _get_app_object(space, 'struct_time')
    w_time_tuple = space.newtuple(time_tuple)
    return space.call_function(w_struct_time, w_time_tuple)

def _gettmarg(space, w_tup, buf):
    y = space.int_w(w_tup[0])
    buf.tm_mon = space.int_w(w_tup[1])
    buf.tm_mday = space.int_w(w_tup[2])
    buf.tm_hour = space.int_w(w_tup[3])
    buf.tm_min = space.int_w(w_tup[4])
    buf.tm_sec = space.int_w(w_tup[5])
    buf.tm_wday = space.int_w(w_tup[6])
    buf.tm_yday = space.int_w(w_tup[7])
    buf.tm_isdst = space.int_w(w_tup[8])

    w_accept2dyear = _get_app_object(space, "accept2dyear")
    accept2dyear = space.int_w(w_accept2dyear)
    
    if y < 1900:
        if not accept2dyear:
            raise OperationError(space.w_ValueError,
                space.wrap("year >= 1900 required"))

        if 69 <= y <= 99:
            y += 1900
        elif 0 <= y <= 68:
            y += 2000
        else:
            raise OperationError(space.w_ValueError,
                space.wrap("year out of range"))

    buf.tm_year = y - 1900
    buf.tm_mon = buf.tm_mon - 1
    buf.tm_wday = int(math.fmod((buf.tm_wday + 1), 7))
    buf.tm_yday = buf.tm_yday - 1

    return buf

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

def ctime(space, w_seconds=None):
    """ctime([seconds]) -> string

    Convert a time in seconds since the Epoch to a string in local time.
    This is equivalent to asctime(localtime(seconds)). When the time tuple is
    not present, current time as returned by localtime() is used."""

    seconds = _get_floattime(space, w_seconds)
    tt = cConfig.time_t(int(seconds))

    p = libc.ctime(byref(tt))
    if not p:
        raise OperationError(space.w_ValueError,
            space.wrap("unconvertible time"))

    return space.wrap(p[:-1]) # get rid of new line
ctime.unwrap_spec = [ObjSpace, W_Root]

def gmtime(space, w_seconds=None):
    """gmtime([seconds]) -> (tm_year, tm_mon, tm_day, tm_hour, tm_min,
                          tm_sec, tm_wday, tm_yday, tm_isdst)

    Convert seconds since the Epoch to a time tuple expressing UTC (a.k.a.
    GMT).  When 'seconds' is not passed in, convert the current time instead.
    """

    # rpython does not support that a variable has two incompatible builtins
    # as value so we have to duplicate the code. NOT GOOD! see localtime()
    seconds = _get_floattime(space, w_seconds)
    whent = cConfig.time_t(int(seconds))
    p = libc.gmtime(byref(whent))
    
    if not p:
        raise OperationError(space.w_ValueError, space.wrap(_get_error_msg()))
    return _tm_to_tuple(space, p.contents)
gmtime.unwrap_spec = [ObjSpace, W_Root]

def localtime(space, w_seconds=None):
    """localtime([seconds]) -> (tm_year, tm_mon, tm_day, tm_hour, tm_min,
                             tm_sec, tm_wday, tm_yday, tm_isdst)

    Convert seconds since the Epoch to a time tuple expressing local time.
    When 'seconds' is not passed in, convert the current time instead."""

    seconds = _get_floattime(space, w_seconds)
    whent = cConfig.time_t(int(seconds))
    p = libc.localtime(byref(whent))
    
    if not p:
        raise OperationError(space.w_ValueError, space.wrap(_get_error_msg()))
    return _tm_to_tuple(space, p.contents)
localtime.unwrap_spec = [ObjSpace, W_Root]

def mktime(space, w_tup):
    """mktime(tuple) -> floating point number

    Convert a time tuple in local time to seconds since the Epoch."""
    
    if space.is_w(w_tup, space.w_None):
        raise OperationError(space.w_TypeError, 
            space.wrap("argument must be 9-item sequence not None"))
    else:
        tup = space.unpackiterable(w_tup)
    
    if 1 < len(tup) < 9:
        raise OperationError(space.w_TypeError,
            space.wrap("argument must be a sequence of length 9, not %d"\
                % len(tup)))

    tt = cConfig.time_t(int(_floattime()))
    
    buf = libc.localtime(byref(tt))
    if not buf:
        raise OperationError(space.w_ValueError, space.wrap(_get_error_msg()))
    
    buf = _gettmarg(space, tup, buf.contents)

    tt = libc.mktime(byref(buf))
    if tt == -1:
        raise OperationError(space.w_OverflowError,
            space.wrap("mktime argument out of range"))

    return space.wrap(float(tt))
mktime.unwrap_spec = [ObjSpace, W_Root]
