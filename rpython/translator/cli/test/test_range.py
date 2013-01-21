import py
from rpython.translator.cli.test.runtest import CliTest
from rpython.rtyper.test.test_rrange import BaseTestRrange

class TestCliRange(CliTest, BaseTestRrange):
    def test_rlist_range(self):
        pass # it doesn't make sense here
