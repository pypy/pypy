import py
from pypy.translator.jvm.test.runtest import JvmTest
import pypy.translator.oosupport.test_template.dict as oodict

class TestJvmDict(JvmTest, oodict.BaseTestDict):
    def test_resize_during_iteration(self):
        py.test.skip("test_resize_during_iteration() doesn't work yet")

    def test_tuple_dict(self):
        py.test.skip("fixme: the hashCode method of Records is not good enough")

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
