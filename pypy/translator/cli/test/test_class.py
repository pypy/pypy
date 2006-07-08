import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rclass import BaseTestRclass

class TestCliClass(CliTest, BaseTestRclass):
    def test_abstract_method(self):
        class Base:
            pass
        class A(Base):
            def f(self, x):
                return x+1
        class B(Base):
            def f(self, x):
                return x+2
        def call(obj, x):
            return obj.f(x)
        def fn(x):
            a = A()
            b = B()
            return call(a, x) + call(b, x)
        assert self.interpret(fn, [0]) == 3
