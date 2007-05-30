import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rint import BaseTestRint

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
        
    def test_specializing_int_functions(self):
    	py.test.skip("Error with longlong precision results in 2 == 1")
    	
    def test_float_conversion(self):
        py.test.skip("Unknown opcode cast_longlong_to_float")
        
    def test_float_conversion_implicit(self):
        py.test.skip("Unknown opcode cast_longlong_to_float")
        
    def test_neg_abs_ovf(self):
        py.test.skip("emit doesn't get str or opcode, but None")
        
    def test_protected_div_mod(self):
        py.test.skip("fails because of unusual exception propagation")

    div_mod_iteration_count = 20
