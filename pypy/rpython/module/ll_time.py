"""
Low-level implementations for the external functions of the 'time' module.
"""

import time, sys, math
from errno import EINTR
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.extfunc import BaseLazyRegistering, registering, extdef
from pypy.rlib import rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo

if sys.platform.startswith('win'):
    includes = ['time.h', 'windows.h']
else:
    includes = ['sys/time.h', 'time.h', 'errno.h', 'sys/select.h',
                'sys/types.h', 'unistd.h', 'sys/timeb.h']


class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=includes
    )
    CLOCK_T = platform.SimpleType('clock_t', rffi.INT)
    TIMEVAL = platform.Struct('struct timeval', [('tv_sec', rffi.INT),
                                                 ('tv_usec', rffi.INT)])
    HAVE_GETTIMEOFDAY = platform.Has('gettimeofday')
    HAVE_FTIME = platform.Has('ftime')

class CConfigForFTime:
    _compilation_info_ = ExternalCompilationInfo(includes=['sys/timeb.h'])
    TIMEB = platform.Struct('struct timeb', [('time', rffi.INT),
                                             ('millitm', rffi.INT)])

constant_names = ['CLOCKS_PER_SEC', 'CLK_TCK', 'EINTR']
for const in constant_names:
    setattr(CConfig, const, platform.DefinedConstantInteger(const))
defs_names = ['GETTIMEOFDAY_NO_TZ']
for const in defs_names:
    setattr(CConfig, const, platform.Defined(const))

class RegisterTime(BaseLazyRegistering):
    def __init__(self):
        self.configure(CConfig)
        if self.CLOCKS_PER_SEC is None:
            if self.CLK_TCK is None:
                self.CLOCKS_PER_SEC = 1000000
            else:
                self.CLOCKS_PER_SEC = self.CLK_TCK
        self.TIMEVALP = lltype.Ptr(self.TIMEVAL)

    @registering(time.time)
    def register_time_time(self):
        # Note: time.time() is used by the framework GC during collect(),
        # which means that we have to be very careful about not allocating
        # GC memory here.  This is the reason for the _nowrapper=True.

        # AWFUL
        if self.HAVE_GETTIMEOFDAY:
            if self.GETTIMEOFDAY_NO_TZ:
                c_gettimeofday = self.llexternal('gettimeofday',
                                 [self.TIMEVALP], rffi.INT,
                                  _nowrapper=True, threadsafe=False)
            else:
                c_gettimeofday = self.llexternal('gettimeofday',
                                 [self.TIMEVALP, rffi.VOIDP], rffi.INT,
                                  _nowrapper=True, threadsafe=False)
        else:
            c_gettimeofday = None

        if self.HAVE_FTIME:
            self.configure(CConfigForFTime)
            c_ftime = self.llexternal('ftime', [lltype.Ptr(self.TIMEB)],
                                      lltype.Void,
                                      _nowrapper=True, threadsafe=False)
        else:
            c_ftime = None    # to not confuse the flow space

        c_time = self.llexternal('time', [rffi.VOIDP], rffi.TIME_T,
                                 _nowrapper=True, threadsafe=False)

        def time_time_llimpl():
            void = lltype.nullptr(rffi.VOIDP.TO)
            result = -1.0
            if self.HAVE_GETTIMEOFDAY:
                t = lltype.malloc(self.TIMEVAL, flavor='raw')

                if self.GETTIMEOFDAY_NO_TZ:
                    if rffi.cast(rffi.LONG, c_gettimeofday(t)) == 0:
                        result = float(t.c_tv_sec) + \
                                 float(t.c_tv_usec) * 0.000001
                else:
                    if rffi.cast(rffi.LONG, c_gettimeofday(t, void)) == 0:
                        result = float(t.c_tv_sec) + \
                                 float(t.c_tv_usec) * 0.000001
                lltype.free(t, flavor='raw')
            if result != -1:
                return result
            if self.HAVE_FTIME:
                t = lltype.malloc(self.TIMEB, flavor='raw')
                c_ftime(t)
                result = float(int(t.c_time)) + float(int(t.c_millitm)) * 0.001
                lltype.free(t, flavor='raw')
                return result
            return float(c_time(void))

        return extdef([], float, llimpl=time_time_llimpl,
                      export_name='ll_time.ll_time_time')

    @registering(time.clock)
    def register_time_clock(self):
        c_clock = self.llexternal('clock', [], self.CLOCK_T,
                                  threadsafe=False)
        if sys.platform == 'win32':
            # hacking to avoid LARGE_INTEGER which is a union...
            A = lltype.FixedSizeArray(lltype.SignedLongLong, 1)
            QueryPerformanceCounter = self.llexternal(
                'QueryPerformanceCounter', [lltype.Ptr(A)], lltype.Void,
                threadsafe=False)
            QueryPerformanceFrequency = self.llexternal(
                'QueryPerformanceFrequency', [lltype.Ptr(A)], rffi.INT,
                threadsafe=False)
            class State(object):
                pass
            state = State()
            state.divisor = 0.0
            def time_clock_llimpl():
                a = lltype.malloc(A, flavor='raw')
                if state.divisor == 0.0:
                    QueryPerformanceCounter(a)
                    state.counter_start = a[0]
                    QueryPerformanceFrequency(a)
                    state.divisor = float(a[0])
                QueryPerformanceCounter(a)
                diff = a[0] - state.counter_start
                lltype.free(a, flavor='raw')
                return float(diff) / state.divisor
        else:
            def time_clock_llimpl():
                result = c_clock()
                return float(result) / self.CLOCKS_PER_SEC

        return extdef([], float, llimpl=time_clock_llimpl,
                      export_name='ll_time.ll_time_clock')

    @registering(time.sleep)
    def register_time_sleep(self):
        if sys.platform == 'win32':
            MAX = sys.maxint
            Sleep = self.llexternal('Sleep', [rffi.ULONG], lltype.Void)
            def time_sleep_llimpl(secs):
                millisecs = secs * 1000.0
                while millisecs > MAX:
                    Sleep(MAX)
                    millisecs -= MAX
                Sleep(rffi.cast(rffi.ULONG, int(millisecs)))
        else:
            c_select = self.llexternal('select', [rffi.INT, rffi.VOIDP,
                                                  rffi.VOIDP, rffi.VOIDP,
                                                  self.TIMEVALP], rffi.INT)
            
            def time_sleep_llimpl(secs):
                void = lltype.nullptr(rffi.VOIDP.TO)
                t = lltype.malloc(self.TIMEVAL, flavor='raw')
                try:
                    frac = math.fmod(secs, 1.0)
                    t.c_tv_sec = int(secs)
                    t.c_tv_usec = int(frac*1000000.0)
                    if rffi.cast(rffi.LONG, c_select(0, void, void, void, t)) != 0:
                        errno = rposix.get_errno()
                        if errno != EINTR:
                            raise OSError(rposix.get_errno(), "Select failed")
                finally:
                    lltype.free(t, flavor='raw')

        return extdef([float], None, llimpl=time_sleep_llimpl,
                      export_name='ll_time.ll_time_sleep')
