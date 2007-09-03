import py
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rspecialcase import BaseTestRspecialcase

class BaseTestClass(BaseTestRclass):    
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

    def test_abstract_method2(self):
        class Root:
            pass
        class Class1(Root):
            pass
        class Derived(Class1):
            x = 1
        class Class2(Root):
            x = 2
        def get_x(obj):
            return obj.x
        def fn():
            a = Derived()
            b = Class2()
            return get_x(a) + get_x(b)
        assert self.interpret(fn, []) == 3

    def test_same_name(self):
        class A:
            def __init__(self, x):
                self.x = x
        B=A
        class A:
            def __init__(self, y):
                self.y = y
        assert A is not B
        assert A.__name__ == B.__name__
        def fn(x, y):
            obj1 = B(x)
            obj2 = A(y)
            return obj1.x + obj2.y
        assert self.interpret(fn, [1, 2]) == 3

    def test_ctr_location(self):
        class A:
            _annspecialcase_ = "specialize:ctr_location"
            def __init__(self, x):
                self.x = x
        def fn(x, y):
            a = A(x)
            b = A(y)
            return a.x + b.x
        assert self.interpret(fn, [1, 2]) == 3

class BaseTestSpecialcase(BaseTestRspecialcase):
    pass
