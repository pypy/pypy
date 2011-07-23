from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.lltypesystem import rffi
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.rarithmetic import ovfcheck_float_to_int
from pypy.rlib import rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import os
import sys
import time as pytime

_POSIX = os.name == "posix"
_WIN = os.name == "nt"

if _WIN:
    # Interruptible sleeps on Windows:
    # We install a specific Console Ctrl Handler which sets an 'event'.
    # time.sleep() will actually call WaitForSingleObject with the desired
    # timeout.  On Ctrl-C, the signal handler is called, the event is set,
    # and the wait function exits.
    from pypy.rlib import rwin32
    from pypy.interpreter.error import wrap_windowserror, wrap_oserror
    from pypy.module.thread import ll_thread as thread

    eci = ExternalCompilationInfo(
        separate_module_sources=['''
            #include <windows.h>

            static HANDLE interrupt_event;

            static BOOL WINAPI CtrlHandlerRoutine(
              DWORD dwCtrlType)
            {
                SetEvent(interrupt_event);
                /* allow other default handlers to be called.
                 * Default Python handler will setup the
                 * KeyboardInterrupt exception.
                 */
                return 0;
            }

            BOOL pypy_timemodule_setCtrlHandler(HANDLE event)
            {
                interrupt_event = event;
                return SetConsoleCtrlHandler(CtrlHandlerRoutine, TRUE);
            }

        '''],
        export_symbols=['pypy_timemodule_setCtrlHandler'],
        )
    _setCtrlHandlerRoutine = rffi.llexternal(
        'pypy_timemodule_setCtrlHandler',
        [rwin32.HANDLE], rwin32.BOOL,
        compilation_info=eci)

    class GlobalState:
        def __init__(self):
            self.init()

        def init(self):
            self.interrupt_event = rwin32.NULL_HANDLE

        def startup(self, space):
            # Initialize the event handle used to signal Ctrl-C
            try:
                globalState.interrupt_event = rwin32.CreateEvent(
                    rffi.NULL, True, False, rffi.NULL)
            except WindowsError, e:
                raise wrap_windowserror(space, e)
            if not _setCtrlHandlerRoutine(globalState.interrupt_event):
                raise wrap_windowserror(
                    space, rwin32.lastWindowsError("SetConsoleCtrlHandler"))

    globalState = GlobalState()

    class State:
        def __init__(self, space):
            self.main_thread = 0

        def _freeze_(self):
            self.main_thread = 0
            globalState.init()

        def startup(self, space):
            self.main_thread = thread.get_ident()
            globalState.startup(space)

        def get_interrupt_event(self):
            return globalState.interrupt_event


_includes = ["time.h"]
if _POSIX:
    _includes.append('sys/time.h')

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes = _includes
    )
    CLOCKS_PER_SEC = platform.ConstantInteger("CLOCKS_PER_SEC")
    clock_t = platform.SimpleType("clock_t", rffi.ULONG)
    has_gettimeofday = platform.Has('gettimeofday')

if _POSIX:
    calling_conv = 'c'
    CConfig.timeval = platform.Struct("struct timeval",
                                      [("tv_sec", rffi.INT),
                                       ("tv_usec", rffi.INT)])
    CConfig.tm = platform.Struct("struct tm", [("tm_sec", rffi.INT),
        ("tm_min", rffi.INT), ("tm_hour", rffi.INT), ("tm_mday", rffi.INT),
        ("tm_mon", rffi.INT), ("tm_year", rffi.INT), ("tm_wday", rffi.INT),
        ("tm_yday", rffi.INT), ("tm_isdst", rffi.INT), ("tm_gmtoff", rffi.LONG),
        ("tm_zone", rffi.CCHARP)])
elif _WIN:
    calling_conv = 'win'
    CConfig.tm = platform.Struct("struct tm", [("tm_sec", rffi.INT),
        ("tm_min", rffi.INT), ("tm_hour", rffi.INT), ("tm_mday", rffi.INT),
        ("tm_mon", rffi.INT), ("tm_year", rffi.INT), ("tm_wday", rffi.INT),
        ("tm_yday", rffi.INT), ("tm_isdst", rffi.INT)])

class cConfig:
    pass

for k, v in platform.configure(CConfig).items():
    setattr(cConfig, k, v)
cConfig.tm.__name__ = "_tm"

def external(name, args, result, eci=CConfig._compilation_info_):
    if _WIN and rffi.sizeof(rffi.TIME_T) == 8:
        # Recent Microsoft compilers use 64bit time_t and
        # the corresponding functions are named differently
        if (rffi.TIME_T in args or rffi.TIME_TP in args
            or result in (rffi.TIME_T, rffi.TIME_TP)):
            name = '_' + name + '64'
    return rffi.llexternal(name, args, result,
                           compilation_info=eci,
                           calling_conv=calling_conv,
                           threadsafe=False)

if _POSIX:
    cConfig.timeval.__name__ = "_timeval"
    timeval = cConfig.timeval

CLOCKS_PER_SEC = cConfig.CLOCKS_PER_SEC
clock_t = cConfig.clock_t
tm = cConfig.tm
glob_buf = lltype.malloc(tm, flavor='raw', zero=True, immortal=True)

if cConfig.has_gettimeofday:
    c_gettimeofday = external('gettimeofday', [rffi.VOIDP, rffi.VOIDP], rffi.INT)
TM_P = lltype.Ptr(tm)
c_clock = external('clock', [rffi.TIME_TP], clock_t)
c_time = external('time', [rffi.TIME_TP], rffi.TIME_T)
c_ctime = external('ctime', [rffi.TIME_TP], rffi.CCHARP)
c_gmtime = external('gmtime', [rffi.TIME_TP], TM_P)
c_mktime = external('mktime', [TM_P], rffi.TIME_T)
c_asctime = external('asctime', [TM_P], rffi.CCHARP)
c_localtime = external('localtime', [rffi.TIME_TP], TM_P)
if _POSIX:
    c_tzset = external('tzset', [], lltype.Void)
if _WIN:
    win_eci = ExternalCompilationInfo(
        includes = ["time.h"],
        post_include_bits = ["long pypy_get_timezone();",
                             "int pypy_get_daylight();",
                             "char** pypy_get_tzname();"],
        separate_module_sources = ["""
        long pypy_get_timezone() { return timezone; }
        int pypy_get_daylight() { return daylight; }
        char** pypy_get_tzname() { return tzname; }
        """],
        export_symbols = [
        '_tzset', 'pypy_get_timezone', 'pypy_get_daylight', 'pypy_get_tzname'],
        )
    # Ensure sure that we use _tzset() and timezone from the same C Runtime.
    c_tzset = external('_tzset', [], lltype.Void, win_eci)
    c_get_timezone = external('pypy_get_timezone', [], rffi.LONG, win_eci)
    c_get_daylight = external('pypy_get_daylight', [], rffi.INT, win_eci)
    c_get_tzname = external('pypy_get_tzname', [], rffi.CCHARPP, win_eci)

c_strftime = external('strftime', [rffi.CCHARP, rffi.SIZE_T, rffi.CCHARP, TM_P],
                      rffi.SIZE_T)

def _init_accept2dyear(space):
    if os.environ.get("PYTHONY2K"):
        accept2dyear = 0
    else:
        accept2dyear = 1
    _set_module_object(space, "accept2dyear", space.wrap(accept2dyear))

def _init_timezone(space):
    timezone = daylight = altzone = 0
    tzname = ["", ""]

    if _WIN:
         c_tzset()
         timezone = c_get_timezone()
         altzone = timezone - 3600
         daylight = c_get_daylight()
         tzname_ptr = c_get_tzname()
         tzname = rffi.charp2str(tzname_ptr[0]), rffi.charp2str(tzname_ptr[1])

    if _POSIX:
        YEAR = (365 * 24 + 6) * 3600

        t = (((c_time(lltype.nullptr(rffi.TIME_TP.TO))) / YEAR) * YEAR)
        # we cannot have reference to stack variable, put it on the heap
        t_ref = lltype.malloc(rffi.TIME_TP.TO, 1, flavor='raw')
        t_ref[0] = t
        p = c_localtime(t_ref)
        janzone = -p.c_tm_gmtoff
        tm_zone = rffi.charp2str(p.c_tm_zone)
        janname = ["   ", tm_zone][bool(tm_zone)]
        tt = t + YEAR / 2
        t_ref[0] = tt
        p = c_localtime(t_ref)
        lltype.free(t_ref, flavor='raw')
        tm_zone = rffi.charp2str(p.c_tm_zone)
        julyzone = -p.c_tm_gmtoff
        julyname = ["   ", tm_zone][bool(tm_zone)]

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

    _set_module_object(space, "timezone", space.wrap(timezone))
    _set_module_object(space, 'daylight', space.wrap(daylight))
    tzname_w = [space.wrap(tzname[0]), space.wrap(tzname[1])]
    _set_module_object(space, 'tzname', space.newtuple(tzname_w))
    _set_module_object(space, 'altzone', space.wrap(altzone))

def _get_error_msg():
    errno = rposix.get_errno()
    return os.strerror(errno)

if sys.platform != 'win32':
    @unwrap_spec(secs=float)
    def sleep(space, secs):
        pytime.sleep(secs)
else:
    from pypy.rlib import rwin32
    from errno import EINTR
    def _simple_sleep(space, secs, interruptible):
        if secs == 0.0 or not interruptible:
            pytime.sleep(secs)
        else:
            millisecs = int(secs * 1000)
            interrupt_event = space.fromcache(State).get_interrupt_event()
            rwin32.ResetEvent(interrupt_event)
            rc = rwin32.WaitForSingleObject(interrupt_event, millisecs)
            if rc == rwin32.WAIT_OBJECT_0:
                # Yield to make sure real Python signal handler
                # called.
                pytime.sleep(0.001)
                raise wrap_oserror(space,
                                   OSError(EINTR, "sleep() interrupted"))
    @unwrap_spec(secs=float)
    def sleep(space, secs):
        # as decreed by Guido, only the main thread can be
        # interrupted.
        main_thread = space.fromcache(State).main_thread
        interruptible = (main_thread == thread.get_ident())
        MAX = sys.maxint / 1000.0 # > 24 days
        while secs > MAX:
            _simple_sleep(space, MAX, interruptible)
            secs -= MAX
        _simple_sleep(space, secs, interruptible)

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
        seconds = pytime.time()
    else:
        seconds = space.float_w(w_seconds)
    try:
        ovfcheck_float_to_int(seconds)
    except OverflowError:
        raise OperationError(space.w_ValueError,
                             space.wrap("time argument too large"))
    return rffi.r_time_t(seconds)

def _tm_to_tuple(space, t):
    time_tuple = [
        space.wrap(rffi.getintfield(t, 'c_tm_year') + 1900),
        space.wrap(rffi.getintfield(t, 'c_tm_mon') + 1), # want january == 1
        space.wrap(rffi.getintfield(t, 'c_tm_mday')),
        space.wrap(rffi.getintfield(t, 'c_tm_hour')),
        space.wrap(rffi.getintfield(t, 'c_tm_min')),
        space.wrap(rffi.getintfield(t, 'c_tm_sec')),
        space.wrap((rffi.getintfield(t, 'c_tm_wday') + 6) % 7), # want monday == 0
        space.wrap(rffi.getintfield(t, 'c_tm_yday') + 1), # want january, 1 == 1
        space.wrap(rffi.getintfield(t, 'c_tm_isdst'))]

    w_struct_time = _get_module_object(space, 'struct_time')
    w_time_tuple = space.newtuple(time_tuple)
    return space.call_function(w_struct_time, w_time_tuple)

def _gettmarg(space, w_tup, allowNone=True):
    if allowNone and space.is_w(w_tup, space.w_None):
        # default to the current local time
        tt = rffi.r_time_t(pytime.time())
        t_ref = lltype.malloc(rffi.TIME_TP.TO, 1, flavor='raw')
        t_ref[0] = tt
        pbuf = c_localtime(t_ref)
        lltype.free(t_ref, flavor='raw')
        if not pbuf:
            raise OperationError(space.w_ValueError,
                space.wrap(_get_error_msg()))
        return pbuf

    tup_w = space.fixedview(w_tup)
    if len(tup_w) != 9:
        raise operationerrfmt(space.w_TypeError,
                              "argument must be sequence of "
                              "length 9, not %d", len(tup_w))

    y = space.int_w(tup_w[0])
    tm_mon = space.int_w(tup_w[1])
    if tm_mon == 0:
        tm_mon = 1
    tm_mday = space.int_w(tup_w[2])
    if tm_mday == 0:
        tm_mday = 1
    tm_yday = space.int_w(tup_w[7])
    if tm_yday == 0:
        tm_yday = 1
    rffi.setintfield(glob_buf, 'c_tm_mon', tm_mon)
    rffi.setintfield(glob_buf, 'c_tm_mday', tm_mday)
    rffi.setintfield(glob_buf, 'c_tm_hour', space.int_w(tup_w[3]))
    rffi.setintfield(glob_buf, 'c_tm_min', space.int_w(tup_w[4]))
    rffi.setintfield(glob_buf, 'c_tm_sec', space.int_w(tup_w[5]))
    rffi.setintfield(glob_buf, 'c_tm_wday', space.int_w(tup_w[6]))
    rffi.setintfield(glob_buf, 'c_tm_yday', tm_yday)
    rffi.setintfield(glob_buf, 'c_tm_isdst', space.int_w(tup_w[8]))
    if _POSIX:
        # actually never happens, but makes annotator happy
        glob_buf.c_tm_zone = lltype.nullptr(rffi.CCHARP.TO)
        rffi.setintfield(glob_buf, 'c_tm_gmtoff', 0)

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

    if rffi.getintfield(glob_buf, 'c_tm_wday') < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("day of week out of range"))

    rffi.setintfield(glob_buf, 'c_tm_year', y - 1900)
    rffi.setintfield(glob_buf, 'c_tm_mon',
                     rffi.getintfield(glob_buf, 'c_tm_mon') - 1)
    rffi.setintfield(glob_buf, 'c_tm_wday',
                     (rffi.getintfield(glob_buf, 'c_tm_wday') + 1) % 7)
    rffi.setintfield(glob_buf, 'c_tm_yday',
                     rffi.getintfield(glob_buf, 'c_tm_yday') - 1)

    return glob_buf

def time(space):
    """time() -> floating point number

    Return the current time in seconds since the Epoch.
    Fractions of a second may be present if the system clock provides them."""

    secs = pytime.time()
    return space.wrap(secs)

if _WIN:
    class PCCache:
        pass
    pccache = PCCache()
    pccache.divisor = 0.0
    pccache.ctrStart = 0

def clock(space):
    """clock() -> floating point number

    Return the CPU time or real time since the start of the process or since
    the first call to clock().  This has as much precision as the system
    records."""

    return space.wrap(pytime.clock())

def ctime(space, w_seconds=None):
    """ctime([seconds]) -> string

    Convert a time in seconds since the Epoch to a string in local time.
    This is equivalent to asctime(localtime(seconds)). When the time tuple is
    not present, current time as returned by localtime() is used."""

    seconds = _get_inttime(space, w_seconds)

    t_ref = lltype.malloc(rffi.TIME_TP.TO, 1, flavor='raw')
    t_ref[0] = seconds
    p = c_ctime(t_ref)
    lltype.free(t_ref, flavor='raw')
    if not p:
        raise OperationError(space.w_ValueError,
            space.wrap("unconvertible time"))

    return space.wrap(rffi.charp2str(p)[:-1]) # get rid of new line

# by now w_tup is an optional argument (and not *args)
# because of the ext. compiler bugs in handling such arguments (*args, **kwds)
def asctime(space, w_tup=None):
    """asctime([tuple]) -> string

    Convert a time tuple to a string, e.g. 'Sat Jun 06 16:26:11 1998'.
    When the time tuple is not present, current time as returned by localtime()
    is used."""
    buf_value = _gettmarg(space, w_tup)
    p = c_asctime(buf_value)
    if not p:
        raise OperationError(space.w_ValueError,
            space.wrap("unconvertible time"))

    return space.wrap(rffi.charp2str(p)[:-1]) # get rid of new line

def gmtime(space, w_seconds=None):
    """gmtime([seconds]) -> (tm_year, tm_mon, tm_day, tm_hour, tm_min,
                          tm_sec, tm_wday, tm_yday, tm_isdst)

    Convert seconds since the Epoch to a time tuple expressing UTC (a.k.a.
    GMT).  When 'seconds' is not passed in, convert the current time instead.
    """

    # rpython does not support that a variable has two incompatible builtins
    # as value so we have to duplicate the code. NOT GOOD! see localtime() too
    seconds = _get_inttime(space, w_seconds)
    t_ref = lltype.malloc(rffi.TIME_TP.TO, 1, flavor='raw')
    t_ref[0] = seconds
    p = c_gmtime(t_ref)
    lltype.free(t_ref, flavor='raw')

    if not p:
        raise OperationError(space.w_ValueError, space.wrap(_get_error_msg()))
    return _tm_to_tuple(space, p)

def localtime(space, w_seconds=None):
    """localtime([seconds]) -> (tm_year, tm_mon, tm_day, tm_hour, tm_min,
                             tm_sec, tm_wday, tm_yday, tm_isdst)

    Convert seconds since the Epoch to a time tuple expressing local time.
    When 'seconds' is not passed in, convert the current time instead."""

    seconds = _get_inttime(space, w_seconds)
    t_ref = lltype.malloc(rffi.TIME_TP.TO, 1, flavor='raw')
    t_ref[0] = seconds
    p = c_localtime(t_ref)
    lltype.free(t_ref, flavor='raw')

    if not p:
        raise OperationError(space.w_ValueError, space.wrap(_get_error_msg()))
    return _tm_to_tuple(space, p)

def mktime(space, w_tup):
    """mktime(tuple) -> floating point number

    Convert a time tuple in local time to seconds since the Epoch."""

    buf = _gettmarg(space, w_tup, allowNone=False)
    tt = c_mktime(buf)
    if tt == -1:
        raise OperationError(space.w_OverflowError,
            space.wrap("mktime argument out of range"))

    return space.wrap(float(tt))

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

        c_tzset()

        # reset timezone, altzone, daylight and tzname
        _init_timezone(space)

@unwrap_spec(format=str)
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
    if rffi.getintfield(buf_value, 'c_tm_mon') < 0 or rffi.getintfield(buf_value, 'c_tm_mon') > 11:
        raise OperationError(space.w_ValueError,
                             space.wrap("month out of range"))
    if rffi.getintfield(buf_value, 'c_tm_mday') < 1 or rffi.getintfield(buf_value, 'c_tm_mday') > 31:
        raise OperationError(space.w_ValueError,
                             space.wrap("day of month out of range"))
    if rffi.getintfield(buf_value, 'c_tm_hour') < 0 or rffi.getintfield(buf_value, 'c_tm_hour') > 23:
        raise OperationError(space.w_ValueError,
                             space.wrap("hour out of range"))
    if rffi.getintfield(buf_value, 'c_tm_min') < 0 or rffi.getintfield(buf_value, 'c_tm_min') > 59:
        raise OperationError(space.w_ValueError,
                             space.wrap("minute out of range"))
    if rffi.getintfield(buf_value, 'c_tm_sec') < 0 or rffi.getintfield(buf_value, 'c_tm_sec') > 61:
        raise OperationError(space.w_ValueError,
                             space.wrap("seconds out of range"))
    if rffi.getintfield(buf_value, 'c_tm_yday') < 0 or rffi.getintfield(buf_value, 'c_tm_yday') > 365:
        raise OperationError(space.w_ValueError,
                             space.wrap("day of year out of range"))
    if rffi.getintfield(buf_value, 'c_tm_isdst') < -1 or rffi.getintfield(buf_value, 'c_tm_isdst') > 1:
        raise OperationError(space.w_ValueError,
                             space.wrap("daylight savings flag out of range"))

    if _WIN:
        # check that the format string contains only valid directives
        length = len(format)
        i = 0
        while i < length:
            if format[i] == '%':
                i += 1
                if i < length and format[i] == '#':
                    # not documented by python
                    i += 1
                if i >= length or format[i] not in "aAbBcdfHIjmMpSUwWxXyYzZ%":
                    raise OperationError(space.w_ValueError,
                                         space.wrap("invalid format string"))
            i += 1

    i = 1024
    while True:
        outbuf = lltype.malloc(rffi.CCHARP.TO, i, flavor='raw')
        try:
            buflen = c_strftime(outbuf, i, format, buf_value)
            if buflen > 0 or i >= 256 * len(format):
                # if the buffer is 256 times as long as the format,
                # it's probably not failing for lack of room!
                # More likely, the format yields an empty result,
                # e.g. an empty format, or %Z when the timezone
                # is unknown.
                result = rffi.charp2strn(outbuf, buflen)
                return space.wrap(result)
        finally:
            lltype.free(outbuf, flavor='raw')
        i += i
