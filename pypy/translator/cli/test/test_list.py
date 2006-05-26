import py

from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rlist import BaseTestRlist

class TestCliList(CliTest, BaseTestRlist):
    def test_recursive(self):
        py.test.skip("CLI doesn't support recursive lists")

    def test_list_comparestr(self):
        py.test.skip("CLI doesn't support string, yet")

    def test_not_a_char_list_after_all(self):
        py.test.skip("CLI doesn't support string, yet")
        
    def test_list_str(self):
        py.test.skip("CLI doesn't support string, yet")

    def test_inst_list(self):
        py.test.skip("CLI doesn't support string, yet")
