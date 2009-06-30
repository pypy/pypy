import py
from pypy.translator.jvm.test.runtest import JvmTest
import pypy.translator.oosupport.test_template.dict as oodict

class TestJvmDict(JvmTest, oodict.BaseTestDict):
    def test_invalid_iterator(self):
        py.test.skip("test_invalid_iterator() doesn't work yet")

    def test_recursive(self):
        py.test.skip("JVM doesn't support recursive dicts")

    def test_None_set(self):
        def fn(k):
            m = {k:None}
            del m[k]
            return 22
        assert self.interpret(fn, [5]) == 22

class TestJvmEmptyDict(JvmTest, oodict.BaseTestEmptyDict):
    pass

class TestJvmConstantDict(JvmTest, oodict.BaseTestConstantDict):
    pass
