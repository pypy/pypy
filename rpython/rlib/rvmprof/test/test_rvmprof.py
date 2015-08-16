import py, os
from rpython.tool.udir import udir
from rpython.rlib import rvmprof
from rpython.translator.c.test.test_genc import compile


def test_vmprof_execute_code_1():

    class MyCode:
        pass
    try:
        rvmprof.register_code_object_class(MyCode, lambda code: 'some code')
    except rvmprof.VMProfPlatformUnsupported:
        pass

    @rvmprof.vmprof_execute_code("xcode1", lambda code, num: code)
    def main(code, num):
        print num
        return 42

    def f():
        res = main(MyCode(), 5)
        assert res == 42
        return 0

    assert f() == 0
    fn = compile(f, [])
    assert fn() == 0


def test_vmprof_execute_code_2():

    class MyCode:
        pass
    try:
        rvmprof.register_code_object_class(MyCode, lambda code: 'some code')
    except rvmprof.VMProfPlatformUnsupported:
        pass

    class A:
        pass

    @rvmprof.vmprof_execute_code("xcode2", lambda num, code: code,
                                 result_class=A)
    def main(num, code):
        print num
        return A()

    def f():
        a = main(7, MyCode())
        assert isinstance(a, A)
        return 0

    assert f() == 0
    fn = compile(f, [])
    assert fn() == 0


def test_register_code():

    class MyCode:
        pass
    try:
        rvmprof.register_code_object_class(MyCode, lambda code: 'some code')
    except rvmprof.VMProfPlatformUnsupported, e:
        py.test.skip(str(e))

    @rvmprof.vmprof_execute_code("xcode1", lambda code, num: code)
    def main(code, num):
        print num
        return 42

    def f():
        code = MyCode()
        rvmprof.register_code(code, lambda code: 'some code')
        res = main(code, 5)
        assert res == 42
        return 0

    assert f() == 0
    fn = compile(f, [])
    assert fn() == 0


def test_enable():

    class MyCode:
        pass
    def get_name(code):
        return 'py:code:52:x'
    try:
        rvmprof.register_code_object_class(MyCode, get_name)
    except rvmprof.VMProfPlatformUnsupported, e:
        py.test.skip(str(e))

    @rvmprof.vmprof_execute_code("xcode1", lambda code, num: code)
    def main(code, num):
        print num
        return 42

    tmpfilename = str(udir.join('test_rvmprof'))

    def f():
        code = MyCode()
        rvmprof.register_code(code, get_name)
        fd = os.open(tmpfilename, os.O_WRONLY | os.O_CREAT, 0666)
        rvmprof.enable(fd, 0.5)
        res = main(code, 5)
        assert res == 42
        rvmprof.disable()
        os.close(fd)
        return 0

    assert f() == 0
    assert os.path.exists(tmpfilename)
    fn = compile(f, [], gcpolicy="minimark")
    os.unlink(tmpfilename)
    assert fn() == 0
    assert os.path.exists(tmpfilename)
