from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.rlib.rarithmetic import ovfcheck_float_to_int
from ctypes import *
import math
import os
import sys

_POSIX = os.name == "posix"
_WIN = os.name == "nt"

_include = "#include <time.h>"
if _POSIX:
    _include = """%s
    #include <sys/time.h>""" % _include
    
class CConfig:
    _header_ = _include
    CLOCKS_PER_SEC = ctypes_platform.ConstantInteger("CLOCKS_PER_SEC")
    clock_t = ctypes_platform.SimpleType("clock_t", c_ulong)
    time_t = ctypes_platform.SimpleType("time_t", c_long)
    size_t = ctypes_platform.SimpleType("size_t", c_long)
    
if _POSIX:
    CConfig.timeval = ctypes_platform.Struct("struct timeval", [("tv_sec", c_int),
                                                                ("tv_usec", c_int)])
    CConfig.tm = ctypes_platform.Struct("struct tm", [("tm_sec", c_int),
        ("tm_min", c_int), ("tm_hour", c_int), ("tm_mday", c_int),
        ("tm_mon", c_int), ("tm_year", c_int), ("tm_wday", c_int),
        ("tm_yday", c_int), ("tm_isdst", c_int), ("tm_gmtoff", c_long),
        ("tm_zone", c_char_p)])
elif _WIN:
    from ctypes import wintypes
    CConfig.tm = ctypes_platform.Struct("struct tm", [("tm_sec", c_int),
        ("tm_min", c_int), ("tm_hour", c_int), ("tm_mday", c_int),
        ("tm_mon", c_int), ("tm_year", c_int), ("tm_wday", c_int),
        ("tm_yday", c_int), ("tm_isdst", c_int)])
    
    LARGE_INTEGER = wintypes.LARGE_INTEGER
    BOOL = wintypes.BOOL
    DWORD = wintypes.DWORD

class cConfig:
    pass
cConfig.__dict__.update(ctypes_platform.configure(CConfig))
cConfig.tm.__name__ = "_tm"

if _POSIX:
    cConfig.timeval.__name__ = "_timeval"
    timeval = cConfig.timeval

CLOCKS_PER_SEC = cConfig.CLOCKS_PER_SEC
clock_t = cConfig.clock_t
time_t = cConfig.time_t
size_t = cConfig.size_t
tm = cConfig.tm

has_gettimeofday = False
if hasattr(libc, "gettimeofday"):
    libc.gettimeofday.argtypes = [c_void_p, c_void_p]
    libc.gettimeofday.restype = c_int
    has_gettimeofday = True
libc.clock.restype = clock_t
libc.time.argtypes = [POINTER(time_t)]
libc.time.restype = time_t
libc.ctime.argtypes = [POINTER(time_t)]
libc.ctime.restype = c_char_p
libc.gmtime.argtypes = [POINTER(time_t)]
libc.gmtime.restype = POINTER(tm)
libc.localtime.argtypes = [POINTER(time_t)]
libc.localtime.restype = POINTER(tm)
libc.mktime.argtypes = [POINTER(tm)]
libc.mktime.restype = time_t
libc.asctime.argtypes = [POINTER(tm)]
libc.asctime.restype = c_char_p
if _POSIX:
    libc.tzset.restype = None # tzset() returns void
elif _WIN:
    QueryPerformanceCounter = windll.kernel32.QueryPerformanceCounter
    QueryPerformanceCounter.argtypes = [POINTER(LARGE_INTEGER)]
    QueryPerformanceCounter.restype = BOOL
    QueryPerformanceFrequency = windll.kernel32.QueryPerformanceFrequency
    QueryPerformanceFrequency.argtypes = [POINTER(LARGE_INTEGER)]
    QueryPerformanceFrequency.restype = BOOL
    Sleep = windll.kernel32.Sleep
    Sleep.argtypes = [DWORD]
    Sleep.restype = None
libc.strftime.argtypes = [c_char_p, size_t, c_char_p, POINTER(tm)]
libc.strftime.restype = size_t


def _init_accept2dyear():
    return (1, 0)[bool(os.getenv("PYTHONY2K"))]

def _init_timezone():
    timezone = daylight = altzone = 0
    tzname = ["", ""]
    
    # pypy cant' use in_dll to access global exported variables
    # so we can't compute these attributes

    # if _WIN:
    #     cdll.msvcrt._tzset()
    # 
    #     timezone = c_long.in_dll(cdll.msvcrt, "_timezone").value
    #     if hasattr(cdll.msvcrt, "altzone"):
    #         altzone = c_long.in_dll(cdll.msvcrt, "altzone").value
    #     else:
    #         altzone = timezone - 3600
    #     daylight = c_long.in_dll(cdll.msvcrt, "_daylight").value
    #     tzname = _tzname_t.in_dll(cdll.msvcrt, "_tzname")
    #     tzname = (tzname.tzname_0, tzname.tzname_1)
    if _POSIX:
        YEAR = (365 * 24 + 6) * 3600

        t = (((libc.time(byref(time_t(0)))) / YEAR) * YEAR)
        tt = time_t(t)
        p = libc.localtime(byref(tt)).contents
        janzone = -p.tm_gmtoff
        janname = ["   ", p.tm_zone][bool(p.tm_zone)]
        tt = time_t(tt.value + YEAR / 2)
        p = libc.localtime(byref(tt)).contents
        julyzone = -p.tm_gmtoff
        julyname = ["   ", p.tm_zone][bool(p.tm_zone)]

        if janzone < julyzone:
            # DST is reversed in the southern hemisphere
            timezone = julyzone
            altzone = janzone
            daylight = int(janzone != julyzone)
            tzname = [julyname, janname]
        else:
            timezone = janzone
            altzone = julyzone
            daylight = int(janzone != julyzone)
            tzname = [janname, julyname]
    
    return timezone, daylight, tzname, altzone

def _get_error_msg():
    errno = geterrno()
    return os.strerror(errno)
    
def _floattime():
    """ _floattime() -> computes time since the Epoch for various platforms.

    Since on some system gettimeofday may fail we fall back on ftime
    or time.

    gettimeofday() has a resolution in microseconds
    ftime() has a resolution in milliseconds and it never fails
    time() has a resolution in seconds
    """

    if has_gettimeofday:
        t = timeval()
        if libc.gettimeofday(byref(t), c_void_p(None)) == 0:
            return float(t.tv_sec) + t.tv_usec * 0.000001

    return float(libc.time(None))

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

if _WIN:
    def sleep(space, w_secs):
        """sleep(seconds)
    
        Delay execution for a given number of seconds.  The argument may be
        a floating point number for subsecond precision."""
        
        secs = space.float_w(w_secs)
        if secs < 0.0:
            secs = 0.0
        msecs = secs * 1000.0
        try:
            msecs = ovfcheck_float_to_int(msecs)
        except OverflowError:
            raise OperationError(space.w_OverflowError, 
                                 space.wrap("sleep length is too large"))
        ul_millis = c_ulong(msecs)
        Sleep(ul_millis)

def _get_module_object(space, obj_name):
    w_module = space.getbuiltinmodule('time')
    w_obj = space.getattr(w_module, space.wrap(obj_name))
    return w_obj

def _set_module_object(space, obj_name, w_obj_value):
    w_module = space.getbuiltinmodule('time')
    space.setattr(w_module, space.wrap(obj_name), w_obj_value)

def _get_inttime(space, w_seconds):
    # w_seconds can be a wrapped None (it will be automatically wrapped
    # in the callers, so we never get a real None here).
    if space.is_w(w_seconds, space.w_None):
        seconds = _floattime()
    else:
        seconds = space.float_w(w_seconds)
    try:
        return ovfcheck_float_to_int(seconds)
    except OverflowError:
        raise OperationError(space.w_ValueError,
                             space.wrap("time argument too large"))

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
    
    w_struct_time = _get_module_object(space, 'struct_time')
    w_time_tuple = space.newtuple(time_tuple)
    return space.call_function(w_struct_time, w_time_tuple)

def _gettmarg(space, w_tup, allowNone=True):
    if allowNone and space.is_w(w_tup, space.w_None):
        # default to the current local time
        tt = time_t(int(_floattime())) 
        pbuf = libc.localtime(byref(tt))
        if not pbuf:
            raise OperationError(space.w_ValueError,
                space.wrap(_get_error_msg()))
        return pbuf.contents

    tup_w = space.unpackiterable(w_tup)
    if len(tup_w) != 9:
        raise OperationError(space.w_TypeError, 
                             space.wrap("argument must be sequence of "
                                        "length 9, not %d" % len(tup_w)))

    buf = tm()
    y = space.int_w(tup_w[0])
    buf.tm_mon = space.int_w(tup_w[1])
    buf.tm_mday = space.int_w(tup_w[2])
    buf.tm_hour = space.int_w(tup_w[3])
    buf.tm_min = space.int_w(tup_w[4])
    buf.tm_sec = space.int_w(tup_w[5])
    buf.tm_wday = space.int_w(tup_w[6])
    buf.tm_yday = space.int_w(tup_w[7])
    buf.tm_isdst = space.int_w(tup_w[8])

    w_accept2dyear = _get_module_object(space, "accept2dyear")
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

    if buf.tm_wday < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("day of week out of range"))

    buf.tm_year = y - 1900
    buf.tm_mon = buf.tm_mon - 1
    buf.tm_wday = (buf.tm_wday + 1) % 7
    buf.tm_yday = buf.tm_yday - 1

    return buf

def time(space):
    """time() -> floating point number

    Return the current time in seconds since the Epoch.
    Fractions of a second may be present if the system clock provides them."""
    
    secs = _floattime()
    return space.wrap(secs)

if _WIN:
    class PCCache:
        pass
    pccache = PCCache()
    pccache.divisor = 0.0
    pccache.ctrStart = LARGE_INTEGER()

def clock(space):
    """clock() -> floating point number

    Return the CPU time or real time since the start of the process or since
    the first call to clock().  This has as much precision as the system
    records."""

    if _POSIX:
        res = float(libc.clock()) / CLOCKS_PER_SEC
        return space.wrap(res)
    elif _WIN:
        if pccache.divisor == 0.0:
            freq = LARGE_INTEGER()
            res = QueryPerformanceFrequency(byref(freq))
            if not res or not freq:
                return space.wrap(float(libc.clock()) / CLOCKS_PER_SEC)
            pccache.divisor = float(freq.value)
            QueryPerformanceCounter(byref(pccache.ctrStart))

        now = LARGE_INTEGER()
        QueryPerformanceCounter(byref(now))
        diff = float(now.value - pccache.ctrStart.value)
        return space.wrap(diff / pccache.divisor)

def ctime(space, w_seconds=None):
    """ctime([seconds]) -> string

    Convert a time in seconds since the Epoch to a string in local time.
    This is equivalent to asctime(localtime(seconds)). When the time tuple is
    not present, current time as returned by localtime() is used."""

    seconds = _get_inttime(space, w_seconds)
    tt = time_t(seconds)

    p = libc.ctime(byref(tt))
    if not p:
        raise OperationError(space.w_ValueError,
            space.wrap("unconvertible time"))

    return space.wrap(p[:-1]) # get rid of new line
ctime.unwrap_spec = [ObjSpace, W_Root]

# by now w_tup is an optional argument (and not *args)
# because of the ext. compiler bugs in handling such arguments (*args, **kwds)
def asctime(space, w_tup=None):
    """asctime([tuple]) -> string

    Convert a time tuple to a string, e.g. 'Sat Jun 06 16:26:11 1998'.
    When the time tuple is not present, current time as returned by localtime()
    is used."""
    buf_value = _gettmarg(space, w_tup)
    p = libc.asctime(byref(buf_value))
    if not p:
        raise OperationError(space.w_ValueError,
            space.wrap("unconvertible time"))
    
    return space.wrap(p[:-1]) # get rid of new line
asctime.unwrap_spec = [ObjSpace, W_Root]

def gmtime(space, w_seconds=None):
    """gmtime([seconds]) -> (tm_year, tm_mon, tm_day, tm_hour, tm_min,
                          tm_sec, tm_wday, tm_yday, tm_isdst)

    Convert seconds since the Epoch to a time tuple expressing UTC (a.k.a.
    GMT).  When 'seconds' is not passed in, convert the current time instead.
    """

    # rpython does not support that a variable has two incompatible builtins
    # as value so we have to duplicate the code. NOT GOOD! see localtime() too
    seconds = _get_inttime(space, w_seconds)
    whent = time_t(seconds)
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

    seconds = _get_inttime(space, w_seconds)
    whent = time_t(seconds)
    p = libc.localtime(byref(whent))
    
    if not p:
        raise OperationError(space.w_ValueError, space.wrap(_get_error_msg()))
    return _tm_to_tuple(space, p.contents)
localtime.unwrap_spec = [ObjSpace, W_Root]

def mktime(space, w_tup):
    """mktime(tuple) -> floating point number

    Convert a time tuple in local time to seconds since the Epoch."""

    buf = _gettmarg(space, w_tup, allowNone=False)
    tt = libc.mktime(byref(buf))
    if tt == -1:
        raise OperationError(space.w_OverflowError,
            space.wrap("mktime argument out of range"))

    return space.wrap(float(tt))
mktime.unwrap_spec = [ObjSpace, W_Root]

if _POSIX:
    def tzset(space):
        """tzset()

        Initialize, or reinitialize, the local timezone to the value stored in
        os.environ['TZ']. The TZ environment variable should be specified in
        standard Unix timezone format as documented in the tzset man page
        (eg. 'US/Eastern', 'Europe/Amsterdam'). Unknown timezones will silently
        fall back to UTC. If the TZ environment variable is not set, the local
        timezone is set to the systems best guess of wallclock time.
        Changing the TZ environment variable without calling tzset *may* change
        the local timezone used by methods such as localtime, but this behaviour
        should not be relied on"""

        libc.tzset()
        
        # reset timezone, altzone, daylight and tzname
        timezone, daylight, tzname, altzone = _init_timezone()
        _set_module_object(space, "timezone", space.wrap(timezone))
        _set_module_object(space, 'daylight', space.wrap(daylight))
        tzname_w = [space.wrap(tzname[0]), space.wrap(tzname[1])] 
        _set_module_object(space, 'tzname', space.newtuple(tzname_w))
        _set_module_object(space, 'altzone', space.wrap(altzone))
    tzset.unwrap_spec = [ObjSpace]

def strftime(space, format, w_tup=None):
    """strftime(format[, tuple]) -> string

    Convert a time tuple to a string according to a format specification.
    See the library reference manual for formatting codes. When the time tuple
    is not present, current time as returned by localtime() is used."""

    buf_value = _gettmarg(space, w_tup)

    # Checks added to make sure strftime() does not crash Python by
    # indexing blindly into some array for a textual representation
    # by some bad index (fixes bug #897625).
    # No check for year since handled in gettmarg().
    if buf_value.tm_mon < 0 or buf_value.tm_mon > 11:
        raise OperationError(space.w_ValueError,
            space.wrap("month out of range"))
    if buf_value.tm_mday < 1 or buf_value.tm_mday > 31:
        raise OperationError(space.w_ValueError,
            space.wrap("day of month out of range"))
    if buf_value.tm_hour < 0 or buf_value.tm_hour > 23:
        raise OperationError(space.w_ValueError,
            space.wrap("hour out of range"))
    if buf_value.tm_min < 0 or buf_value.tm_min > 59:
        raise OperationError(space.w_ValueError,
            space.wrap("minute out of range"))
    if buf_value.tm_sec < 0 or buf_value.tm_sec > 61:
        raise OperationError(space.w_ValueError,
            space.wrap("seconds out of range"))
    if buf_value.tm_yday < 0 or buf_value.tm_yday > 365:
        raise OperationError(space.w_ValueError,
            space.wrap("day of year out of range"))
    if buf_value.tm_isdst < -1 or buf_value.tm_isdst > 1:
        raise OperationError(space.w_ValueError,
            space.wrap("daylight savings flag out of range"))

    i = 1024
    while True:
        outbuf = create_string_buffer(i)
        buflen = libc.strftime(outbuf, i, format, byref(buf_value))

        if buflen > 0 or i >= 256 * len(format):
            # if the buffer is 256 times as long as the format,
            # it's probably not failing for lack of room!
            # More likely, the format yields an empty result,
            # e.g. an empty format, or %Z when the timezone
            # is unknown.
            if buflen < 0: buflen = 0    # should not occur
            return space.wrap(outbuf.value[:buflen])

        i += i
strftime.unwrap_spec = [ObjSpace, str, W_Root]
