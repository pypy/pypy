import py, os
import pytest
from rpython.tool.udir import udir
from rpython.rlib import rvmprof
from rpython.translator.c.test.test_genc import compile
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype

@pytest.mark.usefixtures('init')
class RVMProfTest(object):

    ENTRY_POINT_ARGS = ()

    class MyCode(object):
        def __init__(self, name='py:code:0:noname'):
            self.name = name

        def get_name(self):
            return self.name

    @pytest.fixture
    def init(self):
        self.register()
        self.rpy_entry_point = compile(self.entry_point, self.ENTRY_POINT_ARGS)

    def register(self):
        try:
            rvmprof.register_code_object_class(self.MyCode,
                                               self.MyCode.get_name)
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


class RVMProfSamplingTest(RVMProfTest):

    @pytest.fixture
    def init(self, tmpdir):
        self.tmpdir = tmpdir
        self.tmpfile = tmpdir.join('profile.vmprof')
        self.tmpfilename = str(self.tmpfile)
        super(RVMProfSamplingTest, self).init()

    ENTRY_POINT_ARGS = (int, float)
    def entry_point(self, count, period):
        code = self.MyCode('py:code:52:test_enable')
        rvmprof.register_code(code, self.MyCode.get_name)
        fd = os.open(self.tmpfilename, os.O_WRONLY | os.O_CREAT, 0666)
        rvmprof.enable(fd, period)
        res = self.main(code, count)
        rvmprof.disable()
        os.close(fd)
        return res


class TestEnable(RVMProfSamplingTest):

    @rvmprof.vmprof_execute_code("xcode1", lambda self, code, count: code)
    def main(self, code, count):
        print count
        s = 0
        for i in range(count):
            s += (i << 1)
            if s % 2123423423 == 0:
                print s
        return s

    def test(self):
        from vmprof import read_profile
        assert self.entry_point(10**4, 0.9) == 99990000
        assert self.tmpfile.check()
        self.tmpfile.remove()
        #
        assert self.rpy_entry_point(10**8, 0.0001) == 9999999900000000
        assert self.tmpfile.check()
        prof = read_profile(self.tmpfilename)
        tree = prof.get_tree()
        assert tree.name == 'py:code:52:test_enable'
        assert tree.count


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

