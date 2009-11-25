import os
import time
import py

from pypy.translator.jvm.test.runtest import JvmTest

class TestPrimitive(JvmTest):

    def test_time_time(self):
        def fn():
            return time.time()
        t1 = self.interpret(fn, [])
        t2 = self.interpret(fn, [])
        assert t1 <= t2
