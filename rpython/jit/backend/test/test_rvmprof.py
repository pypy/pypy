import py
from rpython.rlib import jit
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rvmprof import cintf, vmprof_execute_code, register_code,\
    register_code_object_class, _get_vmprof
from rpython.jit.backend.x86.arch import WORD
from rpython.jit.codewriter.policy import JitPolicy

class BaseRVMProfTest(object):
    def test_one(self):
        py.test.skip("needs thread-locals in the JIT, which is only available "
                     "after translation")
        visited = []

        def helper():
            stack = cintf.vmprof_tl_stack.getraw()
            print stack
            if stack:
                # not during tracing
                visited.append(stack.c_value)
            else:
                visited.append(0)

        llfn = llhelper(lltype.Ptr(lltype.FuncType([], lltype.Void)), helper)

        driver = jit.JitDriver(greens=['code'], reds='auto')

        class CodeObj(object):
            pass

        def get_code_fn(code, arg):
            return code

        def get_name(code):
            return "foo"

        register_code_object_class(CodeObj, get_name)

        @vmprof_execute_code("main", get_code_fn)
        def f(code, n):
            i = 0
            while i < n:
                driver.jit_merge_point(code=code)
                i += 1
                llfn()

        def main(n):
            cintf.vmprof_tl_stack.setraw(null)   # make it empty
            vmprof = _get_vmprof()
            code = CodeObj()
            register_code(code, get_name)
            return f(code, n)

        class Hooks(jit.JitHookInterface):
            def after_compile(self, debug_info):
                self.raw_start = debug_info.asminfo.rawstart

        hooks = Hooks()

        null = lltype.nullptr(cintf.VMPROFSTACK)
        self.meta_interp(main, [10], policy=JitPolicy(hooks))
        print visited
        #v = set(visited)
        #assert 0 in v
        #v.remove(0)
        #assert len(v) == 1
        #assert 0 <= list(v)[0] - hooks.raw_start <= 10*1024
        #assert cintf.vmprof_tl_stack.getraw() == null
        # ^^^ make sure we didn't leave anything dangling
