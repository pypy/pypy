
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
#from pypy.translator.c.test.test_genc import compile

import time, sys

class BaseTestTime(BaseRtypingTest):
    def test_time_time(self):
        def fn():
            return time.time()
        
        t0 = time.time()
        res0 = self.interpret(fn, [])
        t1 = time.time()
        res1 = self.interpret(fn, [])
        assert t0 <= res0 <= t1 <= res1

    def test_time_clock(self):
        def f():
            return time.clock()
        t0 = time.clock()
        time.sleep(0.011)
        t1 = self.interpret(f, [])
        time.sleep(0.011)
        t2 = time.clock()
        time.sleep(0.011)
        t3 = self.interpret(f, [])
        time.sleep(0.011)
        t4 = time.clock()
        time.sleep(0.011)
        t5 = self.interpret(f, [])
        time.sleep(0.011)
        t6 = time.clock()
        # time.clock() and t1() might have a different notion of zero, so
        # we can only subtract two numbers returned by the same function.
        # Moreover they might have different precisions, but it should
        # be at least 0.01 seconds, hence the sleeps.
        assert 0 <= t2-t0
        assert 0 <= t3-t1 <= t4-t0
        assert 0 <= t4-t2 <= t5-t1 <= t6-t0
        assert 0 <= t5-t3 <= t6-t2
        assert 0 <= t6-t4

    def test_time_sleep(self):
        def does_nothing():
            time.sleep(0.19)
        t0 = time.time()
        self.interpret(does_nothing, [])
        t1 = time.time()
        assert t0 <= t1
        assert t1 - t0 >= 0.15

class TestLLType(BaseTestTime, LLRtypeMixin):
    pass

class TestOOType(BaseTestTime, OORtypeMixin):
    pass
