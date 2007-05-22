import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rspecialcase import BaseTestRspecialcase

class TestJvmClass(JvmTest, BaseTestRclass):    
    def test_overridden_classattr_as_defaults(self):
        py.test.skip("JVM doesn't support overridden default value yet")

    def test_abstract_method(self):
        class Base(object):
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
        class Root(object):
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
            derived = Derived()
            cls2 = Class2()
            return get_x(derived) + get_x(cls2)
        assert self.interpret(fn, []) == 3

    def test_same_name(self):
        py.test.skip("JVM doesn't support classes with the same name")

    def test_ctr_location(self):
        py.test.skip("Ask cuni if this applies to JVM -I don't think so")


#class TestCliSpecialCase(CliTest, BaseTestRspecialcase):
#    pass
