import sys

from pypy.interpreter.error import exception_from_errno
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo


class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=["time.h"],
        libraries=["rt"],
    )

    HAS_CLOCK_GETTIME = rffi_platform.Has('clock_gettime')

    CLOCK_REALTIME = rffi_platform.DefinedConstantInteger("CLOCK_REALTIME")
    CLOCK_MONOTONIC = rffi_platform.DefinedConstantInteger("CLOCK_MONOTONIC")
    CLOCK_MONOTONIC_RAW = rffi_platform.DefinedConstantInteger("CLOCK_MONOTONIC_RAW")
    CLOCK_PROCESS_CPUTIME_ID = rffi_platform.DefinedConstantInteger("CLOCK_PROCESS_CPUTIME_ID")
    CLOCK_THREAD_CPUTIME_ID = rffi_platform.DefinedConstantInteger("CLOCK_THREAD_CPUTIME_ID")

    TIMESPEC = rffi_platform.Struct("struct timespec", [
        ("tv_sec", rffi.TIME_T),
        ("tv_nsec", rffi.LONG),
    ])

cconfig = rffi_platform.configure(CConfig)

HAS_CLOCK_GETTIME = cconfig["HAS_CLOCK_GETTIME"]

CLOCK_REALTIME = cconfig["CLOCK_REALTIME"]
CLOCK_MONOTONIC = cconfig["CLOCK_MONOTONIC"]
CLOCK_MONOTONIC_RAW = cconfig["CLOCK_MONOTONIC_RAW"]
CLOCK_PROCESS_CPUTIME_ID = cconfig["CLOCK_PROCESS_CPUTIME_ID"]
CLOCK_THREAD_CPUTIME_ID = cconfig["CLOCK_THREAD_CPUTIME_ID"]

TIMESPEC = cconfig["TIMESPEC"]

c_clock_gettime = rffi.llexternal("clock_gettime",
    [lltype.Signed, lltype.Ptr(TIMESPEC)], rffi.INT,
    compilation_info=CConfig._compilation_info_, threadsafe=False
)
c_clock_getres = rffi.llexternal("clock_getres",
    [lltype.Signed, lltype.Ptr(TIMESPEC)], rffi.INT,
    compilation_info=CConfig._compilation_info_, threadsafe=False
)

@unwrap_spec(clk_id="c_int")
def clock_gettime(space, clk_id):
    with lltype.scoped_alloc(TIMESPEC) as tp:
        ret = c_clock_gettime(clk_id, tp)
        if ret != 0:
            raise exception_from_errno(space, space.w_IOError)
        return space.wrap(tp.c_tv_sec + tp.c_tv_nsec * 1e-9)

@unwrap_spec(clk_id="c_int")
def clock_getres(space, clk_id):
    with lltype.scoped_alloc(TIMESPEC) as tp:
        ret = c_clock_getres(clk_id, tp)
        if ret != 0:
            raise exception_from_errno(space, space.w_IOError)
        return space.wrap(tp.c_tv_sec + tp.c_tv_nsec * 1e-9)
