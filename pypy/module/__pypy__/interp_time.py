from __future__ import with_statement
import sys

from pypy.interpreter.error import exception_from_errno
from pypy.interpreter.gateway import unwrap_spec
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo

if sys.platform == 'linux2':
    libraries = ["rt"]
else:
    libraries = []


class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=["time.h"],
        libraries=libraries,
    )

    HAS_CLOCK_GETTIME = rffi_platform.Has('clock_gettime')

    CLOCK_REALTIME = rffi_platform.DefinedConstantInteger("CLOCK_REALTIME")
    CLOCK_MONOTONIC = rffi_platform.DefinedConstantInteger("CLOCK_MONOTONIC")
    CLOCK_MONOTONIC_RAW = rffi_platform.DefinedConstantInteger("CLOCK_MONOTONIC_RAW")
    CLOCK_PROCESS_CPUTIME_ID = rffi_platform.DefinedConstantInteger("CLOCK_PROCESS_CPUTIME_ID")
    CLOCK_THREAD_CPUTIME_ID = rffi_platform.DefinedConstantInteger("CLOCK_THREAD_CPUTIME_ID")

cconfig = rffi_platform.configure(CConfig)

HAS_CLOCK_GETTIME = cconfig["HAS_CLOCK_GETTIME"]

CLOCK_REALTIME = cconfig["CLOCK_REALTIME"]
CLOCK_MONOTONIC = cconfig["CLOCK_MONOTONIC"]
CLOCK_MONOTONIC_RAW = cconfig["CLOCK_MONOTONIC_RAW"]
CLOCK_PROCESS_CPUTIME_ID = cconfig["CLOCK_PROCESS_CPUTIME_ID"]
CLOCK_THREAD_CPUTIME_ID = cconfig["CLOCK_THREAD_CPUTIME_ID"]

if HAS_CLOCK_GETTIME:
    #redo it for timespec
    CConfig.TIMESPEC = rffi_platform.Struct("struct timespec", [
        ("tv_sec", rffi.TIME_T),
        ("tv_nsec", rffi.LONG),
    ])
    cconfig = rffi_platform.configure(CConfig)
    TIMESPEC = cconfig['TIMESPEC']

    c_clock_gettime = rffi.llexternal("clock_gettime",
        [lltype.Signed, lltype.Ptr(TIMESPEC)], rffi.INT,
        compilation_info=CConfig._compilation_info_, releasegil=False
    )
    c_clock_getres = rffi.llexternal("clock_getres",
        [lltype.Signed, lltype.Ptr(TIMESPEC)], rffi.INT,
        compilation_info=CConfig._compilation_info_, releasegil=False
    )

    @unwrap_spec(clk_id="c_int")
    def clock_gettime(space, clk_id):
        with lltype.scoped_alloc(TIMESPEC) as tp:
            ret = c_clock_gettime(clk_id, tp)
            if ret != 0:
                raise exception_from_errno(space, space.w_IOError)
            return space.wrap(int(tp.c_tv_sec) + 1e-9 * int(tp.c_tv_nsec))

    @unwrap_spec(clk_id="c_int")
    def clock_getres(space, clk_id):
        with lltype.scoped_alloc(TIMESPEC) as tp:
            ret = c_clock_getres(clk_id, tp)
            if ret != 0:
                raise exception_from_errno(space, space.w_IOError)
            return space.wrap(int(tp.c_tv_sec) + 1e-9 * int(tp.c_tv_nsec))
