import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rspecialcase import BaseTestRspecialcase

class TestJvmClass(JvmTest, BaseTestRclass):    
    def test_overridden_classattr_as_defaults(self):
        py.test.skip("JVM doesn't support overridden default value yet")

#class TestCliSpecialCase(CliTest, BaseTestRspecialcase):
#    pass
