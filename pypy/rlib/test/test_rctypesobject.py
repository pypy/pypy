from pypy.rlib.rctypesobject import *
from pypy.rpython.test.test_llinterp import interpret


class TestBasic:

    def do(self, func):
        return func()

    def test_primitive(self):
        def func():
            x = rc_int.allocate()
            assert x.get_value() == 0
            x.set_value(17)
            return x.get_value()
        res = self.do(func)
        assert res == 17

    def test_ptr(self):
        def func():
            x = rc_int.allocate()
            p1 = pointer(x)
            p2 = pointer(x)
            x.set_value(17)
            assert p1.get_contents().get_value() == 17
            p2.get_contents().set_value(18)
            assert x.get_value() == 18
            del x
            return p1.get_contents().get_value()
        res = self.do(func)
        assert res == 18

    def test_struct(self):
        S1 = makeRStruct('S1', [('x', rc_int),
                                ('y', makeRPointer(rc_int))])
        def func():
            x = rc_int.allocate()
            x.set_value(42)
            s = S1.allocate()
            s.ref_x().set_value(12)
            s.ref_y().set_contents(x)
            assert s.ref_x().get_value() == 12
            return s.ref_y().get_contents().get_value()
        res = self.do(func)
        assert res == 42

    def test_copyfrom(self):
        def func():
            x1 = rc_int.allocate()
            x1.set_value(101)
            p1 = pointer(x1)
            x2 = rc_int.allocate()
            x2.set_value(202)
            p2 = pointer(x2)
            del x1, x2
            p1.copyfrom(p2)
            assert p1.get_contents().sameaddr(p2.get_contents())
            p1.get_contents().set_value(303)
            assert p2.get_contents().get_value() == 303
            del p2
            return p1.get_contents().get_value()
        res = self.do(func)
        assert res == 303


class TestLLInterpreted(TestBasic):
    
    def do(self, func):
        return interpret(func, [])
