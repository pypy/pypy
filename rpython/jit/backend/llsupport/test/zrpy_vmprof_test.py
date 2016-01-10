
import os, py
from rpython.jit.backend.test.support import CCompiledMixin
from rpython.rlib.jit import JitDriver
from rpython.tool.udir import udir
from rpython.translator.translator import TranslationContext
from rpython.jit.backend.detect_cpu import getcpuclass

class CompiledVmprofTest(CCompiledMixin):
    CPUClass = getcpuclass()

    def _get_TranslationContext(self):
        t = TranslationContext()
        t.config.translation.gc = 'incminimark'
        t.config.translation.list_comprehension_operations = True
        return t

    def test_vmprof(self):
        from rpython.rlib import rvmprof

        class MyCode:
            pass
        def get_name(code):
            return 'py:code:52:x'
        try:
            rvmprof.register_code_object_class(MyCode, get_name)
        except rvmprof.VMProfPlatformUnsupported, e:
            py.test.skip(str(e))

        driver = JitDriver(greens = ['code'], reds = ['i', 's', 'num'],
            is_recursive=True)

        @rvmprof.vmprof_execute_code("xcode13", lambda code, num: code)
        def main(code, num):
            return main_jitted(code, num)

        def main_jitted(code, num):
            s = 0
            i = 0
            while i < num:
                driver.jit_merge_point(code=code, i=i, s=s, num=num)
                s += (i << 1)
                if s % 32423423423 == 0 and s > 0 == 0:
                    print s
                i += 1
            return s

        tmpfilename = str(udir.join('test_rvmprof'))

        def f(num):
            code = MyCode()
            rvmprof.register_code(code, get_name)
            fd = os.open(tmpfilename, os.O_WRONLY | os.O_CREAT, 0666)
            period = 0.0001
            rvmprof.enable(fd, period)
            res = main(code, num)
            #assert res == 499999500000
            rvmprof.disable()
            os.close(fd)
            return 0
        
        def check_vmprof_output():
            from vmprof import read_profile
            tmpfile = str(udir.join('test_rvmprof'))
            stats = read_profile(tmpfile)
            t = stats.get_tree()
            import pdb
            pdb.set_trace()

        self.meta_interp(f, [100000000])
        try:
            import vmprof
        except ImportError:
            pass
        else:
            check_vmprof_output()