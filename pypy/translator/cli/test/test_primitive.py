import os
import time

from pypy.translator.cli.test.runtest import CliTest

class TestPrimitive(CliTest):

    def test_time_time(self):
        def fn():
            return time.time()
        t1 = self.interpret(fn, [])
        t2 = self.interpret(fn, [])
        assert t1 <= t2
