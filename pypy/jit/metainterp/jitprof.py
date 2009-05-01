
""" A small helper module for profiling JIT
"""

import time

TRACING = 0
RUNNING = 1
BLACKHOLE = 2
END_TRACING = 4
END_RUNNING = 5
END_BLACKHOLE = 6

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
    
    def start(self):
        self.t0 = time.clock()
        self.events = []

    def finish(self):
        self.tk = time.clock()
        self.print_stats()

    def start_tracing(self, greenkey=None):
        self.events.append((time.clock(), TRACING))

    def end_tracing(self):
        self.events.append((time.clock(), END_TRACING))

    def start_running(self, greenkey=None):
        self.events.append((time.clock(), RUNNING))

    def end_running(self):
        self.events.append((time.clock(), END_RUNNING))

    def start_blackhole(self, greenkey=None):
        self.events.append((time.clock(), BLACKHOLE))

    def end_blackhole(self):
        self.events.append((time.clock(), END_BLACKHOLE))

    def print_stats(self):
        print "Total: %f" % (self.tk - self.t0)
        #for t, ev in self.events:
        #    if ev == END_TRACING

