from pypy.translator.jvm.test.runtest import JvmTest
import pypy.translator.oosupport.test_template.dict as oodict

class TestJvmDict(JvmTest, oodict.BaseTestDict):
    pass

class TestJvmEmptyDict(JvmTest, oodict.BaseTestEmptyDict):
    pass

class TestJvmConstantDict(JvmTest, oodict.BaseTestConstantDict):
    pass


