import py
from pypy.translator.js.test.runtest import JsTest
from pypy.rpython.test.test_exception import BaseTestException
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rtuple import BaseTestRtuple
from pypy.rpython.test.test_rstr import BaseTestRstr

class TestJsException(JsTest, BaseTestException):
    pass

# ====> ../../../rpython/test/test_rclass.py

class TestJsClass(JsTest, BaseTestRclass):
    def test___class___attribute(self):
        class Base(object): pass
        class A(Base): pass
        class B(Base): pass
        class C(A): pass
        def seelater():
            C()
        def f(n):
            if n == 1:
                x = A()
            else:
                x = B()
            y = B()
            result = x.__class__, y.__class__
            seelater()
            return result
        def g():
            cls1, cls2 = f(1)
            return cls1 is A, cls2 is B

        res = self.interpret(g, [])
        assert res[0]
        assert res[1]

    def test_mixin(self):
        class Mixin(object):
            _mixin_ = True

            def m(self, v):
                return v

        class Base(object):
            pass

        class A(Base, Mixin):
            pass

        class B(Base, Mixin):
            pass

        class C(B):
            pass

        def f():
            a = A()
            v0 = a.m(2)
            b = B()
            v1 = b.m('x')
            c = C()
            v2 = c.m('y')
            return v0, v1, v2

        res = self.interpret(f, [])
        assert isinstance(res[0], int)

    def test_hash_preservation(self):
        py.test.skip("Broken")

    def test_issubclass_type(self):
        py.test.skip("Broken")

    def test___class___attribute(self):
        py.test.skip("Broken")

    def test_circular_hash_initialization(self):
        py.test.skip("Broken")

    def test_type(self):
        py.test.skip("Broken")
    
    #def test_isinstance(self):
    #    py.test.skip("WIP")

