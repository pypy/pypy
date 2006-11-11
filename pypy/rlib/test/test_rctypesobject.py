from pypy.rlib.rctypesobject import *
from pypy.rpython.test.test_llinterp import interpret
from pypy.annotation.policy import AnnotatorPolicy


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
        S1 = RStruct('S1', [('x', rc_int),
                            ('y', RPointer(rc_int))])
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

    def test_fixedarray(self):
        def func():
            a = RFixedArray(rc_int, 10).allocate()
            for i in range(10):
                a.ref(i).set_value(5 * i)
            for i in range(10):
                assert a.ref(i).get_value() == 5 * i
            return a.length
        res = self.do(func)
        assert res == 10

    def test_vararray(self):
        def func():
            a = RVarArray(rc_int).allocate(10)
            for i in range(10):
                a.ref(i).set_value(5 * i)
            for i in range(10):
                assert a.ref(i).get_value() == 5 * i
            return a.length
        res = self.do(func)
        assert res == 10

    def test_vararray_cast(self):
        def func():
            a = RVarArray(rc_int).allocate(10)
            for i in range(10):
                a.ref(i).set_value(100 + 5 * i)
            p = pointer(a.ref(0))
            del a
            assert p.get_contents().get_value() == 100
            a1 = RVarArray(rc_int).fromitem(p.get_contents(), 8)
            del p
            for i in range(8):
                a1.ref(i).get_value() == 100 + 5 * i
            return a1.length
        res = self.do(func)
        assert res == 8

    def test_char_p(self):
        def func():
            p = rc_char_p.allocate()
            s = ''
            for i in range(65, 91):
                s += chr(i)
            p.set_value(s)
            del s
            s = p.get_value()
            for i in range(26):
                assert ord(s[i]) == 65 + i
            return len(s)
        res = self.do(func)
        assert res == 26


class TestLLInterpreted(TestBasic):
    POLICY = AnnotatorPolicy()
    POLICY.allow_someobjects = False

    def do(self, func):
        return interpret(func, [], policy=self.POLICY)
