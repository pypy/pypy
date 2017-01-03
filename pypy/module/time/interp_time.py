from rpython.rtyper.tool import rffi_platform as platform
from rpython.rtyper.lltypesystem import rffi
from pypy.interpreter.error import (OperationError, oefmt,
        strerror as _strerror, exception_from_saved_errno)
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter import timeutils
from pypy.interpreter.unicodehelper import decode_utf8, encode_utf8
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.rarithmetic import intmask, r_ulonglong, r_longfloat, widen
from rpython.rlib.rtime import (GETTIMEOFDAY_NO_TZ, TIMEVAL,
                                HAVE_GETTIMEOFDAY, HAVE_FTIME)
from rpython.rlib import rposix, rtime
from rpython.translator.tool.cbuild import ExternalCompilationInfo
import math
import os
import sys
import time as pytime

if HAVE_FTIME:
    from rpython.rlib.rtime import TIMEB, c_ftime

_POSIX = os.name == "posix"
_WIN = os.name == "nt"
_MACOSX = sys.platform == "darwin"
_CYGWIN = sys.platform == "cygwin"

_time_zones = []
if _CYGWIN:
    _time_zones = ["GMT-12", "GMT-11", "GMT-10", "GMT-9", "GMT-8", "GMT-7",
                   "GMT-6", "GMT-5", "GMT-4", "GMT-3", "GMT-2", "GMT-1",
                   "GMT",  "GMT+1", "GMT+2", "GMT+3", "GMT+4", "GMT+5",
                   "GMT+6",  "GMT+7", "GMT+8", "GMT+9", "GMT+10", "GMT+11",
                   "GMT+12",  "GMT+13", "GMT+14"]

if _WIN:
    # Interruptible sleeps on Windows:
    # We install a specific Console Ctrl Handler which sets an 'event'.
    # time.sleep() will actually call WaitForSingleObject with the desired
    # timeout.  On Ctrl-C, the signal handler is called, the event is set,
    # and the wait function exits.
    from rpython.rlib import rwin32
    from pypy.interpreter.error import wrap_windowserror, wrap_oserror
    from rpython.rlib import rthread as thread

    eci = ExternalCompilationInfo(
        includes = ['windows.h'],
        post_include_bits = [
            "RPY_EXTERN\n"
            "BOOL pypy_timemodule_setCtrlHandler(HANDLE event);\n"
            "RPY_EXTERN ULONGLONG pypy_GetTickCount64(FARPROC address);"
        ],
        separate_module_sources=['''
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

            ULONGLONG pypy_GetTickCount64(FARPROC address) {
                ULONGLONG (WINAPI *func)();
                *(FARPROC*)&func = address;
                return func();
            }

        '''],
        )
    _setCtrlHandlerRoutine = rffi.llexternal(
        'pypy_timemodule_setCtrlHandler',
        [rwin32.HANDLE], rwin32.BOOL,
        compilation_info=eci,
        save_err=rffi.RFFI_SAVE_LASTERROR)

    pypy_GetTickCount64 = rffi.llexternal(
        'pypy_GetTickCount64',
        [rffi.VOIDP],
        rffi.ULONGLONG, compilation_info=eci)

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
            except WindowsError as e:
                raise wrap_windowserror(space, e)
            if not _setCtrlHandlerRoutine(globalState.interrupt_event):
                raise wrap_windowserror(space,
                    rwin32.lastSavedWindowsError("SetConsoleCtrlHandler"))

    globalState = GlobalState()

    class State:
        def __init__(self, space):
            self.main_thread = 0

        def _cleanup_(self):
            self.main_thread = 0
            globalState.init()

        def startup(self, space):
            self.main_thread = thread.get_ident()
            globalState.startup(space)

        def get_interrupt_event(self):
            return globalState.interrupt_event

    class TimeState(object):
        GetTickCount64_handle = lltype.nullptr(rffi.VOIDP.TO)
        def __init__(self):
            self.n_overflow = 0
            self.last_ticks = 0
            self.divisor = 0.0
            self.counter_start = 0

        def check_GetTickCount64(self, *args):
            if (self.GetTickCount64_handle !=
                lltype.nullptr(rffi.VOIDP.TO)):
                return True
            from rpython.rlib.rdynload import GetModuleHandle, dlsym
            hKernel32 = GetModuleHandle("KERNEL32")
            try:
                GetTickCount64_handle = dlsym(hKernel32, 'GetTickCount64')
            except KeyError:
                return False
            self.GetTickCount64_handle = GetTickCount64_handle
            return True

        def GetTickCount64(self, *args):
            assert (self.GetTickCount64_handle !=
                    lltype.nullptr(rffi.VOIDP.TO))
            return pypy_GetTickCount64(
                self.GetTickCount64_handle, *args)

    time_state = TimeState()

_includes = ["time.h"]
if _POSIX:
    _includes.append('sys/time.h')
if _MACOSX:
    _includes.append('mach/mach_time.h')

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=_includes,
        libraries=rtime.libraries
    )
    CLOCKS_PER_SEC = platform.ConstantInteger("CLOCKS_PER_SEC")
    has_gettimeofday = platform.Has('gettimeofday')

HAS_TM_ZONE = False

if _POSIX:
    calling_conv = 'c'
    CConfig.timeval = platform.Struct("struct timeval",
                                      [("tv_sec", rffi.INT),
                                       ("tv_usec", rffi.INT)])
    if _CYGWIN:
        CConfig.tm = platform.Struct("struct tm", [("tm_sec", rffi.INT),
            ("tm_min", rffi.INT), ("tm_hour", rffi.INT), ("tm_mday", rffi.INT),
            ("tm_mon", rffi.INT), ("tm_year", rffi.INT), ("tm_wday", rffi.INT),
            ("tm_yday", rffi.INT), ("tm_isdst", rffi.INT)])
    else:
        CConfig.tm = platform.Struct("struct tm", [("tm_sec", rffi.INT),
            ("tm_min", rffi.INT), ("tm_hour", rffi.INT), ("tm_mday", rffi.INT),
            ("tm_mon", rffi.INT), ("tm_year", rffi.INT), ("tm_wday", rffi.INT),
            ("tm_yday", rffi.INT), ("tm_isdst", rffi.INT), ("tm_gmtoff", rffi.LONG),
            ("tm_zone", rffi.CCHARP)])

        HAS_TM_ZONE = True

elif _WIN:
    calling_conv = 'win'
    CConfig.tm = platform.Struct("struct tm", [("tm_sec", rffi.INT),
        ("tm_min", rffi.INT), ("tm_hour", rffi.INT), ("tm_mday", rffi.INT),
        ("tm_mon", rffi.INT), ("tm_year", rffi.INT), ("tm_wday", rffi.INT),
        ("tm_yday", rffi.INT), ("tm_isdst", rffi.INT)])

if _MACOSX:
    CConfig.TIMEBASE_INFO = platform.Struct("struct mach_timebase_info", [
        ("numer", rffi.UINT),
        ("denom", rffi.UINT),
    ])

# XXX: optionally support the 2 additional tz fields
_STRUCT_TM_ITEMS = 9
if HAS_TM_ZONE:
    _STRUCT_TM_ITEMS = 11

class cConfig:
    pass

for k, v in platform.configure(CConfig).items():
    setattr(cConfig, k, v)
cConfig.tm.__name__ = "_tm"

def external(name, args, result, eci=CConfig._compilation_info_, **kwds):
    if _WIN and rffi.sizeof(rffi.TIME_T) == 8:
        # Recent Microsoft compilers use 64bit time_t and
        # the corresponding functions are named differently
        if (rffi.TIME_T in args or rffi.TIME_TP in args
            or result in (rffi.TIME_T, rffi.TIME_TP)):
            name = '_' + name + '64'
    return rffi.llexternal(name, args, result,
                           compilation_info=eci,
                           calling_conv=calling_conv,
                           releasegil=False,
                           **kwds)

if _POSIX:
    cConfig.timeval.__name__ = "_timeval"
    timeval = cConfig.timeval

CLOCKS_PER_SEC = cConfig.CLOCKS_PER_SEC
HAS_CLOCK_GETTIME = rtime.HAS_CLOCK_GETTIME
HAS_CLOCK_HIGHRES = rtime.CLOCK_HIGHRES is not None
HAS_CLOCK_MONOTONIC = rtime.CLOCK_MONOTONIC is not None
HAS_MONOTONIC = (_WIN or _MACOSX or
                 (HAS_CLOCK_GETTIME and (HAS_CLOCK_HIGHRES or HAS_CLOCK_MONOTONIC)))
tm = cConfig.tm
glob_buf = lltype.malloc(tm, flavor='raw', zero=True, immortal=True)

if _WIN:
    _GetSystemTimeAsFileTime = rwin32.winexternal('GetSystemTimeAsFileTime',
                                                  [lltype.Ptr(rwin32.FILETIME)],
                                                  lltype.Void)
    LPDWORD = rwin32.LPDWORD
    _GetSystemTimeAdjustment = rwin32.winexternal(
                                            'GetSystemTimeAdjustment',
                                            [LPDWORD, LPDWORD, rwin32.LPBOOL], 
                                            rffi.INT)
    def gettimeofday(space, w_info=None):
        with lltype.scoped_alloc(rwin32.FILETIME) as system_time:
            _GetSystemTimeAsFileTime(system_time)
            quad_part = (system_time.c_dwLowDateTime |
                         (r_ulonglong(system_time.c_dwHighDateTime) << 32))
            # 11,644,473,600,000,000: number of microseconds between
            # the 1st january 1601 and the 1st january 1970 (369 years + 80 leap
            # days).

            # We can't use that big number when translating for
            # 32-bit system (which windows always is currently)
            # XXX: Need to come up with a better solution
            offset = (r_ulonglong(16384) * r_ulonglong(27) * r_ulonglong(390625)
                     * r_ulonglong(79) * r_ulonglong(853))
            microseconds = quad_part / 10 - offset
            tv_sec = microseconds / 1000000
            tv_usec = microseconds % 1000000
            if w_info:
                with lltype.scoped_alloc(LPDWORD.TO, 1) as time_adjustment, \
                     lltype.scoped_alloc(LPDWORD.TO, 1) as time_increment, \
                     lltype.scoped_alloc(rwin32.LPBOOL.TO, 1) as is_time_adjustment_disabled:
                    _GetSystemTimeAdjustment(time_adjustment, time_increment,
                                             is_time_adjustment_disabled)
                    
                    _setinfo(space, w_info, "GetSystemTimeAsFileTime()",
                             time_increment[0] * 1e-7, False, True)
            return space.wrap(tv_sec + tv_usec * 1e-6)
else:
    if HAVE_GETTIMEOFDAY:
        if GETTIMEOFDAY_NO_TZ:
            c_gettimeofday = external('gettimeofday',
                                      [lltype.Ptr(TIMEVAL)], rffi.INT)
        else:
            c_gettimeofday = external('gettimeofday',
                                      [lltype.Ptr(TIMEVAL), rffi.VOIDP], rffi.INT)
    def gettimeofday(space, w_info=None):
        if HAVE_GETTIMEOFDAY:
            with lltype.scoped_alloc(TIMEVAL) as timeval:
                if GETTIMEOFDAY_NO_TZ:
                    errcode = c_gettimeofday(timeval)
                else:
                    void = lltype.nullptr(rffi.VOIDP.TO)
                    errcode = c_gettimeofday(timeval, void)
                if rffi.cast(rffi.LONG, errcode) == 0:
                    if w_info is not None:
                        _setinfo(space, w_info, "gettimeofday()", 1e-6, False, True)
                    return space.wrap(
                        widen(timeval.c_tv_sec) +
                        widen(timeval.c_tv_usec) * 1e-6)
        if HAVE_FTIME:
            with lltype.scoped_alloc(TIMEB) as t:
                c_ftime(t)
                result = (widen(t.c_time) +
                          widen(t.c_millitm) * 0.001)
                if w_info is not None:
                    _setinfo(space, w_info, "ftime()", 1e-3,
                             False, True) 
            return space.wrap(result)
        else:
            if w_info:
                _setinfo(space, w_info, "time()", 1.0, False, True)
            return space.wrap(c_time(lltype.nullptr(rffi.TIME_TP.TO)))

TM_P = lltype.Ptr(tm)
c_time = external('time', [rffi.TIME_TP], rffi.TIME_T)
c_gmtime = external('gmtime', [rffi.TIME_TP], TM_P,
                    save_err=rffi.RFFI_SAVE_ERRNO)
c_mktime = external('mktime', [TM_P], rffi.TIME_T)
c_localtime = external('localtime', [rffi.TIME_TP], TM_P,
                       save_err=rffi.RFFI_SAVE_ERRNO)
if HAS_CLOCK_GETTIME:
    from rpython.rlib.rtime import TIMESPEC, c_clock_gettime
    from rpython.rlib.rtime import c_clock_settime, c_clock_getres
if _POSIX:
    c_tzset = external('tzset', [], lltype.Void)
if _WIN:
    win_eci = ExternalCompilationInfo(
        includes = ["time.h"],
        post_include_bits = ["RPY_EXTERN "
                             "long pypy_get_timezone();\n"
                             "RPY_EXTERN "
                             "int pypy_get_daylight();\n"
                             "RPY_EXTERN "
                             "char** pypy_get_tzname();\n"
                             "RPY_EXTERN "
                             "void pypy__tzset();"],
        separate_module_sources = ["""
        long pypy_get_timezone() { return timezone; }
        int pypy_get_daylight() { return daylight; }
        char** pypy_get_tzname() { return tzname; }
        void pypy__tzset() { return _tzset(); }
        """])
    # Ensure sure that we use _tzset() and timezone from the same C Runtime.
    c_tzset = external('pypy__tzset', [], lltype.Void, win_eci)
    c_get_timezone = external('pypy_get_timezone', [], rffi.LONG, win_eci)
    c_get_daylight = external('pypy_get_daylight', [], rffi.INT, win_eci)
    c_get_tzname = external('pypy_get_tzname', [], rffi.CCHARPP, win_eci)

c_strftime = external('strftime', [rffi.CCHARP, rffi.SIZE_T, rffi.CCHARP, TM_P],
                      rffi.SIZE_T)

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
        if _CYGWIN:
            YEAR = (365 * 24 + 6) * 3600

            # about January 11th
            t = (((c_time(lltype.nullptr(rffi.TIME_TP.TO))) / YEAR) * YEAR + 10 * 24 * 3600)
            # we cannot have reference to stack variable, put it on the heap
            t_ref = lltype.malloc(rffi.TIME_TP.TO, 1, flavor='raw')
            t_ref[0] = rffi.cast(rffi.TIME_T, t)
            p = c_localtime(t_ref)
            q = c_gmtime(t_ref)
            janzone = (p.c_tm_hour + 24 * p.c_tm_mday) - (q.c_tm_hour + 24 * q.c_tm_mday)
            if janzone < -12:
                janname = "   "
            elif janzone > 14:
                janname = "   "
            else:
                janname = _time_zones[janzone - 12]
            janzone = janzone * 3600
            # about July 11th
            tt = t + YEAR / 2
            t_ref[0] = rffi.cast(rffi.TIME_T, tt)
            p = c_localtime(t_ref)
            q = c_gmtime(t_ref)
            julyzone = (p.c_tm_hour + 24 * p.c_tm_mday) - (q.c_tm_hour + 24 * q.c_tm_mday)
            if julyzone < -12:
                julyname = "   "
            elif julyzone > 14:
                julyname = "   "
            else:
                julyname = _time_zones[julyzone - 12]
            julyzone = julyzone * 3600
            lltype.free(t_ref, flavor='raw')

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

        else:
            YEAR = (365 * 24 + 6) * 3600

            t = (((c_time(lltype.nullptr(rffi.TIME_TP.TO))) / YEAR) * YEAR)
            # we cannot have reference to stack variable, put it on the heap
            t_ref = lltype.malloc(rffi.TIME_TP.TO, 1, flavor='raw')
            t_ref[0] = rffi.cast(rffi.TIME_T, t)
            p = c_localtime(t_ref)
            janzone = -p.c_tm_gmtoff
            tm_zone = rffi.charp2str(p.c_tm_zone)
            janname = ["   ", tm_zone][bool(tm_zone)]
            tt = t + YEAR / 2
            t_ref[0] = rffi.cast(rffi.TIME_T, tt)
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
    errno = rposix.get_saved_errno()
    return _strerror(errno)

if sys.platform != 'win32':
    from errno import EINTR
    from rpython.rlib.rtime import c_select

    @unwrap_spec(secs=float)
    def sleep(space, secs):
        if secs < 0:
            raise oefmt(space.w_ValueError,
                        "sleep length must be non-negative")
        end_time = timeutils.monotonic(space) + secs
        while True:
            void = lltype.nullptr(rffi.VOIDP.TO)
            with lltype.scoped_alloc(TIMEVAL) as t:
                frac = math.fmod(secs, 1.0)
                rffi.setintfield(t, 'c_tv_sec', int(secs))
                rffi.setintfield(t, 'c_tv_usec', int(frac*1000000.0))

                res = rffi.cast(rffi.LONG, c_select(0, void, void, void, t))
            if res == 0:
                break    # normal path
            if rposix.get_saved_errno() != EINTR:
                raise exception_from_saved_errno(space, space.w_OSError)
            secs = end_time - timeutils.monotonic(space)   # retry
            if secs <= 0.0:
                break

else:
    from rpython.rlib import rwin32
    from errno import EINTR
    def _simple_sleep(space, secs, interruptible):
        if secs == 0.0 or not interruptible:
            rtime.sleep(secs)
        else:
            millisecs = int(secs * 1000)
            interrupt_event = space.fromcache(State).get_interrupt_event()
            rwin32.ResetEvent(interrupt_event)
            rc = rwin32.WaitForSingleObject(interrupt_event, millisecs)
            if rc == rwin32.WAIT_OBJECT_0:
                # Yield to make sure real Python signal handler
                # called.
                rtime.sleep(0.001)
                raise wrap_oserror(space,
                                   OSError(EINTR, "sleep() interrupted"))
    @unwrap_spec(secs=float)
    def sleep(space, secs):
        XXX   # review for EINTR / PEP475
        if secs < 0:
            raise oefmt(space.w_ValueError,
                        "sleep length must be non-negative")
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
    if space.is_none(w_seconds):
        seconds = pytime.time()
    else:
        seconds = space.float_w(w_seconds)
    #
    t = rffi.cast(rffi.TIME_T, seconds)
    #
    # Logic from CPython: How much info did we lose?  We assume that
    # time_t is an integral type.  If we lost a second or more, the
    # input doesn't fit in a time_t; call it an error.
    diff = seconds - rffi.cast(lltype.Float, t)
    if diff <= -1.0 or diff >= 1.0:
        raise oefmt(space.w_OverflowError,
                    "timestamp out of range for platform time_t")
    return t

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

    if HAS_TM_ZONE:
        # CPython calls PyUnicode_DecodeLocale here should we do the same?
        tm_zone = decode_utf8(space, rffi.charp2str(t.c_tm_zone), allow_surrogates=True)
        time_tuple.append(space.newunicode(tm_zone))
        time_tuple.append(space.wrap(rffi.getintfield(t, 'c_tm_gmtoff')))
    w_struct_time = _get_module_object(space, 'struct_time')
    w_time_tuple = space.newtuple(time_tuple)
    w_obj = space.call_function(w_struct_time, w_time_tuple)
    return w_obj

def _gettmarg(space, w_tup, allowNone=True):
    if space.is_none(w_tup):
        if not allowNone:
            raise oefmt(space.w_TypeError, "tuple expected")
        # default to the current local time
        tt = rffi.cast(rffi.TIME_T, pytime.time())
        t_ref = lltype.malloc(rffi.TIME_TP.TO, 1, flavor='raw')
        t_ref[0] = tt
        pbuf = c_localtime(t_ref)
        rffi.setintfield(pbuf, "c_tm_year",
                         rffi.getintfield(pbuf, "c_tm_year") + 1900)
        lltype.free(t_ref, flavor='raw')
        if not pbuf:
            raise OperationError(space.w_ValueError,
                                 space.wrap(_get_error_msg()))
        return pbuf

    tup_w = space.fixedview(w_tup)
    if len(tup_w) < 9:
        raise oefmt(space.w_TypeError,
                    "argument must be sequence of at least length 9, not %d",
                    len(tup_w))

    y = space.c_int_w(tup_w[0])
    tm_mon = space.c_int_w(tup_w[1])
    if tm_mon == 0:
        tm_mon = 1
    tm_mday = space.c_int_w(tup_w[2])
    if tm_mday == 0:
        tm_mday = 1
    tm_yday = space.c_int_w(tup_w[7])
    if tm_yday == 0:
        tm_yday = 1
    rffi.setintfield(glob_buf, 'c_tm_mon', tm_mon)
    rffi.setintfield(glob_buf, 'c_tm_mday', tm_mday)
    rffi.setintfield(glob_buf, 'c_tm_hour', space.c_int_w(tup_w[3]))
    rffi.setintfield(glob_buf, 'c_tm_min', space.c_int_w(tup_w[4]))
    rffi.setintfield(glob_buf, 'c_tm_sec', space.c_int_w(tup_w[5]))
    rffi.setintfield(glob_buf, 'c_tm_wday', space.c_int_w(tup_w[6]))
    rffi.setintfield(glob_buf, 'c_tm_yday', tm_yday)
    rffi.setintfield(glob_buf, 'c_tm_isdst', space.c_int_w(tup_w[8]))
    if HAS_TM_ZONE:
        #tm_zone = encode_utf8(space, space.unicode_w(tup_w[9]), allow_surrogates=True)
        #glob_buf.c_tm_zone = rffi.str2charp(tm_zone)
        # TODO using str2charp allocates an object that is never freed
        # find a solution for this memory leak
        glob_buf.c_tm_zone = lltype.nullptr(rffi.CCHARP.TO)
        rffi.setintfield(glob_buf, 'c_tm_gmtoff', space.c_int_w(tup_w[10]))
    else:
        glob_buf.c_tm_zone = lltype.nullptr(rffi.CCHARP.TO)
        rffi.setintfield(glob_buf, 'c_tm_gmtoff', 0)

    # tm_wday does not need checking of its upper-bound since taking "%
    #  7" in _gettmarg() automatically restricts the range.
    if rffi.getintfield(glob_buf, 'c_tm_wday') < -1:
        raise oefmt(space.w_ValueError, "day of week out of range")

    rffi.setintfield(glob_buf, 'c_tm_year', y)
    rffi.setintfield(glob_buf, 'c_tm_mon',
                     rffi.getintfield(glob_buf, 'c_tm_mon') - 1)
    rffi.setintfield(glob_buf, 'c_tm_wday',
                     (rffi.getintfield(glob_buf, 'c_tm_wday') + 1) % 7)
    rffi.setintfield(glob_buf, 'c_tm_yday',
                     rffi.getintfield(glob_buf, 'c_tm_yday') - 1)

    return glob_buf

def _checktm(space, t_ref):
    """Checks added to make sure strftime() and asctime() do not crash
    Python by indexing blindly into some array for a textual
    representation by some bad index (fixes bug #897625).  No check for
    year or wday since handled in _gettmarg()."""
    if not 0 <= rffi.getintfield(t_ref, 'c_tm_mon') <= 11:
        raise oefmt(space.w_ValueError, "month out of range")
    if not 1 <= rffi.getintfield(t_ref, 'c_tm_mday') <= 31:
        raise oefmt(space.w_ValueError, "day of month out of range")
    if not 0 <= rffi.getintfield(t_ref, 'c_tm_hour') <= 23:
        raise oefmt(space.w_ValueError, "hour out of range")
    if not 0 <= rffi.getintfield(t_ref, 'c_tm_min') <= 59:
        raise oefmt(space.w_ValueError, "minute out of range")
    if not 0 <= rffi.getintfield(t_ref, 'c_tm_sec') <= 61:
        raise oefmt(space.w_ValueError, "seconds out of range")
    # tm_wday does not need checking: "% 7" in _gettmarg() automatically
    # restricts the range
    if not 0 <= rffi.getintfield(t_ref, 'c_tm_yday') <= 365:
        raise oefmt(space.w_ValueError, "day of year out of range")

def time(space, w_info=None):
    """time() -> floating point number

    Return the current time in seconds since the Epoch.
    Fractions of a second may be present if the system clock provides them."""
    if HAS_CLOCK_GETTIME:
        with lltype.scoped_alloc(TIMESPEC) as timespec:
            ret = c_clock_gettime(rtime.CLOCK_REALTIME, timespec)
            if ret == 0:
                if w_info is not None:
                    with lltype.scoped_alloc(TIMESPEC) as tsres:
                        ret = c_clock_getres(rtime.CLOCK_REALTIME, tsres)
                        if ret == 0:
                            res = _timespec_to_seconds(tsres)
                        else:
                            res = 1e-9
                        _setinfo(space, w_info, "clock_gettime(CLOCK_REALTIME)",
                                 res, False, True)
                return space.wrap(_timespec_to_seconds(timespec))
    else:
        return gettimeofday(space, w_info)

def ctime(space, w_seconds=None):
    """ctime([seconds]) -> string

    Convert a time in seconds since the Epoch to a string in local time.
    This is equivalent to asctime(localtime(seconds)). When the time tuple is
    not present, current time as returned by localtime() is used."""

    seconds = _get_inttime(space, w_seconds)
    with lltype.scoped_alloc(rffi.TIME_TP.TO, 1) as t_ref:
        t_ref[0] = seconds
        p = c_localtime(t_ref)
    if not p:
        raise oefmt(space.w_OSError, "unconvertible time")
    rffi.setintfield(p, "c_tm_year", rffi.getintfield(p, "c_tm_year") + 1900)
    return _asctime(space, p)

# by now w_tup is an optional argument (and not *args)
# because of the ext. compiler bugs in handling such arguments (*args, **kwds)
def asctime(space, w_tup=None):
    """asctime([tuple]) -> string

    Convert a time tuple to a string, e.g. 'Sat Jun 06 16:26:11 1998'.
    When the time tuple is not present, current time as returned by localtime()
    is used."""
    buf_value = _gettmarg(space, w_tup)
    _checktm(space, buf_value)
    return _asctime(space, buf_value)

_wday_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
_mon_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
              "Oct", "Nov", "Dec"]

def _asctime(space, t_ref):
    # Inspired by Open Group reference implementation available at
    # http://pubs.opengroup.org/onlinepubs/009695399/functions/asctime.html
    w, getif = space.wrap, rffi.getintfield
    args = [w(_wday_names[getif(t_ref, 'c_tm_wday')]),
            w(_mon_names[getif(t_ref, 'c_tm_mon')]),
            w(getif(t_ref, 'c_tm_mday')),
            w(getif(t_ref, 'c_tm_hour')),
            w(getif(t_ref, 'c_tm_min')),
            w(getif(t_ref, 'c_tm_sec')),
            w(getif(t_ref, 'c_tm_year'))]
    return space.mod(w("%.3s %.3s%3d %.2d:%.2d:%.2d %d"),
                     space.newtuple(args))

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
        raise OperationError(space.w_OSError, space.wrap(_get_error_msg()))
    return _tm_to_tuple(space, p)

def mktime(space, w_tup):
    """mktime(tuple) -> floating point number

    Convert a time tuple in local time to seconds since the Epoch."""

    buf = _gettmarg(space, w_tup, allowNone=False)
    rffi.setintfield(buf, "c_tm_wday", -1)
    rffi.setintfield(buf, "c_tm_year", rffi.getintfield(buf, "c_tm_year") - 1900)
    tt = c_mktime(buf)
    # A return value of -1 does not necessarily mean an error, but tm_wday
    # cannot remain set to -1 if mktime succeeds.
    if tt == -1 and rffi.getintfield(buf, "c_tm_wday") == -1:
        raise oefmt(space.w_OverflowError, "mktime argument out of range")

    return space.wrap(float(tt))

if HAS_CLOCK_GETTIME:
    def _timespec_to_seconds(timespec):
        return widen(timespec.c_tv_sec) + widen(timespec.c_tv_nsec) * 1e-9

    @unwrap_spec(clk_id='c_int')
    def clock_gettime(space, clk_id):
        with lltype.scoped_alloc(TIMESPEC) as timespec:
            ret = c_clock_gettime(clk_id, timespec)
            if ret != 0:
                raise exception_from_saved_errno(space, space.w_OSError)
            secs = _timespec_to_seconds(timespec)
        return space.wrap(secs)

    @unwrap_spec(clk_id='c_int', secs=float)
    def clock_settime(space, clk_id, secs):
        with lltype.scoped_alloc(TIMESPEC) as timespec:
            integer_secs = rffi.cast(TIMESPEC.c_tv_sec, secs)
            frac = secs - widen(integer_secs)
            rffi.setintfield(timespec, 'c_tv_sec', integer_secs)
            rffi.setintfield(timespec, 'c_tv_nsec', int(frac * 1e9))
            ret = c_clock_settime(clk_id, timespec)
            if ret != 0:
                raise exception_from_saved_errno(space, space.w_OSError)

    @unwrap_spec(clk_id='c_int')
    def clock_getres(space, clk_id):
        with lltype.scoped_alloc(TIMESPEC) as timespec:
            ret = c_clock_getres(clk_id, timespec)
            if ret != 0:
                raise exception_from_saved_errno(space, space.w_OSError)
            secs = _timespec_to_seconds(timespec)
        return space.wrap(secs)

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
    _checktm(space, buf_value)

    # Normalize tm_isdst just in case someone foolishly implements %Z
    # based on the assumption that tm_isdst falls within the range of
    # [-1, 1]
    if rffi.getintfield(buf_value, 'c_tm_isdst') < -1:
        rffi.setintfield(buf_value, 'c_tm_isdst', -1)
    elif rffi.getintfield(buf_value, 'c_tm_isdst') > 1:
        rffi.setintfield(buf_value, 'c_tm_isdst', 1)
    rffi.setintfield(buf_value, "c_tm_year",
                     rffi.getintfield(buf_value, "c_tm_year") - 1900)

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
                if i >= length or format[i] not in "aAbBcdHIjmMpSUwWxXyYzZ%":
                    raise oefmt(space.w_ValueError, "invalid format string")
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
                result = rffi.charp2strn(outbuf, intmask(buflen))
                return space.wrap(result)
        finally:
            lltype.free(outbuf, flavor='raw')
        i += i

if HAS_MONOTONIC:
    if _WIN:
        _GetTickCount = rwin32.winexternal('GetTickCount', [], rwin32.DWORD)
        def monotonic(space, w_info=None):
            result = 0
            HAS_GETTICKCOUNT64 = time_state.check_GetTickCount64()
            if HAS_GETTICKCOUNT64:
                result = time_state.GetTickCount64() * 1e-3
            else:
                ticks = _GetTickCount()
                if ticks < time_state.last_ticks:
                    time_state.n_overflow += 1
                time_state.last_ticks = ticks
                result = math.ldexp(time_state.n_overflow, 32)
                result = result + ticks
                result = result * 1e-3

            if w_info is not None:
                if HAS_GETTICKCOUNT64:
                    implementation = "GetTickCount64()"
                else:
                    implementation = "GetTickCount()"
                resolution = 1e-7
                with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as time_adjustment, \
                     lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as time_increment, \
                     lltype.scoped_alloc(rwin32.LPBOOL.TO, 1) as is_time_adjustment_disabled:
                    ok = _GetSystemTimeAdjustment(time_adjustment,
                                                  time_increment,
                                                  is_time_adjustment_disabled)
                    if not ok:
                        # Is this right? Cargo culting...
                        raise wrap_windowserror(space,
                            rwin32.lastSavedWindowsError("GetSystemTimeAdjustment"))
                    resolution = resolution * time_increment[0]
                _setinfo(space, w_info, implementation, resolution, True, False)
            return space.wrap(result)

    elif _MACOSX:
        c_mach_timebase_info = external('mach_timebase_info',
                                        [lltype.Ptr(cConfig.TIMEBASE_INFO)],
                                        lltype.Void)
        c_mach_absolute_time = external('mach_absolute_time', [], rffi.ULONGLONG)

        timebase_info = lltype.malloc(cConfig.TIMEBASE_INFO, flavor='raw',
                                      zero=True, immortal=True)

        def monotonic(space, w_info=None):
            if rffi.getintfield(timebase_info, 'c_denom') == 0:
                c_mach_timebase_info(timebase_info)
            time = rffi.cast(lltype.Signed, c_mach_absolute_time())
            numer = rffi.getintfield(timebase_info, 'c_numer')
            denom = rffi.getintfield(timebase_info, 'c_denom')
            nanosecs = time * numer / denom
            if w_info is not None:
                res = (numer / denom) * 1e-9
                _setinfo(space, w_info, "mach_absolute_time()", res, True, False)
            secs = nanosecs / 10**9
            rest = nanosecs % 10**9
            return space.wrap(float(secs) + float(rest) * 1e-9)

    else:
        assert _POSIX
        def monotonic(space, w_info=None):
            if rtime.CLOCK_HIGHRES is not None:
                clk_id = rtime.CLOCK_HIGHRES
                implementation = "clock_gettime(CLOCK_HIGHRES)"
            else:
                clk_id = rtime.CLOCK_MONOTONIC
                implementation = "clock_gettime(CLOCK_MONOTONIC)"
            w_result = clock_gettime(space, clk_id)
            if w_info is not None:
                with lltype.scoped_alloc(TIMESPEC) as tsres:
                    ret = c_clock_getres(clk_id, tsres)
                    if ret == 0:
                        res = _timespec_to_seconds(tsres)
                    else:
                        res = 1e-9
                _setinfo(space, w_info, implementation, res, True, False)
            return w_result

if _WIN:
    # hacking to avoid LARGE_INTEGER which is a union...
    QueryPerformanceCounter = external(
        'QueryPerformanceCounter', [rffi.CArrayPtr(lltype.SignedLongLong)],
         lltype.Void)
    QueryPerformanceCounter = rwin32.winexternal('QueryPerformanceCounter',
                                                 [rffi.CArrayPtr(lltype.SignedLongLong)],
                                                 rwin32.DWORD)
    QueryPerformanceFrequency = rwin32.winexternal(
        'QueryPerformanceFrequency', [rffi.CArrayPtr(lltype.SignedLongLong)], 
        rffi.INT)
    def win_perf_counter(space, w_info=None):
        with lltype.scoped_alloc(rffi.CArray(rffi.lltype.SignedLongLong), 1) as a:
            succeeded = True
            if time_state.divisor == 0.0:
                QueryPerformanceCounter(a)
                time_state.counter_start = a[0]
                succeeded = QueryPerformanceFrequency(a)
                time_state.divisor = float(a[0])
            if succeeded and time_state.divisor != 0.0:
                QueryPerformanceCounter(a)
                diff = a[0] - time_state.counter_start
            else:
                raise ValueError("Failed to generate the result.")
            resolution = 1 / time_state.divisor
            if w_info is not None:
                _setinfo(space, w_info, "QueryPerformanceCounter()", resolution,
                         True, False)
            return space.wrap(float(diff) / time_state.divisor)

    def perf_counter(space, w_info=None):
        try:
            return win_perf_counter(space, w_info=w_info)
        except ValueError:
            if HAS_MONOTONIC:
                try:
                    return monotonic(space, w_info=w_info)
                except Exception:
                    pass
        return time(space, w_info=w_info)
else:
    def perf_counter(space, w_info=None):
        if HAS_MONOTONIC:
            try:
                return monotonic(space, w_info=w_info)
            except Exception:
                pass
        return time(space, w_info=w_info)

if _WIN:
    def process_time(space, w_info=None):
        from rpython.rlib.rposix import GetCurrentProcess, GetProcessTimes
        current_process = GetCurrentProcess()
        with lltype.scoped_alloc(rwin32.FILETIME) as creation_time, \
             lltype.scoped_alloc(rwin32.FILETIME) as exit_time, \
             lltype.scoped_alloc(rwin32.FILETIME) as kernel_time, \
             lltype.scoped_alloc(rwin32.FILETIME) as user_time:
            worked = GetProcessTimes(current_process, creation_time, exit_time,
                                     kernel_time, user_time)
            if not worked:
                raise wrap_windowserror(space,
                    rwin32.lastSavedWindowsError("GetProcessTimes"))
            kernel_time2 = (kernel_time.c_dwLowDateTime |
                            r_ulonglong(kernel_time.c_dwHighDateTime) << 32)
            user_time2 = (user_time.c_dwLowDateTime |
                          r_ulonglong(user_time.c_dwHighDateTime) << 32)
        if w_info is not None:
            _setinfo(space, w_info, "GetProcessTimes()", 1e-7, True, False)
        return space.wrap((float(kernel_time2) + float(user_time2)) * 1e-7)
else:
    have_times = hasattr(rposix, 'c_times')

    def process_time(space, w_info=None):
        if HAS_CLOCK_GETTIME and (
                rtime.CLOCK_PROF is not None or
                rtime.CLOCK_PROCESS_CPUTIME_ID is not None):
            if rtime.CLOCK_PROF is not None:
                clk_id = rtime.CLOCK_PROF
                implementation = "clock_gettime(CLOCK_PROF)"
            else:
                clk_id = rtime.CLOCK_PROCESS_CPUTIME_ID
                implementation = "clock_gettime(CLOCK_PROCESS_CPUTIME_ID)"
            with lltype.scoped_alloc(TIMESPEC) as timespec:
                ret = c_clock_gettime(clk_id, timespec)
                if ret == 0:
                    if w_info is not None:
                        with lltype.scoped_alloc(TIMESPEC) as tsres:
                            ret = c_clock_getres(clk_id, tsres)
                            if ret == 0:
                                res = _timespec_to_seconds(tsres)
                            else:
                                res = 1e-9
                        _setinfo(space, w_info,
                                 implementation, res, True, False)
                    return space.wrap(_timespec_to_seconds(timespec))

        if True: # XXX available except if it isn't?
            from rpython.rlib.rtime import (c_getrusage, RUSAGE, RUSAGE_SELF,
                                            decode_timeval)
            with lltype.scoped_alloc(RUSAGE) as rusage:
                ret = c_getrusage(RUSAGE_SELF, rusage)
                if ret == 0:
                    if w_info is not None:
                        _setinfo(space, w_info,
                                 "getrusage(RUSAGE_SELF)", 1e-6, True, False)
                    return space.wrap(decode_timeval(rusage.c_ru_utime) +
                                      decode_timeval(rusage.c_ru_stime))
        if have_times:
            with lltype.scoped_alloc(rposix.TMS) as tms:
                ret = rposix.c_times(tms)
                if rffi.cast(lltype.Signed, ret) != -1:
                    cpu_time = float(rffi.cast(lltype.Signed,
                                               tms.c_tms_utime) +
                                     rffi.cast(lltype.Signed,
                                               tms.c_tms_stime))
                    if w_info is not None:
                        _setinfo(space, w_info, "times()",
                                 1.0 / rposix.CLOCK_TICKS_PER_SECOND,
                                 True, False)
                    return space.wrap(cpu_time / rposix.CLOCK_TICKS_PER_SECOND)
        return clock(space)

_clock = external('clock', [], rposix.CLOCK_T)
def clock(space, w_info=None):
    """clock() -> floating point number

    Return the CPU time or real time since the start of the process or since
    the first call to clock().  This has as much precision as the system
    records."""
    if _WIN:
        try:
            return win_perf_counter(space, w_info=w_info)
        except ValueError:
            pass
    value = widen(_clock())
    if value == widen(rffi.cast(rposix.CLOCK_T, -1)):
        raise oefmt(space.w_RuntimeError,
                    "the processor time used is not available or its value"
                    "cannot be represented")
    if w_info is not None:
        _setinfo(space, w_info,
                 "clock()", 1.0 / CLOCKS_PER_SEC, True, False)
    return space.wrap(float(value) / CLOCKS_PER_SEC)


def _setinfo(space, w_info, impl, res, mono, adj):
    space.setattr(w_info, space.wrap('implementation'), space.wrap(impl))
    space.setattr(w_info, space.wrap('resolution'), space.wrap(res))
    space.setattr(w_info, space.wrap('monotonic'), space.wrap(mono))
    space.setattr(w_info, space.wrap('adjustable'), space.wrap(adj))
