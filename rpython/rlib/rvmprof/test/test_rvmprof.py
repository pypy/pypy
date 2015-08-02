from rpython.rlib.rvmprof import get_vmprof, vmprof_execute_code
from rpython.translator.c.test.test_genc import compile


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
