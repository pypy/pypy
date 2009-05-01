
""" A small helper module for profiling JIT
"""

import time

TRACING = 0
BACKEND = 1
RUNNING = 2
BLACKHOLE = 3

class EmptyProfiler(object):
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

class Profiler(object):
    initialized = False
    timer = time.time
    
    def start(self):
        self.starttime = self.timer()
        self.t1 = self.starttime
        self.times = [0, 0, 0, 0]
        self.current = []

    def finish(self):
        self.tk = self.timer()
        self.print_stats()

    def _start(self, event):
        t0 = self.t1
        self.t1 = self.timer()
        if self.current:
            self.times[self.current[-1]] += self.t1 - t0
        self.current.append(event)

    def _end(self, event):
        t0 = self.t1
        self.t1 = self.timer()
        if not self.current:
            raise BrokenProfilerData
        ev1 = self.current.pop()
        if ev1 != event:
            raise BrokenProfilerData
        self.times[ev1] += self.t1 - t0

    def start_tracing(self):   self._start(TRACING)
    def end_tracing(self):     self._end  (TRACING)

    def start_backend(self):   self._start(BACKEND)
    def end_backend(self):     self._end  (BACKEND)

    def start_running(self):   self._start(RUNNING)
    def end_running(self):     self._end  (RUNNING)

    def start_blackhole(self): self._start(BLACKHOLE)
    def end_blackhole(self):   self._end  (BLACKHOLE)

    def print_stats(self):
        print "Tracing:     %f" % self.times[TRACING]
        print "Backend:     %f" % self.times[BACKEND]
        print "Running asm: %f" % self.times[RUNNING]
        print "Blackhole:   %f" % self.times[BLACKHOLE]
        print "TOTAL:       %f" % (self.tk - self.starttime)


class BrokenProfilerData(Exception):
    pass
