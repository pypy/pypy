from rpython.rtyper.tool import rffi_platform as platform
from rpython.rtyper.lltypesystem import rffi
from pypy.interpreter.error import (OperationError, oefmt,
        strerror as _strerror, exception_from_saved_errno)
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.time.timeutils import (
    SECS_TO_NS, MS_TO_NS, US_TO_NS, timestamp_w)
from pypy.interpreter.unicodehelper import decode_utf8sp
from pypy.module._codecs.locale import (
    str_decode_locale_surrogateescape, utf8_encode_locale_surrogateescape)
from pypy import pypydir
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.rarithmetic import (
    intmask, r_ulonglong, r_longfloat, r_int64, widen, ovfcheck,
    ovfcheck_float_to_int, INT_MIN, r_uint, r_longlong)
from rpython.rlib.rtime import (TIMEVAL,
                    HAVE_GETTIMEOFDAY, HAVE_FTIME)
from rpython.rlib import rposix, rtime
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.objectmodel import we_are_translated
from rpython.tool.cparser import CTypeSpace
from rpython.translator import cdir

import errno
import os
import math
import sys
import time as pytime

src_dir = os.path.join(pypydir, 'module', 'cpyext',  'src')
my_dir = os.path.join(pypydir, 'module', 'time',  'src')

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


if r_uint.BITS == 64:
    tolong = intmask
else:
    tolong = r_int64

if _WIN:
    # Interruptible sleeps on Windows:
    # We install a specific Console Ctrl Handler which sets an 'event'.
    # time.sleep() will actually call WaitForSingleObject with the desired
    # timeout.  On Ctrl-C, the signal handler is called, the event is set,
    # and the wait function exits.
    from rpython.rlib import rwin32
    from pypy.interpreter.error import wrap_oserror
    from rpython.rlib import rthread as thread

    wineci = ExternalCompilationInfo(
        includes = ['windows.h'],
        post_include_bits = [
            "RPY_EXTERN\n"
            "BOOL pypy_timemodule_setCtrlHandler(HANDLE event);\n"
            "RPY_EXTERN ULONGLONG pypy_GetTickCount64(FARPROC address);"
        ],
        separate_module_sources=['''
            /* this 'extern' is defined in translator/c/src/signals.c */
            #ifdef PYPY_SIGINT_INTERRUPT_EVENT
            extern HANDLE pypy_sigint_interrupt_event;
            #endif

            static BOOL WINAPI CtrlHandlerRoutine(
              DWORD dwCtrlType)
            {
                return TRUE;     /* like CPython 3.6 */
            }

            BOOL pypy_timemodule_setCtrlHandler(HANDLE event)
            {
            #ifdef PYPY_SIGINT_INTERRUPT_EVENT
                pypy_sigint_interrupt_event = event;
            #endif
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
        compilation_info=wineci,
        save_err=rffi.RFFI_SAVE_LASTERROR)

    pypy_GetTickCount64 = rffi.llexternal(
        'pypy_GetTickCount64',
        [rffi.VOIDP],
        rffi.ULONGLONG, compilation_info=wineci)

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
                raise wrap_oserror(space, e)
            if not _setCtrlHandlerRoutine(globalState.interrupt_event):
                raise wrap_oserror(space,
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
            self.divisor = 0
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

cts = CTypeSpace()
with open(os.path.join(my_dir, 'time_module.h')) as fid:
    data = fid.read()
    start = data.find("// parse from here")
    stop = data.find("// stop parsing")
    src = data[start:stop]
cts.parse_source(src)

compile_extra = ["-DBUILD_TIME_MODULE", "-DHAVE_CLOCK_GETTIME"]
_includes = ["time.h"]
if _POSIX:
    _includes.append('sys/time.h')
    _includes.append(os.path.join(my_dir, "time_module_posix.h"))
    compile_extra.append("-DHAVE_SYS_TIME_H")
if _MACOSX:
    _includes.append('mach/mach_time.h')
    compile_extra.append("-DHAVE_SYS_TIME_H")
if _WIN:
    compile_extra.append("-DMS_WINDOWS")

HAS_CLOCK_HIGHRES = rtime.CLOCK_HIGHRES is not None
separate_module_sources = []
if HAS_CLOCK_HIGHRES:
    compile_extra.append("-DCLOCK_HIGHRES")

if rtime.HAVE_NANOSLEEP:
    compile_extra.append("-DHAVE_NANOSLEEP")
    separate_module_sources.append("""
        #include <errno.h>
        RPY_EXTERN int
        py_nanosleep(const struct timespec *rqtp, struct timespec *rmtp);

        RPY_EXTERN int
        py_nanosleep(const struct timespec *rqtp, struct timespec *rmtp)
        {
            int ret = nanosleep(rqtp, rmtp);
            if (ret == 0)
                return 0;
            return errno;
        }
    """)

if rtime.HAVE_CLOCK_NANOSLEEP:
    compile_extra.append("-DHAVE_CLOCK_NANOSLEEP")
    separate_module_sources.append("""
        #include <errno.h>

        RPY_EXTERN int
        py_clock_nanosleep(clockid_t clockid, int flags,
                           const struct timespec *request,
                           struct timespec *remain);
        RPY_EXTERN int
        py_clock_nanosleep(clockid_t clockid, int flags,
                           const struct timespec *request,
                           struct timespec *remain)
        {
            int ret = clock_nanosleep(clockid, flags, request, remain);
            if (ret == 0)
                return 0;
            errno = ret;
            return ret;
        }
    """)

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=_includes,
        include_dirs = [my_dir, cdir],
        libraries=rtime.libraries,
        separate_module_files=[os.path.join(src_dir, "pytime.c")],
        separate_module_sources=separate_module_sources,
        compile_extra=compile_extra,
    )
    CLOCKS_PER_SEC = platform.ConstantInteger("CLOCKS_PER_SEC")

HAS_TM_ZONE = False

clock_info_t = cts.gettype("_Py_clock_info_t")
_PyTime_ROUND_CEILING = cts.definitions['_PyTime_round_t']._PyTime_ROUND_CEILING
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
    if _WIN and rffi.sizeof(rffi.TIME_T) == 8 and not name.startswith("_PyTime"):
        # Recent Microsoft compilers use 64bit time_t and
        # the corresponding functions are named differently
        if (rffi.TIME_T in args or rffi.TIME_TP in args
            or result in (rffi.TIME_T, rffi.TIME_TP)):
            name = '_' + name + '64'
    _calling_conv = kwds.pop('calling_conv', calling_conv)
    releasegil = kwds.pop('releasegil', False)
    return rffi.llexternal(name, args, result,
                           compilation_info=eci,
                           calling_conv=_calling_conv,
                           releasegil=releasegil,
                           **kwds)

if _POSIX:
    cConfig.timeval.__name__ = "_timeval"
    timeval = cConfig.timeval

CLOCKS_PER_SEC = cConfig.CLOCKS_PER_SEC
HAS_CLOCK_GETTIME_RUNTIME = rtime.HAS_CLOCK_GETTIME_RUNTIME
HAS_CLOCK_HIGHRES = rtime.CLOCK_HIGHRES is not None
HAS_CLOCK_MONOTONIC = rtime.CLOCK_MONOTONIC is not None
HAS_MONOTONIC = (_WIN or _MACOSX or
                 (HAS_CLOCK_GETTIME_RUNTIME and (HAS_CLOCK_HIGHRES or HAS_CLOCK_MONOTONIC)))
HAS_THREAD_TIME = (_WIN or
                   (HAS_CLOCK_GETTIME_RUNTIME and rtime.CLOCK_PROCESS_CPUTIME_ID is not None))
tm = cConfig.tm
pytime_t = rffi.LONGLONG  # int64_t

glob_buf = lltype.malloc(tm, flavor='raw', zero=True, immortal=True)

_PyTime_GetPerfCounterWithInfo = external("_PyTime_GetPerfCounterWithInfo",
    [rffi.CArrayPtr(pytime_t), rffi.CArrayPtr(clock_info_t)], rffi.INT)
_PyTime_GetMonotonicClockWithInfo = external("_PyTime_GetMonotonicClockWithInfo",
    [rffi.CArrayPtr(pytime_t), rffi.CArrayPtr(clock_info_t)], rffi.INT)

_PyTime_GetSystemClockWithInfo = external("_PyTime_GetSystemClockWithInfo",
    [rffi.CArrayPtr(pytime_t), rffi.CArrayPtr(clock_info_t)], rffi.INT)

_PyTime_AsSecondsDouble = external("_PyTime_AsSecondsDouble", [pytime_t], rffi.DOUBLE)

if _WIN:
    _GetSystemTimeAsFileTime = rwin32.winexternal('GetSystemTimeAsFileTime',
                                                  [lltype.Ptr(rwin32.FILETIME)],
                                                  lltype.Void)
    LPDWORD = rwin32.LPDWORD
    _GetSystemTimeAdjustment = rwin32.winexternal(
                                            'GetSystemTimeAdjustment',
                                            [LPDWORD, LPDWORD, rwin32.LPBOOL],
                                            rffi.INT)
    def _gettimeofday_impl(space, w_info, return_ns):
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
            offset = (r_ulonglong(16384) * r_ulonglong(27) *
                      r_ulonglong(390625) * r_ulonglong(79) *
                      r_ulonglong(853)  * r_ulonglong(10))
            microseconds10x = quad_part - offset
            if w_info:
                with lltype.scoped_alloc(LPDWORD.TO, 1) as time_adjustment, \
                     lltype.scoped_alloc(LPDWORD.TO, 1) as time_increment, \
                     lltype.scoped_alloc(rwin32.LPBOOL.TO, 1) as is_time_adjustment_disabled:
                    _GetSystemTimeAdjustment(time_adjustment, time_increment,
                                             is_time_adjustment_disabled)

                    _setinfo(space, w_info, "GetSystemTimeAsFileTime()",
                             intmask(time_increment[0]) * 1e-7, False, True)
            if return_ns:
                return space.newint(tolong(microseconds10x) * 10**2)
            else:
                return space.newfloat(float(tolong(microseconds10x)) / 1e7)
else:
    if HAVE_GETTIMEOFDAY:
        if rtime.GETTIMEOFDAY_NO_TZ:
            c_gettimeofday = external('gettimeofday',
                                      [lltype.Ptr(TIMEVAL)], rffi.INT)
        else:
            c_gettimeofday = external('gettimeofday',
                                      [lltype.Ptr(TIMEVAL), rffi.VOIDP], rffi.INT)
    def _gettimeofday_impl(space, w_info, return_ns):
        if HAVE_GETTIMEOFDAY:
            with lltype.scoped_alloc(TIMEVAL) as timeval:
                if rtime.GETTIMEOFDAY_NO_TZ:
                    errcode = c_gettimeofday(timeval)
                else:
                    void = lltype.nullptr(rffi.VOIDP.TO)
                    errcode = c_gettimeofday(timeval, void)
                if rffi.cast(rffi.LONG, errcode) == 0:
                    if w_info is not None:
                        _setinfo(space, w_info, "gettimeofday()", 1e-6, False, True)
                    if return_ns:
                        return space.newint(
                            r_int64(timeval.c_tv_sec) * 10**9 +
                            r_int64(timeval.c_tv_usec) * 10**3)
                    else:
                        return space.newfloat(
                            widen(timeval.c_tv_sec) +
                            widen(timeval.c_tv_usec) * 1e-6)
        if HAVE_FTIME:
            with lltype.scoped_alloc(TIMEB) as t:
                c_ftime(t)
                if w_info is not None:
                    _setinfo(space, w_info, "ftime()", 1e-3, False, True)
                if return_ns:
                    return space.newint(
                        r_int64(t.c_time) * 10**9 +
                        r_int64(intmask(t.c_millitm)) * 10**6)
                else:
                    return space.newfloat(
                        widen(t.c_time) +
                        widen(t.c_millitm) * 1e-3)
        else:
            if w_info:
                _setinfo(space, w_info, "time()", 1.0, False, True)
            result = c_time(lltype.nullptr(rffi.TIME_TP.TO))
            if return_ns:
                return space.newint(r_int64(result) * 10**9)
            else:
                return space.newfloat(float(result))

    def gettimeofday(space, w_info=None):
        return _gettimeofday_impl(space, w_info, False)

    _PyTime_AsTimeval = external("_PyTime_AsTimeval",
        [pytime_t, lltype.Ptr(TIMEVAL), rffi.INT], rffi.INT)
    TIMER_ABSTIME = 0x01  # from time.h on linux

TM_P = lltype.Ptr(tm)
c_time = external('time', [rffi.TIME_TP], rffi.TIME_T)
c_gmtime = external('gmtime', [rffi.TIME_TP], TM_P,
                    save_err=rffi.RFFI_SAVE_ERRNO)
c_mktime = external('mktime', [TM_P], rffi.TIME_T)
c_localtime = external('localtime', [rffi.TIME_TP], TM_P,
                       save_err=rffi.RFFI_SAVE_ERRNO)
if HAS_CLOCK_GETTIME_RUNTIME:
    from rpython.rlib.rtime import TIMESPEC, c_clock_gettime
    from rpython.rlib.rtime import c_clock_settime, c_clock_getres
    _PyTime_AsTimespec = external("_PyTime_AsTimespec",
        [pytime_t, lltype.Ptr(TIMESPEC)], rffi.INT)
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
                             "int pypy_get_tzname(size_t, int, char*);\n"
                             "RPY_EXTERN "
                             "void pypy__tzset();"],
        separate_module_sources = ["""
            long pypy_get_timezone() {
                long timezone;
                _get_timezone(&timezone);
                return timezone;
            };
            int pypy_get_daylight() {
                int daylight;
                _get_daylight(&daylight);
                return daylight;
            };
            int pypy_get_tzname(size_t len, int index, char * tzname) {
                size_t s;
                errno_t ret = _get_tzname(&s, tzname, len, index);
                return (int)s;
            };
            void pypy__tzset() { _tzset(); }
        """])
    # Ensure sure that we use _tzset() and timezone from the same C Runtime.
    c_tzset = external('pypy__tzset', [], lltype.Void, win_eci)
    c_get_timezone = external('pypy_get_timezone', [], rffi.LONG, win_eci)
    c_get_daylight = external('pypy_get_daylight', [], rffi.INT, win_eci)
    c_get_tzname = external('pypy_get_tzname',
                            [rffi.SIZE_T, rffi.INT, rffi.CCHARP],
                            rffi.INT, win_eci, calling_conv='c')

if _WIN:
    c_strftime = external('wcsftime',
                      [rffi.CWCHARP, rffi.SIZE_T, rffi.CWCHARP, TM_P],
                      rffi.SIZE_T,
                      save_err=rffi.RFFI_FULL_ERRNO_ZERO)
    _CreateWaitableTimerExW = rwin32.winexternal('CreateWaitableTimerExW',
            [rwin32.LPSECURITY_ATTRIBUTES, rwin32.LPCWSTR, rwin32.DWORD, rwin32.DWORD], rwin32.HANDLE)
    _SetWaitableTimerEx = rwin32.winexternal('SetWaitableTimerEx',
            [rwin32.HANDLE, rffi.CArrayPtr(rffi.LONGLONG), rffi.LONG, rffi.VOIDP, rffi.VOIDP, rffi.VOIDP, rffi.ULONG], rwin32.BOOL)
else:
    c_strftime = external('strftime',
                      [rffi.CCHARP, rffi.SIZE_T, rffi.CCHARP, TM_P],
                      rffi.SIZE_T)

if rtime.HAVE_NANOSLEEP:
    from rpython.rlib.rtime import TIMESPEC
    nanosleep = external("py_nanosleep",
        [lltype.Ptr(TIMESPEC), lltype.Ptr(TIMESPEC)],
        rffi.INT, releasegil=True, save_err=rffi.RFFI_SAVE_ERRNO)
if rtime.HAVE_CLOCK_NANOSLEEP:
    from rpython.rlib.rtime import TIMESPEC
    clock_nanosleep = external("py_clock_nanosleep",
        [rffi.INT, rffi.INT, lltype.Ptr(TIMESPEC), lltype.Ptr(TIMESPEC)],        rffi.INT, releasegil=True, save_err=rffi.RFFI_SAVE_ERRNO)

def _init_timezone(space):
    timezone = daylight = altzone = 0
    tzname = ["", ""]

    if _WIN:
        c_tzset()
        timezone = c_get_timezone()
        altzone = timezone - 3600
        daylight = c_get_daylight()
        for i in [0, 1]:
            blen = c_get_tzname(0, i, None)
            with rffi.scoped_alloc_buffer(blen) as buf:
                s = c_get_tzname(blen, i, buf.raw)
                tzn = buf.str(s - 1)
                tznutf8, _ = str_decode_locale_surrogateescape(tzn)
                tzname[i] = tznutf8

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

    _set_module_object(space, "timezone", space.newint(timezone))
    _set_module_object(space, 'daylight', space.newint(daylight))
    tzname_w = [space.newtext(tzname[0]),
                space.newtext(tzname[1])]
    _set_module_object(space, 'tzname', space.newtuple(tzname_w))
    _set_module_object(space, 'altzone', space.newint(altzone))

def _get_error_msg():
    errno = rposix.get_saved_errno()
    return _strerror(errno)

from errno import EINTR
if not _WIN:
    from rpython.rlib.rtime import c_select
from rpython.rlib import rwin32

def time_sleep(space, w_secs):
    timeout = timestamp_w(space, w_secs)
    if not (timeout >= 0):
        raise oefmt(space.w_ValueError,
                    "sleep length must be non-negative")
    deadline = _monotonic_impl(space, None) + timeout
    timeout_abs = None
    timeout_ts = None
    timeout_tv = None
    if _WIN:
        timer = rffi.cast(rwin32.HANDLE, 0)
    try:
        if rtime.HAVE_CLOCK_NANOSLEEP:
            timeout_abs = lltype.malloc(TIMESPEC, flavor='raw')
            if _PyTime_AsTimespec(deadline, timeout_abs) < 0:
                raise oefmt(space.w_OverflowError,
                    "timestamp out of range for platform time_t")
        elif rtime.HAVE_NANOSLEEP:
            timeout_ts = lltype.malloc(TIMESPEC, flavor='raw')
        elif not _WIN:
            timeout_tv = lltype.malloc(TIMEVAL, flavor ='raw')
        while True:
            # 'deadline' is reduced at the end of the loop, for the next iteration.
            NULL = lltype.nullptr(rffi.VOIDP.TO)
            if _WIN:
                timeout_100ns = timeout // 100
                if timeout_100ns == 0:
                    # A value of zero causes the thread to relinquish the remainder of its
                    # time slice to any other thread that is ready to run. If there are no
                    # other threads ready to run, the function returns immediately, and
                    # the thread continues execution.
                    rtime.Sleep(rffi.cast(rffi.ULONG, 0))
                    return
                relative_timeout = rffi.cast(rffi.LONGLONG, -timeout_100ns)
                timer_flags = 0x02  # CREATE_WAITABLE_TIMER_HIGH_RESOLUTION
                all_access = 0x1F0003   # TIMER_ALL_ACCESS
                timer = _CreateWaitableTimerExW(lltype.nullptr(rwin32.LPSECURITY_ATTRIBUTES.TO),
                                                rffi.cast(rwin32.LPCWSTR, 0),
                                                timer_flags, all_access)
                if not timer:
                    raise exception_from_saved_errno(space, space.w_OSError)
                assert timer is not None
                with lltype.scoped_alloc(rffi.CArray(rffi.LONGLONG), 1) as rt:
                    rt[0] = relative_timeout
                    if not _SetWaitableTimerEx(timer, rt, 0, NULL, NULL, NULL, 0):
                        raise exception_from_saved_errno(space, space.w_OSError)

                main_thread = space.fromcache(State).main_thread
                interruptible = (main_thread == thread.get_ident())
                if interruptible:
                    # Only the main thread can be interrupted
                    space.getexecutioncontext().checksignals()
                    interrupt_event = space.fromcache(State).get_interrupt_event()
                    rwin32.ResetEvent(interrupt_event)
                    rc = rwin32.WaitForMultipleObjects([interrupt_event, timer])
                else:
                    rc = rwin32.WaitForSingleObject(timer, rwin32.INFINITE)
                if rc == rwin32.WAIT_FAILED:
                    raise exception_from_saved_errno(space, space.w_OSError)
                if rc == rwin32.WAIT_OBJECT_0:
                    break
            else:
                NULL_TS = lltype.nullptr(lltype.Ptr(TIMESPEC).TO)
                if rtime.HAVE_CLOCK_NANOSLEEP:
                    ret = clock_nanosleep(rtime.CLOCK_MONOTONIC, TIMER_ABSTIME, timeout_abs, NULL_TS);
                    pass
                elif rtime.HAVE_NANOSLEEP:
                    if _PyTime_AsTimespec(timeout, timeout_ts) < 0:
                        raise oefmt(space.w_OverflowError,
                            "timestamp out of range for platform time_t")
                    ret = nanosleep(timeout_ts, NULL_TS);
                    if ret == 0:
                        break
                    if ret != EINTR:
                        raise exception_from_saved_errno(space, space.w_OSError)
                else:
                    if _PyTime_AsTimeval(timeout, timeout_tv, _PyTime_ROUND_CEILING) < 0:
                        raise oefmt(space.w_OverflowError,
                            "timestamp out of range for platform time_t")
                    ret = rffi.cast(rffi.LONG,
                                    c_select(0, NULL, NULL, NULL, timeout_tv))
                if ret == 0:
                    break    # normal path
                if ret != EINTR:
                    raise exception_from_saved_errno(space, space.w_OSError)
            space.getexecutioncontext().checksignals()
            timeout = deadline - _monotonic_impl(space, None)   # retry
            if timeout <= 0:
                break
    finally:
        if timeout_abs:
            lltype.free(timeout_abs, flavor='raw')
        if timeout_ts:
            lltype.free(timeout_ts, flavor='raw')
        if timeout_tv:
            lltype.free(timeout_tv, flavor='raw')
        if _WIN and timer:
            rwin32.CloseHandle(timer)


def _get_module_object(space, obj_name):
    w_module = space.getbuiltinmodule('time')
    w_obj = space.getattr(w_module, space.newtext(obj_name))
    return w_obj


def _set_module_object(space, obj_name, w_obj_value):
    w_module = space.getbuiltinmodule('time')
    space.setattr(w_module, space.newtext(obj_name), w_obj_value)
    # XXX find a more appropriate way to ensure the values are preserved
    # across module reloading
    from pypy.interpreter.mixedmodule import MixedModule
    assert isinstance(w_module, MixedModule)
    w_module.reset_lazy_initial_values()


def _get_inttime(space, w_seconds):
    # w_seconds can be a wrapped None (it will be automatically wrapped
    # in the callers, so we never get a real None here).
    if space.is_none(w_seconds):
        seconds = pytime.time()
    else:
        seconds = space.float_w(w_seconds)
        if math.isnan(seconds):
            raise oefmt(space.w_ValueError,
                        "Invalid value Nan (not a number)")
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

def _tm_to_tuple(space, t, zone="UTC", offset=0):
    time_tuple = [
        space.newint(rffi.getintfield(t, 'c_tm_year') + 1900),
        space.newint(rffi.getintfield(t, 'c_tm_mon') + 1), # want january == 1
        space.newint(rffi.getintfield(t, 'c_tm_mday')),
        space.newint(rffi.getintfield(t, 'c_tm_hour')),
        space.newint(rffi.getintfield(t, 'c_tm_min')),
        space.newint(rffi.getintfield(t, 'c_tm_sec')),
        space.newint((rffi.getintfield(t, 'c_tm_wday') + 6) % 7), # want monday == 0
        space.newint(rffi.getintfield(t, 'c_tm_yday') + 1), # want january, 1 == 1
        space.newint(rffi.getintfield(t, 'c_tm_isdst'))]

    if HAS_TM_ZONE:
        # CPython calls PyUnicode_DecodeLocale here should we do the same?
        tm_zone, lgt, pos = decode_utf8sp(space, rffi.charp2str(t.c_tm_zone))
        extra = [space.newtext(tm_zone, lgt),
                 space.newint(rffi.getintfield(t, 'c_tm_gmtoff'))]
    else:
        extra = [space.newtext(zone), space.newint(offset)]
    w_time_tuple = space.newtuple(time_tuple + extra)
    w_struct_time = _get_module_object(space, 'struct_time')
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
                                 space.newtext(*_get_error_msg()))
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
    #
    if HAS_TM_ZONE :
        old_tm_zone = glob_buf.c_tm_zone
        glob_buf.c_tm_zone = lltype.nullptr(rffi.CCHARP.TO)
        rffi.setintfield(glob_buf, 'c_tm_gmtoff', 0)
        if len(tup_w) >= 10:
            # NOTE this is not cleanly solved!
            # it saves the string that is later deleted when this
            # function is called again. A refactoring of this module
            # could remove this
            tm_zone = space.utf8_w(tup_w[9])
            malloced_str = rffi.str2charp(tm_zone, track_allocation=False)
            if old_tm_zone != lltype.nullptr(rffi.CCHARP.TO):
                rffi.free_charp(old_tm_zone, track_allocation=False)
            glob_buf.c_tm_zone = malloced_str
        if len(tup_w) >= 11:
            rffi.setintfield(glob_buf, 'c_tm_gmtoff', space.c_int_w(tup_w[10]))

    if (y < INT_MIN + 1900):
        raise oefmt(space.w_OverflowError, "year out of range")

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

def _time_impl(space, w_info):
    with lltype.scoped_alloc(rffi.CArray(pytime_t), 1) as t:
        if w_info:
            with lltype.scoped_alloc(rffi.CArray(clock_info_t), 1) as info:
                res = _PyTime_GetSystemClockWithInfo(t, info)
                implementation = rffi.constcharp2str(info[0].c_implementation)
                resolution = info[0].c_resolution
                mono = bool(widen(info[0].c_monotonic))
                adjust =  bool(widen(info[0].c_adjustable))
                _setinfo(space, w_info, implementation, resolution, mono, adjust)
        else:
            res = _PyTime_GetSystemClockWithInfo(t, rffi.cast(rffi.CArrayPtr(clock_info_t), 0))
        if res < 0:
            raise oefmt(space.w_RuntimeError, "could not get system clock")
        return widen(t[0])

def time_time(space):
    """time() -> floating point number

    Return the current time in seconds since the Epoch.
    Fractions of a second may be present if the system clock provides them."""
    t = _time_impl(space, None)
    d = _PyTime_AsSecondsDouble(t)
    return space.newfloat(d)

def time_time_ns(space):
    """time_ns() -> int

    Return the current time in nanoseconds since the Epoch."""
    t = _time_impl(space, None)
    return space.newint(t)

@unwrap_spec(name='text0')
def _get_time_info(space, name, w_info):
    """_get_time_info(name, info) -> None
    Internal helper for get_clock_info
    """
    if name == 'time':
        _time_impl(space, w_info)
    elif name == 'monotonic':
        _monotonic_impl(space, w_info)
    elif name == 'perf_counter':
        _perf_counter_impl(space, w_info)
    elif name == "process_time":
        _process_time_impl(space, w_info, False)
    elif name == "thread_time" and HAS_THREAD_TIME:
        _thread_time_impl(space, w_info, False)
    else:
        raise oefmt(space.w_ValueError, "unknown clock")

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
    getif = rffi.getintfield
    args = [space.newtext(_wday_names[getif(t_ref, 'c_tm_wday')]),
            space.newtext(_mon_names[getif(t_ref, 'c_tm_mon')]),
            space.newint(getif(t_ref, 'c_tm_mday')),
            space.newint(getif(t_ref, 'c_tm_hour')),
            space.newint(getif(t_ref, 'c_tm_min')),
            space.newint(getif(t_ref, 'c_tm_sec')),
            space.newint(getif(t_ref, 'c_tm_year'))]
    return space.mod(space.newtext("%.3s %.3s%3d %.2d:%.2d:%.2d %d"),
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
    with lltype.scoped_alloc(rffi.TIME_TP.TO, 1) as t_ref:
        t_ref[0] = seconds
        p = c_gmtime(t_ref)
        if not p:
            raise exception_from_saved_errno(space, space.w_OSError)
    return _tm_to_tuple(space, p, zone="UTC", offset=0)

def localtime(space, w_seconds=None):
    """localtime([seconds]) -> (tm_year, tm_mon, tm_day, tm_hour, tm_min,
                             tm_sec, tm_wday, tm_yday, tm_isdst)

    Convert seconds since the Epoch to a time tuple expressing local time.
    When 'seconds' is not passed in, convert the current time instead."""

    seconds = _get_inttime(space, w_seconds)
    with lltype.scoped_alloc(rffi.TIME_TP.TO, 1) as t_ref:
        t_ref[0] = seconds
        p = c_localtime(t_ref)
        if not p:
            raise exception_from_saved_errno(space, space.w_OSError)
    if HAS_TM_ZONE:
        return _tm_to_tuple(space, p)
    else:
        offset = space.int_w(_get_module_object(space, "timezone"))
        daylight_w = _get_module_object(space, 'daylight')
        tzname_w =  _get_module_object(space, 'tzname')
        zone_w = space.getitem(tzname_w, daylight_w)
        if not space.eq_w(daylight_w, space.newint(0)):
            offset -= 3600
        return _tm_to_tuple(space, p, zone=space.utf8_w(zone_w), offset=-offset)


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

    return space.newfloat(float(tt))

if HAS_CLOCK_GETTIME_RUNTIME:
    def _timespec_to_seconds(timespec):
        return widen(timespec.c_tv_sec) + widen(timespec.c_tv_nsec) * 1e-9

    def _timespec_to_nanoseconds(timespec):
        return r_int64(timespec.c_tv_sec) * 10**9 + r_int64(timespec.c_tv_nsec)

    def _clock_gettime_impl(space, clk_id, return_ns):
        with lltype.scoped_alloc(TIMESPEC) as timespec:
            ret = c_clock_gettime(clk_id, timespec)
            if ret != 0:
                raise exception_from_saved_errno(space, space.w_OSError)
            if return_ns:
                return space.newint(_timespec_to_nanoseconds(timespec))
            else:
                return space.newfloat(_timespec_to_seconds(timespec))

    @unwrap_spec(clk_id='c_int')
    def clock_gettime(space, clk_id):
        """clock_gettime(clk_id) -> float

        Return the time of the specified clock clk_id."""
        return _clock_gettime_impl(space, clk_id, False)

    @unwrap_spec(clk_id='c_int')
    def clock_gettime_ns(space, clk_id):
        """clock_gettime_ns(clk_id) -> int

        Return the time of the specified clock clk_id as nanoseconds."""
        return _clock_gettime_impl(space, clk_id, True)

    @unwrap_spec(clk_id='c_int', secs=float)
    def clock_settime(space, clk_id, secs):
        """clock_settime(clk_id, time)

        Set the time of the specified clock clk_id."""
        with lltype.scoped_alloc(TIMESPEC) as timespec:
            integer_secs = rffi.cast(TIMESPEC.c_tv_sec, secs)
            frac = secs - widen(integer_secs)
            rffi.setintfield(timespec, 'c_tv_sec', integer_secs)
            rffi.setintfield(timespec, 'c_tv_nsec', int(frac * 1e9))
            ret = c_clock_settime(clk_id, timespec)
            if ret != 0:
                raise exception_from_saved_errno(space, space.w_OSError)

    @unwrap_spec(clk_id='c_int', ns=r_int64)
    def clock_settime_ns(space, clk_id, ns):
        """clock_settime_ns(clk_id, time)

        Set the time of the specified clock clk_id with nanoseconds."""
        with lltype.scoped_alloc(TIMESPEC) as timespec:
            rffi.setintfield(timespec, 'c_tv_sec', ns // 10**9)
            rffi.setintfield(timespec, 'c_tv_nsec', ns % 10**9)
            ret = c_clock_settime(clk_id, timespec)
            if ret != 0:
                raise exception_from_saved_errno(space, space.w_OSError)

    @unwrap_spec(clk_id='c_int')
    def clock_getres(space, clk_id):
        """clock_getres(clk_id) -> floating point number

        Return the resolution (precision) of the specified clock clk_id."""
        with lltype.scoped_alloc(TIMESPEC) as timespec:
            ret = c_clock_getres(clk_id, timespec)
            if ret != 0:
                raise exception_from_saved_errno(space, space.w_OSError)
            secs = _timespec_to_seconds(timespec)
        return space.newfloat(secs)

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

@unwrap_spec(format='text0')
def strftime(space, format, w_tup=None):
    """strftime(format[, tuple]) -> string

    Convert a time tuple to a string according to a format specification.
    See the library reference manual for formatting codes. When the time tuple
    is not present, current time as returned by localtime() is used."""
    from rpython.rlib.rutf8 import codepoints_in_utf8
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

    i = 1024
    passthrough = False
    if _WIN:
        tm_year = rffi.getintfield(buf_value, 'c_tm_year')
        if (tm_year + 1900 < 1 or  9999 < tm_year + 1900):
            raise oefmt(space.w_ValueError, "strftime() requires year in [1; 9999]")

        # wcharp with track_allocation=True
        format_for_call = rffi.utf82wcharp(
                    format, codepoints_in_utf8(format))
    else:
        try:
            format_for_call = utf8_encode_locale_surrogateescape(
                    format, codepoints_in_utf8(format))
        except UnicodeEncodeError:
            format_for_call = format
            passthrough = True
    try:
        while True:
            if _WIN:
                outbuf = lltype.malloc(rffi.CWCHARP.TO, i, flavor='raw')
            else:
                outbuf = lltype.malloc(rffi.CCHARP.TO, i, flavor='raw')
            try:
                with rposix.SuppressIPH():
                    buflen = c_strftime(outbuf, i, format_for_call, buf_value)
                if _WIN and buflen == 0 and rposix.get_saved_errno() == errno.EINVAL:
                    raise oefmt(space.w_ValueError, "invalid format string")
                if buflen > 0 or i >= 256 * len(format):
                    # if the buffer is 256 times as long as the format,
                    # it's probably not failing for lack of room!
                    # More likely, the format yields an empty result,
                    # e.g. an empty format, or %Z when the timezone
                    # is unknown.
                    if _WIN:
                        decoded, size = rffi.wcharp2utf8n(outbuf, intmask(buflen))
                    else:
                        result = rffi.charp2strn(outbuf, intmask(buflen))
                        if passthrough:
                            decoded = result
                            size = codepoints_in_utf8(result)
                        else:
                            decoded, size = str_decode_locale_surrogateescape(result)
                    return space.newutf8(decoded, size)
            finally:
                lltype.free(outbuf, flavor='raw')
            i += i
    finally:
        if _WIN:
            rffi.free_wcharp(format_for_call)

def _monotonic_impl(space, w_info):
    with lltype.scoped_alloc(rffi.CArray(pytime_t), 1) as t:
        if w_info:
            with lltype.scoped_alloc(rffi.CArray(clock_info_t), 1) as info:
                res = _PyTime_GetMonotonicClockWithInfo(t, info)
                implementation = rffi.constcharp2str(info[0].c_implementation)
                resolution = info[0].c_resolution
                mono = bool(widen(info[0].c_monotonic))
                adjust =  bool(widen(info[0].c_adjustable))
                _setinfo(space, w_info, implementation, resolution, mono, adjust)

        else:
            res = _PyTime_GetMonotonicClockWithInfo(t, rffi.cast(rffi.CArrayPtr(clock_info_t), 0))
        if res < 0:
            raise oefmt(space.w_RuntimeError, "could not get montonic clock")
        return t[0]


def _monotonic(space):
    t = _monotonic_impl(space, None)
    d = _PyTime_AsSecondsDouble(t)
    return d

def monotonic(space):
    """monotonic() -> float

    Monotonic clock, cannot go backward."""
    d = _monotonic(space)
    return space.newfloat(d)

def monotonic_ns(space):
    """monotonic_ns() -> int

    Monotonic clock, cannot go backward, as nanoseconds."""
    t = _monotonic_impl(space, None)
    return space.newint(t)

def _perf_counter_impl(space, w_info):
    with lltype.scoped_alloc(rffi.CArray(pytime_t), 1) as t:
        if w_info:
            with lltype.scoped_alloc(rffi.CArray(clock_info_t), 1) as info:
                res = _PyTime_GetPerfCounterWithInfo(t, info)
                implementation = rffi.constcharp2str(info[0].c_implementation)
                resolution = info[0].c_resolution
                mono = bool(widen(info[0].c_monotonic))
                adjust =  bool(widen(info[0].c_adjustable))
                _setinfo(space, w_info, implementation, resolution, mono, adjust)

        else:
            res = _PyTime_GetPerfCounterWithInfo(t, rffi.cast(rffi.CArrayPtr(clock_info_t), 0))
        if res < 0:
            raise oefmt(space.w_RuntimeError, "could not get perf_counter")
        return t[0]

def perf_counter(space):
    """perf_counter() -> float

    Performance counter for benchmarking."""

    t = _perf_counter_impl(space, None)
    d = _PyTime_AsSecondsDouble(t)
    return space.newfloat(d)

def perf_counter_ns(space):
    """perf_counter_ns() -> int

    Performance counter for benchmarking as nanoseconds."""
    t = _perf_counter_impl(space, None)
    return space.newint(t)


if _WIN:
    def _process_time_impl(space, w_info, return_ns):
        from rpython.rlib.rposix import GetCurrentProcess, GetProcessTimes
        current_process = GetCurrentProcess()
        with lltype.scoped_alloc(rwin32.FILETIME) as creation_time, \
             lltype.scoped_alloc(rwin32.FILETIME) as exit_time, \
             lltype.scoped_alloc(rwin32.FILETIME) as kernel_time, \
             lltype.scoped_alloc(rwin32.FILETIME) as user_time:
            worked = GetProcessTimes(current_process, creation_time, exit_time,
                                     kernel_time, user_time)
            if not worked:
                raise wrap_oserror(space,
                    rwin32.lastSavedWindowsError("GetProcessTimes"))
            kernel_time2 = (kernel_time.c_dwLowDateTime |
                            r_ulonglong(kernel_time.c_dwHighDateTime) << 32)
            user_time2 = (user_time.c_dwLowDateTime |
                          r_ulonglong(user_time.c_dwHighDateTime) << 32)
        if w_info is not None:
            _setinfo(space, w_info, "GetProcessTimes()", 1e-7, True, False)
        if return_ns:
            return space.newint((tolong(kernel_time2) +
                                 tolong(user_time2)) * 100)
        else:
            return space.newfloat((float(kernel_time2) +
                                   float(user_time2)) * 1e-7)
else:
    have_times = hasattr(rposix, 'c_times')

    def _process_time_impl(space, w_info, return_ns):
        if HAS_CLOCK_GETTIME_RUNTIME and (
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
                    if return_ns:
                        return space.newint(_timespec_to_nanoseconds(timespec))
                    else:
                        return space.newfloat(_timespec_to_seconds(timespec))

        if True: # XXX available except if it isn't?
            from rpython.rlib.rtime import (c_getrusage, RUSAGE, RUSAGE_SELF,
                                            decode_timeval, decode_timeval_ns)
            with lltype.scoped_alloc(RUSAGE) as rusage:
                ret = c_getrusage(RUSAGE_SELF, rusage)
                if ret == 0:
                    if w_info is not None:
                        _setinfo(space, w_info,
                                 "getrusage(RUSAGE_SELF)", 1e-6, True, False)
                    if return_ns:
                        return space.newint(
                            decode_timeval_ns(rusage.c_ru_utime) +
                            decode_timeval_ns(rusage.c_ru_stime))
                    else:
                        return space.newfloat(decode_timeval(rusage.c_ru_utime) +
                                              decode_timeval(rusage.c_ru_stime))
        if have_times:
            with lltype.scoped_alloc(rposix.TMS) as tms:
                ret = rposix.c_times(tms)
                if rffi.cast(lltype.Signed, ret) != -1:
                    cpu_time = (rffi.cast(lltype.Signed, tms.c_tms_utime) +
                                rffi.cast(lltype.Signed, tms.c_tms_stime))
                    if w_info is not None:
                        _setinfo(space, w_info, "times()",
                                 1.0 / rposix.CLOCK_TICKS_PER_SECOND,
                                 True, False)
                    if return_ns:
                        return space.newint(r_int64(cpu_time) * 10**9 // int(rposix.CLOCK_TICKS_PER_SECOND))
                    else:
                        return space.newfloat(float(cpu_time) / rposix.CLOCK_TICKS_PER_SECOND)
        return _clock_impl(space, w_info, return_ns)

def process_time(space):
    """process_time() -> float

    Process time for profiling: sum of the kernel and user-space CPU time."""
    return _process_time_impl(space, None, False)

def process_time_ns(space):
    """process_time() -> int

    Process time for profiling as nanoseconds:
    sum of the kernel and user-space CPU time"""
    return _process_time_impl(space, None, True)

if HAS_THREAD_TIME:
    if _WIN:
        FILETIME_P = lltype.Ptr(rwin32.FILETIME)
        _GetCurrentThread = rwin32.winexternal('GetCurrentThread', [], rwin32.HANDLE)
        _GetThreadTimes = rwin32.winexternal('GetThreadTimes',
                [rwin32.HANDLE, FILETIME_P, FILETIME_P, FILETIME_P, FILETIME_P],
                rwin32.BOOL)
        def _thread_time_impl(space, w_info, return_ns):
            thread = _GetCurrentThread()

            with lltype.scoped_alloc(rwin32.FILETIME) as creation_time, \
                 lltype.scoped_alloc(rwin32.FILETIME) as exit_time, \
                 lltype.scoped_alloc(rwin32.FILETIME) as kernel_time, \
                 lltype.scoped_alloc(rwin32.FILETIME) as user_time:
                ok = _GetThreadTimes(thread, creation_time, exit_time,
                                     kernel_time, user_time)
                if not ok:
                    raise wrap_oserror(space,
                        rwin32.lastSavedWindowsError("GetThreadTimes"))
                ktime = (kernel_time.c_dwLowDateTime |
                         r_ulonglong(kernel_time.c_dwHighDateTime) << 32)
                utime = (user_time.c_dwLowDateTime |
                         r_ulonglong(user_time.c_dwHighDateTime) << 32)

            if w_info is not None:
                _setinfo(space, w_info, "GetThreadTimes()", 1e-7, True, False)

            # ktime and utime have a resolution of 100 nanoseconds
            if return_ns:
                return space.newint((tolong(ktime) + tolong(utime)) * 10**2)
            else:
                return space.newfloat((float(ktime) + float(utime)) * 1e-7)
    else:
        def _thread_time_impl(space, w_info, return_ns):
            clk_id = rtime.CLOCK_THREAD_CPUTIME_ID
            implementation = "clock_gettime(CLOCK_THREAD_CPUTIME_ID)"

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
                        _setinfo(space, w_info, implementation, res, True, False)
                    if return_ns:
                        return space.newint(_timespec_to_nanoseconds(timespec))
                    else:
                        return space.newfloat(_timespec_to_seconds(timespec))

    def thread_time(space):
        """thread_time() -> float

        Thread time for profiling: sum of the kernel and user-space CPU time."""
        return _thread_time_impl(space, None, False)

    def thread_time_ns(space):
        """thread_time_ns() -> int

        Thread time for profiling as nanoseconds:
        sum of the kernel and user-space CPU time."""
        return _thread_time_impl(space, None, True)


_clock = external('clock', [], rposix.CLOCK_T)
def _clock_impl(space, w_info, return_ns):
    if _WIN:
        try:
            return _win_perf_counter_impl(space, w_info, return_ns)
        except ValueError:
            pass
    value = widen(_clock())
    if value == widen(rffi.cast(rposix.CLOCK_T, -1)):
        raise oefmt(space.w_RuntimeError,
                    "the processor time used is not available or its value"
                    "cannot be represented")

    if _MACOSX:
        # small hack apparently solving unsigned int on mac
        value = intmask(value)

    if w_info is not None:
        _setinfo(space, w_info, "clock()", 1.0 / CLOCKS_PER_SEC, True, False)
    if return_ns:
        return space.newint(r_int64(value) * 10**9 // CLOCKS_PER_SEC)
    else:
        return space.newfloat(float(value) / CLOCKS_PER_SEC)


def _setinfo(space, w_info, impl, res, mono, adj):
    space.setattr(w_info, space.newtext('implementation'), space.newtext(impl))
    space.setattr(w_info, space.newtext('resolution'), space.newfloat(res))
    space.setattr(w_info, space.newtext('monotonic'), space.newbool(mono))
    space.setattr(w_info, space.newtext('adjustable'), space.newbool(adj))
