import py, os
from rpython.tool.udir import udir
from rpython.rlib import rvmprof
from rpython.translator.c.test.test_genc import compile
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.nonconst import NonConstant
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype

class RVMProfTest:

    class MyCode: pass

    def setup_method(self, meth):
        self.register()
        self.rpy_entry_point = compile(self.entry_point, [])

    def register(self):
        try:
            rvmprof.register_code_object_class(self.MyCode,
                                               lambda code: 'some code')
        except rvmprof.VMProfPlatformUnsupported as e:
            py.test.skip(str(e))


class TestExecuteCode(RVMProfTest):

    def entry_point(self):
        res = self.main(self.MyCode(), 5)
        assert res == 42
        return 0

    @rvmprof.vmprof_execute_code("xcode1", lambda self, code, num: code)
    def main(self, code, num):
        print num
        return 42

    def test(self):
        assert self.entry_point() == 0
        assert self.rpy_entry_point() == 0


class TestResultClass(RVMProfTest):

    class A: pass

    @rvmprof.vmprof_execute_code("xcode2", lambda self, num, code: code,
                                 result_class=A)
    def main(self, num, code):
        print num
        return self.A()

    def entry_point(self):
        a = self.main(7, self.MyCode())
        assert isinstance(a, self.A)
        return 0

    def test(self):
        assert self.entry_point() == 0
        assert self.rpy_entry_point() == 0


class TestRegisterCode(RVMProfTest):
    
    @rvmprof.vmprof_execute_code("xcode1", lambda self, code, num: code)
    def main(self, code, num):
        print num
        return 42

    def entry_point(self):
        code = self.MyCode()
        rvmprof.register_code(code, lambda code: 'some code')
        res = self.main(code, 5)
        assert res == 42
        return 0

    def test(self):
        assert self.entry_point() == 0
        assert self.rpy_entry_point() == 0


def test_enable():

    class MyCode:
        pass
    def get_name(code):
        return 'py:code:52:x'
    try:
        rvmprof.register_code_object_class(MyCode, get_name)
    except rvmprof.VMProfPlatformUnsupported as e:
        py.test.skip(str(e))

    @rvmprof.vmprof_execute_code("xcode1", lambda code, num: code)
    def main(code, num):
        print num
        s = 0
        for i in range(num):
            s += (i << 1)
            if s % 2123423423 == 0:
                print s
        return s

    tmpfilename = str(udir.join('test_rvmprof'))

    def f():
        if NonConstant(False):
            # Hack to give os.open() the correct annotation
            os.open('foo', 1, 1)
        code = MyCode()
        rvmprof.register_code(code, get_name)
        fd = os.open(tmpfilename, os.O_WRONLY | os.O_CREAT, 0666)
        if we_are_translated():
            num = 100000000
            period = 0.0001
        else:
            num = 10000
            period = 0.9
        rvmprof.enable(fd, period)
        res = main(code, num)
        #assert res == 499999500000
        rvmprof.disable()
        os.close(fd)
        return 0

    def check_profile(filename):
        from vmprof import read_profile

        prof = read_profile(filename)
        assert prof.get_tree().name.startswith("py:")
        assert prof.get_tree().count

    assert f() == 0
    assert os.path.exists(tmpfilename)
    fn = compile(f, [], gcpolicy="minimark")
    assert fn() == 0
    try:
        check_profile(tmpfilename)
    finally:
        assert os.path.exists(tmpfilename)
        os.unlink(tmpfilename)

def test_native():
    eci = ExternalCompilationInfo(compile_extra=['-g','-O0'],
            separate_module_sources=["""
            RPY_EXTERN int native_func(int d) {
                int j = 0;
                if (d > 0) {
                    return native_func(d-1);
                } else {
                    for (int i = 0; i < 42000; i++) {
                        j += d;
                    }
                }
                return j;
            }
            """])

    native_func = rffi.llexternal("native_func", [rffi.INT], rffi.INT,
                                  compilation_info=eci)

    class MyCode:
        pass
    def get_name(code):
        return 'py:code:52:x'

    try:
        rvmprof.register_code_object_class(MyCode, get_name)
    except rvmprof.VMProfPlatformUnsupported as e:
        py.test.skip(str(e))

    @rvmprof.vmprof_execute_code("xcode1", lambda code, num: code)
    def main(code, num):
        if num > 0:
            return main(code, num-1)
        else:
            return native_func(100)

    tmpfilename = str(udir.join('test_rvmprof'))

    def f():
        if NonConstant(False):
            # Hack to give os.open() the correct annotation
            os.open('foo', 1, 1)
        code = MyCode()
        rvmprof.register_code(code, get_name)
        fd = os.open(tmpfilename, os.O_RDWR | os.O_CREAT, 0666)
        num = 10000
        period = 0.0001

        rvmprof.enable(fd, period, native=1)
        for i in range(num):
            res = main(code, 3)
        rvmprof.disable()
        os.close(fd)
        return 0

    def check_profile(filename):
        from vmprof import read_profile
        from vmprof.show import PrettyPrinter

        prof = read_profile(filename)
        tree = prof.get_tree()
        p = PrettyPrinter()
        p._print_tree(tree)
        def walk(tree, symbols):
            symbols.append(tree.name)
            if len(tree.children) == 0:
                return
            for child in tree.children.values():
                walk(child, symbols)
        symbols = []
        walk(tree, symbols)
        not_found = ['n:native_func']
        for sym in symbols:
            for i,name in enumerate(not_found):
                if sym.startswith(name):
                    del not_found[i]
                    break
        assert not_found == []

    fn = compile(f, [], gcpolicy="incminimark", lldebug=True)
    assert fn() == 0
    try:
        check_profile(tmpfilename)
    finally:
        assert os.path.exists(tmpfilename)
        os.unlink(tmpfilename)

