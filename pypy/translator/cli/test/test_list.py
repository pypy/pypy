import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rlist import BaseTestRlist

class TestCliList(CliTest, BaseTestRlist):
    def test_recursive(self):
        py.test.skip("CLI doesn't support recursive lists")
