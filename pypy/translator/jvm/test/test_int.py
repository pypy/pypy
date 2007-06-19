import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rint import BaseTestRint

# ====> ../../../rpython/test/test_rint.py

class TestJvmInt(JvmTest, BaseTestRint):
    def test_char_constant(self):
        def dummyfn(i):
            return chr(i)
        res = self.interpret(dummyfn, [ord(' ')])
        assert res == ' '
        # Is the following test supported by JVM?
##        res = self.interpret(dummyfn, [0])
##        assert res == '\0'
        res = self.interpret(dummyfn, [ord('a')])
        assert res == 'a'

    def test_rarithmetic(self):
        pass # does this make more sense in jvm
        
    def test_neg_abs_ovf(self):
        py.test.skip("Unaware how to handle overflow")
        
    def test_protected_div_mod(self):
        py.test.skip("fails because of unusual exception propagation")

    div_mod_iteration_count = 20
