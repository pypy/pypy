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
#        py.test.skip("needs thread-locals in the JIT, which is only available "
#                     "after translation")
        visited = []

        def helper():
            trace = []
            stack = cintf.vmprof_tl_stack.getraw()
            while stack:
                trace.append((stack.c_kind, stack.c_value))
                stack = stack.c_next
            visited.append(trace)

        llfn = llhelper(lltype.Ptr(lltype.FuncType([], lltype.Void)), helper)

        driver = jit.JitDriver(greens=['code'], reds='auto')

        class CodeObj(object):
            def __init__(self, name):
                self.name = name

        def get_code_fn(codes, code, arg):
            return code

        def get_name(code):
            return "foo"

        _get_vmprof().use_weaklist = False
        register_code_object_class(CodeObj, get_name)

        @vmprof_execute_code("main", get_code_fn,
                             _hack_update_stack_untranslated=True)
        def f(codes, code, n):
            i = 0
            while i < n:
                driver.jit_merge_point(code=code)
                if code.name == "main":
                    f(codes, codes[1], 5)
                else:
                    llfn()
                i += 1

        def main(n):
            codes = [CodeObj("main"), CodeObj("not main")]
            for code in codes:
                register_code(code, get_name)
            return f(codes, codes[0], n)

        class Hooks(jit.JitHookInterface):
            def after_compile(self, debug_info):
                self.raw_start = debug_info.asminfo.rawstart

        hooks = Hooks()

        null = lltype.nullptr(cintf.VMPROFSTACK)
        cintf.vmprof_tl_stack.setraw(null)
        self.meta_interp(main, [10], policy=JitPolicy(hooks))
        print visited
        #v = set(visited)
        #assert 0 in v
        #v.remove(0)
        #assert len(v) == 1
        #assert 0 <= list(v)[0] - hooks.raw_start <= 10*1024
        #assert cintf.vmprof_tl_stack.getraw() == null
        # ^^^ make sure we didn't leave anything dangling
