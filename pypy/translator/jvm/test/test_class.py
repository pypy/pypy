import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rclass import BaseTestRclass
from pypy.rpython.test.test_rspecialcase import BaseTestRspecialcase

class TestJvmClass(JvmTest, BaseTestRclass):    
    pass

#class TestCliSpecialCase(CliTest, BaseTestRspecialcase):
#    pass
