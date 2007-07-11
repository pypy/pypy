import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rfloat import BaseTestRfloat

class TestJvmFloat(JvmTest, BaseTestRfloat):
    def test_parse_float(self):
        py.test.skip("JVM backend unknown opcode ooparse_float with ll_str_0")
#        ex = ['', '    ', '0', '1', '-1.5', '1.5E2', '2.5e-1', ' 0 ', '?']
#        def fn(i):
#            s = ex[i]
#            try:
#                return float(s)
#            except ValueError:
#                return -999.0
#        
#        for i in range(len(ex)):
#            expected = fn(i)
#            res = self.interpret(fn, [i])
#            assert res == expected
    
    #Works, answer is correct, but not of type r_longlong.
    def test_longlong_conversion(self):
        py.test.skip("JVM backend unknown opcode cast_float_to_longlong")
                
    def test_float_constant_conversions(self):
        py.test.skip("JVM backend lacks appropriate percision; 42.000000614400001 == 42.0")
    
    #The JVM doesn't even have uints
    def test_from_r_uint(self):
        py.test.skip("JVM backend lacks appropriate percision")
    
    #The jvm doesn't even have uints
    def test_to_r_uint(self):
        py.test.skip("JVM backend lacks appropriate percision")
        
