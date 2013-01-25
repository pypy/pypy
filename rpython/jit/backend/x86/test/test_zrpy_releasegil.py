from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.jit import dont_look_inside
from rpython.jit.metainterp.optimizeopt import ALL_OPTS_NAMES

from rpython.rlib.libffi import CDLL, types, ArgChain, clibffi
from rpython.rtyper.lltypesystem.ll2ctypes import libc_name
from rpython.rtyper.annlowlevel import llhelper

from rpython.jit.backend.x86.test.test_zrpy_gc import BaseFrameworkTests
from rpython.jit.backend.x86.test.test_zrpy_gc import check


class ReleaseGILTests(BaseFrameworkTests):
    compile_kwds = dict(enable_opts=ALL_OPTS_NAMES, thread=True)


class TestShadowStack(ReleaseGILTests):
    gcrootfinder = "shadowstack"

class TestAsmGcc(ReleaseGILTests):
    gcrootfinder = "asmgcc"
