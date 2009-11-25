import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rrange import BaseTestRrange

class TestCliRange(CliTest, BaseTestRrange):
    def test_rlist_range(self):
        pass # it doesn't make sense here
