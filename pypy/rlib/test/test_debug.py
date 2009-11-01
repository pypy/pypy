
import py
from pypy.rlib.debug import check_annotation, make_sure_not_resized
from pypy.rlib.debug import debug_print, debug_start, debug_stop
from pypy.rlib.debug import have_debug_prints
from pypy.rlib import debug
from pypy.rpython.test.test_llinterp import interpret

def test_check_annotation():
    class Error(Exception):
        pass
    
    def checker(ann, bk):
        from pypy.annotation.model import SomeList, SomeInteger
        if not isinstance(ann, SomeList):
            raise Error()
        if not isinstance(ann.listdef.listitem.s_value, SomeInteger):
            raise Error()
    
    def f(x):
        result = [x]
        check_annotation(result, checker)
        return result

    interpret(f, [3])

    def g(x):
        check_annotation(x, checker)
        return x

    py.test.raises(Error, "interpret(g, [3])")

def test_make_sure_not_resized():
    from pypy.annotation.listdef import TooLateForChange
    def f():
        result = [1,2,3]
        make_sure_not_resized(result)
        result.append(4)
        return len(result)

    py.test.raises(TooLateForChange, interpret, f, [], 
                   list_comprehension_operations=True)


class DebugTests:

    def test_debug_print_start_stop(self):
        def f(x):
            debug_start("mycat")
            debug_print("foo", 2, "bar", x)
            debug_stop("mycat")
            return have_debug_prints()

        try:
            debug._log = dlog = debug.DebugLog()
            res = f(3)
            assert res == True
        finally:
            debug._log = None
        assert dlog == [
            ("mycat", [
                ('debug_print', 'foo', 2, 'bar', 3),
                ]),
            ]

        try:
            debug._log = dlog = debug.DebugLog()
            res = self.interpret(f, [3])
            assert res == True
        finally:
            debug._log = None
        assert dlog == [
            ("mycat", [
                ('debug_print', 'foo', 2, 'bar', 3),
                ]),
            ]


class TestLLType(DebugTests):
    def interpret(self, f, args):
        return interpret(f, args, type_system='lltype')

class TestOOType(DebugTests):
    def interpret(self, f, args):
        return interpret(f, args, type_system='ootype')
