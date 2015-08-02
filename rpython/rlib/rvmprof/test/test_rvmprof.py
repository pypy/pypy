from rpython.rlib.rvmprof import get_vmprof, vmprof_execute_code


def test_vmprof_execute_code_1():

    class MyCode:
        pass
    get_vmprof().register_code_object_class(MyCode, lambda code: 'some code')

    @vmprof_execute_code(lambda code, num: code)
    def main(code, num):
        print num

    main(MyCode(), 5)
