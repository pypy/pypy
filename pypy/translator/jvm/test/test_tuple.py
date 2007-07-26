import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rtuple import BaseTestRtuple

class TestJvmTuple(JvmTest, BaseTestRtuple):
    def test_builtin_records(self):
        def fn(x, y):
            return x, y
        res = self.interpret(fn, [1.0, 1])
        assert res.item0 == 1.0 and res.item1 == 1
        res = self.interpret(fn, [1.0, 1.0])
        assert res.item0 == 1.0 and res.item1 == 1.0
    
    #v116 = oosend(('ll_contains'), (<pypy.rpython.ootypesy...7cc5f0>), i_0)
    # Arg 01: Exception in thread "main" java.lang.VerifyError
    def test_constant_tuple_contains(self):
        py.test.skip("VerifyError - Incompatible object argumemt")
        
    def test_constant_tuple_contains2(self):
        py.test.skip("VerifyError - Incompatible object argumemt")
        
    def test_constant_unichar_tuple_contains(self):
        py.test.skip("VerifyError - Incompatible object argumemt")
