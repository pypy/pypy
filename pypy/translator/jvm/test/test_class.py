import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.class_ import BaseTestClass, BaseTestSpecialcase

class TestJvmClass(JvmTest, BaseTestClass):    
    def test_overridden_classattr_as_defaults(self):
        py.test.skip("JVM doesn't support overridden default value yet")

    def test_method_void_arg(self):
        class Space:
            def __init__(self):
                self.x = 40
            def _freeze_(self):
                return True
        space = Space()

        class MyClass:
            def foo(self, space, x):
                return space.x + x

        def fn(x):
            obj = MyClass()
            return obj.foo(space, x)

        assert self.interpret(fn, [2]) == 42
            
    def test_specialize_methods(self):
        py.test.skip('ABSTRACT METHOD FIX: RE-TEST AFTER MERGE')

class TestJvmSpecialCase(JvmTest, BaseTestSpecialcase):
    pass
