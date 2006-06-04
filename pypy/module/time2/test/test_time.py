from pypy.objspace.std import StdObjSpace 
import time

def setup_module(mod): 
    mod.space = StdObjSpace(usemodules=['time2'])

class TestTime: 
    def test_clock(self):
        t0 = time.clock()
        w_t1 = space.appexec([], """(): import time2; return time2.clock()""")
        t2 = time.clock()
        assert t0 <= space.unwrap(w_t1) <= t2

    def XXXtest_time(self):
        t0 = time.time()
        w_t1 = space.appexec([], """(): import time; return time.time()""")
        t2 = time.time()
        assert t0 <= space.unwrap(w_t1) <= t2

    def XXXtest_sleep(self):
        w_sleep = space.appexec([], """(): import time; return time.sleep""")
        t0 = time.time()
        space.call_function(w_sleep, space.wrap(0.3))
        t1 = time.time()
        assert t1-t0 > 0.25
