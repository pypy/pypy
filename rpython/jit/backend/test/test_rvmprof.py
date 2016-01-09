
from rpython.rlib import jit
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rvmprof import _get_vmprof
from rpython.jit.backend.x86.arch import WORD
from rpython.jit.codewriter.policy import JitPolicy

class BaseRVMProfTest(object):
    def test_one(self):
        visited = []

        def helper():
            stackp = _get_vmprof().cintf.vmprof_address_of_global_stack()[0]
            if stackp:
                # not during tracing
                stack = rffi.cast(rffi.CArrayPtr(lltype.Signed), stackp)
                visited.append(rffi.cast(rffi.CArrayPtr(lltype.Signed), stack[1] - WORD)[0])
            else:
                visited.append(0)

        llfn = llhelper(lltype.Ptr(lltype.FuncType([], lltype.Void)), helper)

        driver = jit.JitDriver(greens=[], reds='auto')

        def f(n):
            i = 0
            while i < n:
                driver.jit_merge_point()
                i += 1
                llfn()

        class Hooks(jit.JitHookInterface):
            def after_compile(self, debug_info):
                self.raw_start = debug_info.asminfo.rawstart

        hooks = Hooks()

        stackp = _get_vmprof().cintf.vmprof_address_of_global_stack()
        stackp[0] = 0 # make it empty
        self.meta_interp(f, [10], policy=JitPolicy(hooks))
        v = set(visited)
        assert 0 in v
        v.remove(0)
        assert len(v) == 1
        assert 0 <= list(v)[0] - hooks.raw_start <= 10*1024
        assert stackp[0] == 0 # make sure we didn't leave anything dangling
