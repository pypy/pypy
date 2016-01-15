import py
from rpython.rlib import jit
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rvmprof import cintf
from rpython.jit.backend.x86.arch import WORD
from rpython.jit.codewriter.policy import JitPolicy

class BaseRVMProfTest(object):
    def test_one(self):
        py.test.skip("needs thread-locals in the JIT, which is only available "
                     "after translation")
        visited = []

        def helper():
            stack = cintf.vmprof_tl_stack.getraw()
            if stack:
                # not during tracing
                visited.append(stack.c_value)
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

        null = lltype.nullptr(cintf.VMPROFSTACK)
        cintf.vmprof_tl_stack.setraw(null)   # make it empty
        self.meta_interp(f, [10], policy=JitPolicy(hooks))
        v = set(visited)
        assert 0 in v
        v.remove(0)
        assert len(v) == 1
        assert 0 <= list(v)[0] - hooks.raw_start <= 10*1024
        assert cintf.vmprof_tl_stack.getraw() == null
        # ^^^ make sure we didn't leave anything dangling
