import py
from pypy.translator.jvm.test.runtest import JvmTest
import pypy.translator.oosupport.test_template.dict as oodict

class TestJvmDict(JvmTest, oodict.BaseTestDict):
    def test_invalid_iterator(self):
        py.test.skip("test_invalid_iterator() doesn't work yet")

    def test_recursive(self):
        py.test.skip("JVM doesn't support recursive dicts")

class TestJvmEmptyDict(JvmTest, oodict.BaseTestEmptyDict):
    pass

class TestJvmConstantDict(JvmTest, oodict.BaseTestConstantDict):
    pass
