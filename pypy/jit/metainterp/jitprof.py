
""" A small helper module for profiling JIT
"""

import time

TRACING = 0
RUNNING = 1
BLACKHOLE = 2
LAST_START = 2
END_TRACING = 3
END_RUNNING = 4
END_BLACKHOLE = 5

class EmptyProfiler(object):
    initialized = False
    
    def start(self):
        pass

    def finish(self):
        pass
    
    def start_normal(self, greenkey=None):
        pass

    def end_normal(self):
        pass

    def start_tracing(self, greenkey=None):
        pass

    def end_tracing(self):
        pass

    def start_running(self, greenkey=None):
        pass

    def end_running(self):
        pass

    def start_blackhole(self, greenkey=None):
        pass

    def end_blackhole(self):
        pass

class Profiler(object):
    initialized = False
    timer = time.clock
    
    def start(self):
        self.t0 = self.timer()
        self.events = []

    def finish(self):
        self.tk = self.timer()
        self.summarize()
        self.print_stats()

    def start_tracing(self, greenkey=None):
        self.events.append((self.timer(), TRACING))

    def end_tracing(self):
        self.events.append((self.timer(), END_TRACING))

    def start_running(self, greenkey=None):
        self.events.append((self.timer(), RUNNING))

    def end_running(self):
        self.events.append((self.timer(), END_RUNNING))

    def start_blackhole(self, greenkey=None):
        self.events.append((self.timer(), BLACKHOLE))

    def end_blackhole(self):
        self.events.append((self.timer(), END_BLACKHOLE))

    def summarize(self):
        current = []
        t = 0
        times = [0, 0, 0]
        for t0, ev in self.events:
            if ev <= LAST_START:
                if current:
                    times[current[-1]] += t0 - t
                current.append(ev)
            else:
                times[current.pop()] += t0 - t
            t = t0
        self.trace_time = times[TRACING]
        self.run_time = times[RUNNING]
        self.blackhole_time = times[BLACKHOLE]

    def print_stats(self):
        print "Total: %f" % (self.tk - self.t0)
        print "Tracing: %f" % self.trace_time
        print "Running: %f" % self.run_time
        print "Blackhole: %f" % self.blackhole_time

