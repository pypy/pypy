import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.operations import BaseTestOperations

# ====> ../../oosupport/test_template/operations.py

class TestOperations(JvmTest, BaseTestOperations):

    def test_eq(self):
        py.test.skip("Str to long is not implemented, needed for test")
        
    def test_ne(self):
        py.test.skip("Str to long is not implemented, needed for test")
        
    def test_ge(self):
        py.test.skip("Str to long is not implemented, needed for test")
        
    def test_le(self):
        py.test.skip("Str to long is not implemented, needed for test")
        
    def test_and_not(self):
        py.test.skip("VerifyError happens. Accessing uninit reg")
        
    def test_modulo(self):
        py.test.skip("Backend lacks appropriate precision")
        
    def test_operations(self):
        py.test.skip("Backend lacks appropriate precision")
        
    def test_abs(self):
        py.test.skip("Backend lacks appropriate precision")
        
    def test_is_true(self):
        py.test.skip("VerifyError happens. Accessing uninit reg")
        
    def test_is_early_constant(self):
        py.test.skip("Unknown opcode is_early_constant")
        
