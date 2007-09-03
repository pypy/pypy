import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.class_ import BaseTestClass, BaseTestSpecialcase

class TestJvmClass(JvmTest, BaseTestClass):    
    def test_overridden_classattr_as_defaults(self):
        py.test.skip("JVM doesn't support overridden default value yet")

class TestJvmSpecialCase(JvmTest, BaseTestSpecialcase):
    pass
