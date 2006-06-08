import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rpbc import BaseTestRPBC

class TestCliPBC(CliTest, BaseTestRPBC):
    def test_call_memoized_cache(self):
        py.test.skip("gencli doesn't support recursive constants, yet")        

    def test_multiple_specialized_functions(self):
        py.test.skip("CLI doesn't support string, yet")

    def test_specialized_method_of_frozen(self):
        py.test.skip("CLI doesn't support string, yet")

    def test_specialized_method(self):
        py.test.skip("CLI doesn't support string, yet")
