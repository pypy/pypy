import py
from rpython.rlib.rvmprof import get_vmprof, vmprof_execute_code
from rpython.translator.c.test.test_genc import compile
from rpython.jit.backend import detect_cpu

if detect_cpu.autodetect() != detect_cpu.MODEL_X86_64:
    py.test.skip("rvmprof only supports x86-64 CPUs for now")


def test_vmprof_execute_code_1():

    class MyCode:
        pass
    get_vmprof().register_code_object_class(MyCode, lambda code: 'some code')

    @vmprof_execute_code("xcode1", lambda code, num: code)
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
    get_vmprof().register_code_object_class(MyCode, lambda code: 'some code')

    class A:
        pass

    @vmprof_execute_code("xcode2", lambda num, code: code, result_class=A)
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
    get_vmprof().register_code_object_class(MyCode, lambda code: 'some code')

    @vmprof_execute_code("xcode1", lambda code, num: code)
    def main(code, num):
        print num
        return 42

    def f():
        code = MyCode()
        get_vmprof().register_code(code, 'some code')
        res = main(code, 5)
        assert res == 42
        return 0

    assert f() == 0
    fn = compile(f, [])
    assert fn() == 0
