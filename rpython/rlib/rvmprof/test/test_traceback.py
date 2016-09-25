from rpython.rlib import rvmprof
from rpython.rlib.rvmprof.traceback import traceback


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
