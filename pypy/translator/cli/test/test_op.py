import sys
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.oosupport.test_template.operations import BaseTestOperations
from pypy.rlib.rarithmetic import ovfcheck

# ====> ../../oosupport/test_template/operations.py

class TestOperations(CliTest, BaseTestOperations):
    def test_int_div_overflow(self):
        import py
        py.test.skip('fixme!')
        def fn(x, y):
            try:
                return x//y
            except OverflowError:
                return 42
        res = self.interpret(fn, [-sys.maxint-1, -1])
        assert res == 42

