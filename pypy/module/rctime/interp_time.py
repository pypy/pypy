from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
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
    size_t = ctypes_platform.SimpleType("size_t", c_long)

class cConfig:
    pass
cConfig.__dict__.update(ctypes_platform.configure(CConfig))
cConfig.timeval.__name__ = "_timeval"
cConfig.tm.__name__ = "_tm"

CLOCKS_PER_SEC = cConfig.CLOCKS_PER_SEC
clock_t = cConfig.clock_t
time_t = cConfig.time_t
size_t = cConfig.size_t
timeval = cConfig.timeval
tm = cConfig.tm


has_gettimeofday = False
if hasattr(libc, "gettimeofday"):
    libc.gettimeofday.argtypes = [c_void_p, c_void_p]
    libc.gettimeofday.restype = c_int
    has_gettimeofday = True
libc.strerror.restype = c_char_p
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
libc.tzset.restype = None # tzset() returns void
libc.strftime.argtypes = [c_char_p, size_t, c_char_p, POINTER(tm)]
libc.strftime.restype = size_t

def _init_accept2dyear():
    return (1, 0)[bool(os.getenv("PYTHONY2K"))]

def _init_timezone():
    timezone = daylight = tzname = altzone = None

    # if _MS_WINDOWS:
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
        t = timeval()
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
    # this call the app level _check_float to check the type of
    # the given seconds
    w_check_float = _get_module_object(space, "_check_float")
    space.call_function(w_check_float, space.wrap(seconds))
    
def _get_module_object(space, obj_name):
    w_module = space.getbuiltinmodule('rctime')
    w_obj = space.getattr(w_module, space.wrap(obj_name))
    return w_obj

def _set_module_object(space, obj_name, obj_value):
    w_module = space.getbuiltinmodule('rctime')
    space.setattr(w_module, space.wrap(obj_name), space.wrap(obj_value))

# duplicated function to make the annotator work correctly
def _set_module_list_object(space, list_name, list_value):
    w_module = space.getbuiltinmodule('rctime')
    space.setattr(w_module, space.wrap(list_name), space.newlist(list_value))

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
    
    w_struct_time = _get_module_object(space, 'struct_time')
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

    buf.tm_year = y - 1900
    buf.tm_mon = buf.tm_mon - 1
    buf.tm_wday = int(math.fmod((buf.tm_wday + 1), 7))
    buf.tm_yday = buf.tm_yday - 1

    return buf

def time(space):
    """time() -> floating point number

    Return the current time in seconds since the Epoch.
    Fractions of a second may be present if the system clock provides them."""
    
    secs = _floattime()
    return space.wrap(secs)

def clock(space):
    """clock() -> floating point number

    Return the CPU time or real time since the start of the process or since
    the first call to clock().  This has as much precision as the system
    records."""

    if _POSIX:
        res = float(float(libc.clock()) / CLOCKS_PER_SEC)
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
    tt = time_t(int(seconds))

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
    tup = None
    tuple_len = 0
    buf_value = tm()
    
    # if len(tup_w):
    #     w_tup = tup_w[0]
    if not space.is_w(w_tup, space.w_None):
        tuple_len = space.int_w(space.len(w_tup))
        
        # if space.is_w(w_tup, space.w_None) or 1 < tuple_len < 9:
        if 1 < tuple_len < 9:
            raise OperationError(space.w_TypeError, 
                space.wrap("argument must be 9-item sequence"))
    
        # check if every passed object is a int
        tup = space.unpackiterable(w_tup)
        for t in tup:
            space.int_w(t)
        # map(space.int_w, tup) # XXX: can't use it
        
        buf_value = _gettmarg(space, tup, buf_value)
    else:
        # empty list
        buf = None
        
        tt = time_t(int(_floattime())) 
        buf = libc.localtime(byref(tt))
        if not buf:
            raise OperationError(space.w_ValueError,
                space.wrap(_get_error_msg()))
        buf_value = buf.contents
    
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
    seconds = _get_floattime(space, w_seconds)
    whent = time_t(int(seconds))
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
    whent = time_t(int(seconds))
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
        tup_w = space.unpackiterable(w_tup)
    
    if 1 < len(tup_w) < 9:
        raise OperationError(space.w_TypeError,
            space.wrap("argument must be a sequence of length 9, not %d"\
                % len(tup_w)))

    tt = time_t(int(_floattime()))
    
    buf = libc.localtime(byref(tt))
    if not buf:
        raise OperationError(space.w_ValueError, space.wrap(_get_error_msg()))
    
    buf = _gettmarg(space, tup_w, buf.contents)

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
        _set_module_object(space, "timezone", timezone)
        _set_module_object(space, 'daylight', daylight)
        tzname_w = [space.wrap(tzname[0]), space.wrap(tzname[1])] 
        _set_module_list_object(space, 'tzname', tzname_w)
        _set_module_object(space, 'altzone', altzone)
    tzset.unwrap_spec = [ObjSpace]

def strftime(space, w_format, w_tup=None):
    """strftime(format[, tuple]) -> string

    Convert a time tuple to a string according to a format specification.
    See the library reference manual for formatting codes. When the time tuple
    is not present, current time as returned by localtime() is used."""
    
    tup = None
    tuple_len = 0
    buf_value = tm()
    
    format = space.str_w(w_format)
    
    # if len(tup_w):
    #     w_tup = tup_w[0]
    if not space.is_w(w_tup, space.w_None):
        tuple_len = space.int_w(space.len(w_tup))
        
        #if space.is_w(w_tup, space.w_None) or 1 < tuple_len < 9:
        if 1 < tuple_len < 9:
            raise OperationError(space.w_TypeError, 
                space.wrap("argument must be 9-item sequence"))

        # check if every passed object is a int
        tup = space.unpackiterable(w_tup)
        for t in tup:
            space.int_w(t)
        # map(space.int_w, tup) # XXX: can't use it
        
        buf_value = _gettmarg(space, tup, buf_value)
    else:
        # empty list
        buf = None
        
        tt = time_t(int(_floattime())) 
        buf = libc.localtime(byref(tt))
        if not buf:
            raise OperationError(space.w_ValueError,
                space.wrap(_get_error_msg()))
        buf_value = buf.contents

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
    # tm_wday does not need checking of its upper-bound since taking
    #   "% 7" in gettmarg() automatically restricts the range.
    if buf_value.tm_wday < 0:
        raise OperationError(space.w_ValueError,
            space.wrap("day of week out of range"))
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
            if buflen > 0:
                return space.wrap(outbuf.value[:buflen])

        i += i
strftime.unwrap_spec = [ObjSpace, W_Root, W_Root]

def strptime(space, w_string, w_format="%a %b %d %H:%M:%S %Y"):
    """strptime(string, format) -> struct_time

    Parse a string to a time tuple according to a format specification.
    See the library reference manual for formatting codes
    (same as strftime())."""

    string = space.str_w(w_string)
    format = space.str_w(w_format)
    
    return _strptime(space, string, format)
strptime.unwrap_spec = [ObjSpace, W_Root, W_Root]

"""Strptime-related classes and functions.

CLASSES:
    LocaleTime -- Discovers and stores locale-specific time information
    TimeRE -- Creates regexes for pattern matching a string of text containing
                time information

FUNCTIONS:
    _getlang -- Figure out what language is being used for the locale
    strptime -- Calculates the time struct represented by the passed-in string

"""
import locale
import calendar
from re import compile as re_compile
from re import IGNORECASE
from re import escape as re_escape
from datetime import date as datetime_date

def _getlang():
    # Figure out what the current language is set to.
    return locale.getlocale(locale.LC_TIME)
    
def _struct_time(space, tuple):
    w_struct_time = _get_module_object(space, 'struct_time')
    w_time_tuple = space.newtuple(tuple)
    return space.call_function(w_struct_time, w_time_tuple)

class LocaleTime(object):
    """Stores and handles locale-specific information related to time.

    ATTRIBUTES:
        f_weekday -- full weekday names (7-item list)
        a_weekday -- abbreviated weekday names (7-item list)
        f_month -- full month names (13-item list; dummy value in [0], which
                    is added by code)
        a_month -- abbreviated month names (13-item list, dummy value in
                    [0], which is added by code)
        am_pm -- AM/PM representation (2-item list)
        LC_date_time -- format string for date/time representation (string)
        LC_date -- format string for date representation (string)
        LC_time -- format string for time representation (string)
        timezone -- daylight- and non-daylight-savings timezone representation
                    (2-item list of sets)
        lang -- Language used by instance (2-item tuple)
    """

    def __init__(self, space):
        """Set all attributes.

        Order of methods called matters for dependency reasons.

        The locale language is set at the offset and then checked again before
        exiting.  This is to make sure that the attributes were not set with a
        mix of information from more than one locale.  This would most likely
        happen when using threads where one thread calls a locale-dependent
        function while another thread changes the locale while the function in
        the other thread is still running.  Proper coding would call for
        locks to prevent changing the locale while locale-dependent code is
        running.  The check here is done in case someone does not think about
        doing this.

        Only other possible issue is if someone changed the timezone and did
        not call tz.tzset .  That is an issue for the programmer, though,
        since changing the timezone is worthless without that call.

        """
        self.space = space
        self.lang = _getlang()
        self.__calc_weekday()
        self.__calc_month()
        self.__calc_am_pm()
        self.__calc_timezone()
        self.__calc_date_time()
        if _getlang() != self.lang:
            raise ValueError("locale changed during initialization")

    def __pad(self, seq, front):
        # Add '' to seq to either the front (is True), else the back.
        seq = list(seq)
        if front:
            seq.insert(0, '')
        else:
            seq.append('')
        return seq

    def __calc_weekday(self):
        # Set self.a_weekday and self.f_weekday using the calendar
        # module.
        a_weekday = [calendar.day_abbr[i].lower() for i in range(7)]
        f_weekday = [calendar.day_name[i].lower() for i in range(7)]
        self.a_weekday = a_weekday
        self.f_weekday = f_weekday

    def __calc_month(self):
        # Set self.f_month and self.a_month using the calendar module.
        a_month = [calendar.month_abbr[i].lower() for i in range(13)]
        f_month = [calendar.month_name[i].lower() for i in range(13)]
        self.a_month = a_month
        self.f_month = f_month

    def __calc_am_pm(self):
        # Set self.am_pm by using strftime().

        # The magic date (1999,3,17,hour,44,55,2,76,0) is not really that
        # magical; just happened to have used it everywhere else where a
        # static date was needed.
        am_pm = []
        for hour in (01,22):
            time_tuple = [1999, 3, 17, hour, 44, 55, 2, 76, 0]
            w_res = strftime(self.space, self.space.wrap("%p"),
                self.space.wrap(time_tuple))
            res = self.space.str_w(w_res)
            am_pm.append(res.lower())
        self.am_pm = am_pm

    def __calc_date_time(self):
        # Set self.date_time, self.date, & self.time by using strftime().

        # Use (1999,3,17,22,44,55,2,76,0) for magic date because the amount of
        # overloaded numbers is minimized.  The order in which searches for
        # values within the format string is very important; it eliminates
        # possible ambiguity for what something represents.
        time_tuple = [1999, 3, 17, 22, 44, 55, 2, 76, 0]
        date_time = [None, None, None]
        date_time[0] = self.space.str_w(strftime(self.space,
            self.space.wrap("%c"), self.space.wrap(time_tuple))).lower()
        date_time[1] = self.space.str_w(strftime(self.space,
            self.space.wrap("%x"), self.space.wrap(time_tuple))).lower()    
        date_time[2] = self.space.str_w(strftime(self.space,
            self.space.wrap("%X"), self.space.wrap(time_tuple))).lower()    
        replacement_pairs = [('%', '%%'), (self.f_weekday[2], '%A'),
            (self.f_month[3], '%B'), (self.a_weekday[2], '%a'),
            (self.a_month[3], '%b'), (self.am_pm[1], '%p'),
            ('1999', '%Y'), ('99', '%y'), ('22', '%H'),
            ('44', '%M'), ('55', '%S'), ('76', '%j'),
            ('17', '%d'), ('03', '%m'), ('3', '%m'),
            # '3' needed for when no leading zero.
            ('2', '%w'), ('10', '%I')]
        replacement_pairs.extend([(tz, "%Z") for tz_values in self.timezone
                                                for tz in tz_values])
        for offset,directive in ((0,'%c'), (1,'%x'), (2,'%X')):
            current_format = date_time[offset]
            for old, new in replacement_pairs:
                # Must deal with possible lack of locale info
                # manifesting itself as the empty string (e.g., Swedish's
                # lack of AM/PM info) or a platform returning a tuple of empty
                # strings (e.g., MacOS 9 having timezone as ('','')).
                if old:
                    current_format = current_format.replace(old, new)
            # If %W is used, then Sunday, 2005-01-03 will fall on week 0 since
            # 2005-01-03 occurs before the first Monday of the year.  Otherwise
            # %U is used.
            time_tuple = [1999, 1, 3, 1, 1, 1, 6, 3, 0]
            res = self.space.str_w(strftime(self.space,
                self.space.wrap(directive), self.space.wrap(time_tuple)))
            if '00' in res:
                U_W = '%W'
            else:
                U_W = '%U'
            date_time[offset] = current_format.replace('11', U_W)
        self.LC_date_time = date_time[0]
        self.LC_date = date_time[1]
        self.LC_time = date_time[2]

    def __calc_timezone(self):
        # Set self.timezone by using tzname.
        # Do not worry about possibility of tzname[0] == timetzname[1]
        # and daylight; handle that in strptime .
        
        # get tzname
        w_tzname = _get_module_object(self.space, "tzname")
        tzname_w = self.space.unpackiterable(w_tzname)
        tzname = [self.space.str_w(i) for i in tzname_w]
        # get daylight
        w_daylight = _get_module_object(self.space, "daylight")
        daylight = self.space.int_w(w_daylight)

        try:
            tzset(self.space)
        except AttributeError:
            pass
        no_saving = frozenset(["utc", "gmt", tzname[0].lower()])
        if daylight:
            has_saving = frozenset([tzname[1].lower()])
        else:
            has_saving = frozenset()
        self.timezone = (no_saving, has_saving)

class TimeRE(dict):
    """Handle conversion from format directives to regexes."""

    def __init__(self, space, locale_time=None):
        """Create keys/values.

        Order of execution is important for dependency reasons.

        """
        self.space = space
        if locale_time:
            self.locale_time = locale_time
        else:
            self.locale_time = LocaleTime(self.space)
        base = super(TimeRE, self)
        base.__init__({
            # The " \d" part of the regex is to make %c from ANSI C work
            'd': r"(?P<d>3[0-1]|[1-2]\d|0[1-9]|[1-9]| [1-9])",
            'H': r"(?P<H>2[0-3]|[0-1]\d|\d)",
            'I': r"(?P<I>1[0-2]|0[1-9]|[1-9])",
            'j': r"(?P<j>36[0-6]|3[0-5]\d|[1-2]\d\d|0[1-9]\d|00[1-9]|[1-9]\d|0[1-9]|[1-9])",
            'm': r"(?P<m>1[0-2]|0[1-9]|[1-9])",
            'M': r"(?P<M>[0-5]\d|\d)",
            'S': r"(?P<S>6[0-1]|[0-5]\d|\d)",
            'U': r"(?P<U>5[0-3]|[0-4]\d|\d)",
            'w': r"(?P<w>[0-6])",
            # W is set below by using 'U'
            'y': r"(?P<y>\d\d)",
            #XXX: Does 'Y' need to worry about having less or more than
            #     4 digits?
            'Y': r"(?P<Y>\d\d\d\d)",
            'A': self.__seqToRE(self.locale_time.f_weekday, 'A'),
            'a': self.__seqToRE(self.locale_time.a_weekday, 'a'),
            'B': self.__seqToRE(self.locale_time.f_month[1:], 'B'),
            'b': self.__seqToRE(self.locale_time.a_month[1:], 'b'),
            'p': self.__seqToRE(self.locale_time.am_pm, 'p'),
            'Z': self.__seqToRE((tz for tz_names in self.locale_time.timezone
                                        for tz in tz_names),
                                'Z'),
            '%': '%'})
        base.__setitem__('W', base.__getitem__('U').replace('U', 'W'))
        base.__setitem__('c', self.pattern(self.locale_time.LC_date_time))
        base.__setitem__('x', self.pattern(self.locale_time.LC_date))
        base.__setitem__('X', self.pattern(self.locale_time.LC_time))

    def __seqToRE(self, to_convert, directive):
        """Convert a list to a regex string for matching a directive.

        Want possible matching values to be from longest to shortest.  This
        prevents the possibility of a match occuring for a value that also
        a substring of a larger value that should have matched (e.g., 'abc'
        matching when 'abcdef' should have been the match).

        """
        to_convert = sorted(to_convert, key=len, reverse=True)
        for value in to_convert:
            if value != '':
                break
        else:
            return ''
        regex = '|'.join(re_escape(stuff) for stuff in to_convert)
        regex = '(?P<%s>%s' % (directive, regex)
        return '%s)' % regex

    def pattern(self, format):
        """Return regex pattern for the format string.

        Need to make sure that any characters that might be interpreted as
        regex syntax are escaped.

        """
        processed_format = ''
        # The sub() call escapes all characters that might be misconstrued
        # as regex syntax.  Cannot use re.escape since we have to deal with
        # format directives (%m, etc.).
        regex_chars = re_compile(r"([\\.^$*+?\(\){}\[\]|])")
        format = regex_chars.sub(r"\\\1", format)
        whitespace_replacement = re_compile('\s+')
        format = whitespace_replacement.sub('\s*', format)
        while '%' in format:
            directive_index = format.index('%')+1
            processed_format = "%s%s%s" % (processed_format,
                                           format[:directive_index-1],
                                           self[format[directive_index]])
            format = format[directive_index+1:]
        return "%s%s" % (processed_format, format)

    def compile(self, format):
        """Return a compiled re object for the format string."""
        return re_compile(self.pattern(format), IGNORECASE)

def _strptime(space, data_string, format="%a %b %d %H:%M:%S %Y"):
    """Return a time struct based on the input string and the format string."""

    _TimeRE_cache = TimeRE(space)
    _CACHE_MAX_SIZE = 5 # Max number of regexes stored in _regex_cache
    _regex_cache = {}
    
    # get tzname
    w_tzname = _get_module_object(space, "tzname")
    tzname_w = space.unpackiterable(w_tzname)
    tzname = [space.str_w(i) for i in tzname_w]
    # get daylight
    w_daylight = _get_module_object(space, "daylight")
    daylight = space.int_w(w_daylight)
    
    time_re = _TimeRE_cache
    locale_time = time_re.locale_time
    if _getlang() != locale_time.lang:
        _TimeRE_cache = TimeRE(space)
        _regex_cache = {}
    if len(_regex_cache) > _CACHE_MAX_SIZE:
        _regex_cache.clear()
    format_regex = _regex_cache.get(format)
    if not format_regex:
        try:
            format_regex = time_re.compile(format)
        # KeyError raised when a bad format is found; can be specified as
        # \\, in which case it was a stray % but with a space after it
        except KeyError, err:
            bad_directive = err.args[0]
            if bad_directive == "\\":
                bad_directive = "%"
            del err
            msg = "'%s' is a bad directive in format '%s'" %\
                (bad_directive, format)
            raise OperationError(space.w_ValueError,
                space.wrap(msg))
        # IndexError only occurs when the format string is "%"
        except IndexError:
            raise OperationError(space.w_ValueError,
                space.wrap("stray %% in format '%s'" % format))
        _regex_cache[format] = format_regex

    found = format_regex.match(data_string)
    if not found:
        raise OperationError(space.w_ValueError,
            space.wrap("time data did not match format:  data=%s  fmt=%s" % \
                (data_string, format)))
    if len(data_string) != found.end():
        raise OperationError(space.w_ValueError,
            space.wrap("unconverted data remains: %s" % \
                data_string[found.end():]))
    year = 1900
    month = day = 1
    hour = minute = second = 0
    tz = -1
    # Default to -1 to signify that values not known; not critical to have,
    # though
    week_of_year = -1
    week_of_year_start = -1
    # weekday and julian defaulted to -1 so as to signal need to calculate
    # values
    weekday = julian = -1
    found_dict = found.groupdict()
    for group_key in found_dict.iterkeys():
        # Directives not explicitly handled below:
        #   c, x, X
        #      handled by making out of other directives
        #   U, W
        #      worthless without day of the week
        if group_key == 'y':
            year = int(found_dict['y'])
            # Open Group specification for strptime() states that a %y
            #value in the range of [00, 68] is in the century 2000, while
            #[69,99] is in the century 1900
            if year <= 68:
                year += 2000
            else:
                year += 1900
        elif group_key == 'Y':
            year = int(found_dict['Y'])
        elif group_key == 'm':
            month = int(found_dict['m'])
        elif group_key == 'B':
            month = locale_time.f_month.index(found_dict['B'].lower())
        elif group_key == 'b':
            month = locale_time.a_month.index(found_dict['b'].lower())
        elif group_key == 'd':
            day = int(found_dict['d'])
        elif group_key == 'H':
            hour = int(found_dict['H'])
        elif group_key == 'I':
            hour = int(found_dict['I'])
            ampm = found_dict.get('p', '').lower()
            # If there was no AM/PM indicator, we'll treat this like AM
            if ampm in ('', locale_time.am_pm[0]):
                # We're in AM so the hour is correct unless we're
                # looking at 12 midnight.
                # 12 midnight == 12 AM == hour 0
                if hour == 12:
                    hour = 0
            elif ampm == locale_time.am_pm[1]:
                # We're in PM so we need to add 12 to the hour unless
                # we're looking at 12 noon.
                # 12 noon == 12 PM == hour 12
                if hour != 12:
                    hour += 12
        elif group_key == 'M':
            minute = int(found_dict['M'])
        elif group_key == 'S':
            second = int(found_dict['S'])
        elif group_key == 'A':
            weekday = locale_time.f_weekday.index(found_dict['A'].lower())
        elif group_key == 'a':
            weekday = locale_time.a_weekday.index(found_dict['a'].lower())
        elif group_key == 'w':
            weekday = int(found_dict['w'])
            if weekday == 0:
                weekday = 6
            else:
                weekday -= 1
        elif group_key == 'j':
            julian = int(found_dict['j'])
        elif group_key in ('U', 'W'):
            week_of_year = int(found_dict[group_key])
            if group_key == 'U':
                # U starts week on Sunday
                week_of_year_start = 6
            else:
                # W starts week on Monday
                week_of_year_start = 0
        elif group_key == 'Z':
            # Since -1 is default value only need to worry about setting tz if
            # it can be something other than -1.
            found_zone = found_dict['Z'].lower()
            for value, tz_values in enumerate(locale_time.timezone):
                if found_zone in tz_values:
                    # Deal with bad locale setup where timezone names are the
                    # same and yet daylight is true; too ambiguous to
                    # be able to tell what timezone has daylight savings
                    if (tzname[0] == tzname[1] and
                       daylight and found_zone not in ("utc", "gmt")):
                        break
                    else:
                        tz = value
                        break
    # If we know the week of the year and what day of that week, we can figure
    # out the Julian day of the year
    # Calculations below assume 0 is a Monday
    if julian == -1 and week_of_year != -1 and weekday != -1:
        # Calculate how many days in week 0
        first_weekday = datetime_date(year, 1, 1).weekday()
        preceeding_days = 7 - first_weekday
        if preceeding_days == 7:
            preceeding_days = 0
        # Adjust for U directive so that calculations are not dependent on
        # directive used to figure out week of year
        if weekday == 6 and week_of_year_start == 6:
            week_of_year -= 1
        # If a year starts and ends on a Monday but a week is specified to
        # start on a Sunday we need to up the week to counter-balance the fact
        # that with %W that first Monday starts week 1 while with %U that is
        # week 0 and thus shifts everything by a week
        if weekday == 0 and first_weekday == 0 and week_of_year_start == 6:
            week_of_year += 1
        # If in week 0, then just figure out how many days from Jan 1 to day of
        # week specified, else calculate by multiplying week of year by 7,
        # adding in days in week 0, and the number of days from Monday to the
        # day of the week
        if week_of_year == 0:
            julian = 1 + weekday - first_weekday
        else:
            days_to_week = preceeding_days + (7 * (week_of_year - 1))
            julian = 1 + days_to_week + weekday
    # Cannot pre-calculate datetime_date() since can change in Julian
    #calculation and thus could have different value for the day of the week
    #calculation
    if julian == -1:
        # Need to add 1 to result since first day of the year is 1, not 0.
        julian = datetime_date(year, month, day).toordinal() - \
                  datetime_date(year, 1, 1).toordinal() + 1
    else:  # Assume that if they bothered to include Julian day it will
           #be accurate
        datetime_result = datetime_date.fromordinal((julian - 1) +\
            datetime_date(year, 1, 1).toordinal())
        year = datetime_result.year
        month = datetime_result.month
        day = datetime_result.day
    if weekday == -1:
        weekday = datetime_date(year, month, day).weekday()
    return _struct_time(space, [year, month, day,
                        hour, minute, second,
                        weekday, julian, tz])
