import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.operations import BaseTestOperations

# ====> ../../oosupport/test_template/operations.py

class TestOperations(JvmTest, BaseTestOperations):

    def test_abs(self):
        py.test.skip("Backend lacks appropriate precision")
        
    def test_is_true(self):
        py.test.skip("VerifyError happens. Accessing uninit reg")
        
    def test_is_early_constant(self):
        py.test.skip("Unknown opcode is_early_constant")
        
