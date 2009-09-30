
""" A small helper module for profiling JIT
"""

import time
from pypy.rlib.debug import debug_print

counters="""
TRACING
BACKEND
RUNNING
BLACKHOLE
OPS
RECORDED_OPS
BLACKHOLED_OPS
GUARDS
"""

def _setup():
    names = counters.split()
    for i, name in enumerate(names):
        globals()[name] = i
    global ncounters
    ncounters = len(names)
_setup()

class BaseProfiler(object):
    pass

class EmptyProfiler(BaseProfiler):
    initialized = True
    
    def start(self):
        pass

    def finish(self):
        pass

    def start_tracing(self):
        pass

    def end_tracing(self):
        pass

    def start_backend(self):
        pass

    def end_backend(self):
        pass

    def start_running(self):
        pass

    def end_running(self):
        pass

    def start_blackhole(self):
        pass

    def end_blackhole(self):
        pass

    def count(self, kind, inc=1):
        pass

    def count_ops(self, opnum, kind=OPS):
        pass

class Profiler(BaseProfiler):
    initialized = False
    timer = time.time
    starttime = 0
    t1 = 0
    times = None
    counters = None
    calls = None
    current = None

    def start(self):
        self.starttime = self.timer()
        self.t1 = self.starttime
        self.times = [0, 0, 0, 0]
        self.counters = [0] * ncounters
        self.calls = [[0, 0], [0, 0], [0, 0]]
        self.current = []

    def finish(self):
        self.tk = self.timer()
        self.print_stats()

    def _start(self, event):
        t0 = self.t1
        self.t1 = self.timer()
        if self.current:
            self.times[self.current[-1]] += self.t1 - t0
        self.counters[event] += 1
        self.current.append(event)

    def _end(self, event):
        t0 = self.t1
        self.t1 = self.timer()
        if not self.current:
            debug_print("BROKEN PROFILER DATA!")
            return
        ev1 = self.current.pop()
        if ev1 != event:
            debug_print("BROKEN PROFILER DATA!")
            return
        self.times[ev1] += self.t1 - t0

    def start_tracing(self):   self._start(TRACING)
    def end_tracing(self):     self._end  (TRACING)

    def start_backend(self):   self._start(BACKEND)
    def end_backend(self):     self._end  (BACKEND)

    def start_running(self):   self._start(RUNNING)
    def end_running(self):     self._end  (RUNNING)

    def start_blackhole(self): self._start(BLACKHOLE)
    def end_blackhole(self):   self._end  (BLACKHOLE)

    def count(self, kind, inc=1):
        self.counters[kind] += inc        
    
    def count_ops(self, opnum, kind=OPS):
        from pypy.jit.metainterp.resoperation import rop
        self.counters[kind] += 1
        if opnum == rop.CALL or opnum == rop.OOSEND:
            self.calls[kind-OPS][0] += 1
        elif opnum == rop.CALL_PURE or opnum == rop.OOSEND_PURE:
            self.calls[kind-OPS][1] += 1        

    def print_stats(self):
        cnt = self.counters
        tim = self.times
        calls = self.calls
        lines = ("Tracing:    \t%d\t%f\n" % (cnt[TRACING],   tim[TRACING]) +
                 "Backend:    \t%d\t%f\n" % (cnt[BACKEND],   tim[BACKEND]) +
                 "Running asm:\t%d\t%f\n" % (cnt[RUNNING],   tim[RUNNING]) +
                 "Blackhole:  \t%d\t%f\n" % (cnt[BLACKHOLE], tim[BLACKHOLE]) +
                 "TOTAL:      \t\t%f\n" % (self.tk - self.starttime) + 
                 "ops:           \t%d\n" % cnt[OPS] +
                 "  calls:       \t%d\n" % calls[0][0] +
                 "  pure calls:  \t%d\n" % calls[0][1] +                 
                 "recorded ops:  \t%d\n" % cnt[RECORDED_OPS] +
                 "  calls:       \t%d\n" % calls[1][0] +
                 "  pure calls:  \t%d\n" % calls[1][1] +                 
                 "guards:        \t%d\n" % cnt[GUARDS] +                  
                 "blackholed ops:\t%d\n" % cnt[BLACKHOLED_OPS] +
                 "  calls:       \t%d\n" % calls[2][0] +
                 "  pure calls:  \t%d\n" % calls[2][1]
                 )
        import os
        os.write(2, lines)


class BrokenProfilerData(Exception):
    pass
