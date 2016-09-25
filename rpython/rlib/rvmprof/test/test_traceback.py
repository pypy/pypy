import re
from rpython.rlib import rvmprof
from rpython.rlib.rvmprof.traceback import traceback
from rpython.translator.interactive import Translation


def test_direct():
    class MyCode:
        pass
    def get_name(mycode):
        raise NotImplementedError
    rvmprof.register_code_object_class(MyCode, get_name)
    #
    @rvmprof.vmprof_execute_code("mycode", lambda code, level: code,
                                 _hack_update_stack_untranslated=True)
    def mainloop(code, level):
        if level > 0:
            mainloop(code, level - 1)
        else:
            traceback(MyCode, my_callback, 42)
    #
    seen = []
    def my_callback(depth, code, arg):
        seen.append((depth, code, arg))
        return 0
    #
    code1 = MyCode()
    rvmprof.register_code(code1, "foo")
    mainloop(code1, 2)
    #
    assert seen == [(0, code1, 42),
                    (1, code1, 42),
                    (2, code1, 42)]

def test_compiled():
    class MyCode:
        pass
    def get_name(mycode):
        raise NotImplementedError
    rvmprof.register_code_object_class(MyCode, get_name)

    @rvmprof.vmprof_execute_code("mycode", lambda code, level: code)
    def mainloop(code, level):
        if level > 0:
            mainloop(code, level - 1)
        else:
            traceback(MyCode, my_callback, 42)

    def my_callback(depth, code, arg):
        print depth, code, arg
        return 0

    def f(argv):
        code1 = MyCode()
        rvmprof.register_code(code1, "foo")
        mainloop(code1, 2)
        return 0

    t = Translation(f, None, gc="boehm")
    t.compile_c()
    stdout = t.driver.cbuilder.cmdexec('')
    r = re.compile("(\d+) [<]MyCode object at 0x([0-9a-f]+)[>] 42\n")
    got = r.findall(stdout)
    addr = got[0][1]
    assert got == [("0", addr), ("1", addr), ("2", addr)]
