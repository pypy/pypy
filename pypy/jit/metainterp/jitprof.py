
""" A small helper module for profiling JIT
"""

import time

TRACING = 0
BACKEND = 1
RUNNING = 2
BLACKHOLE = 3
LAST_START = 3

END_TRACING = 4
END_BACKEND = 5
END_RUNNING = 6
END_BLACKHOLE = 7

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
    timer = time.clock
    
    def start(self):
        self.t0 = self.timer()
        self.events = []

    def finish(self):
        self.tk = self.timer()
        self.summarize()
        self.print_stats()

    def start_tracing(self):
        self.events.append((self.timer(), TRACING))

    def end_tracing(self):
        self.events.append((self.timer(), END_TRACING))

    def start_backend(self):
        self.events.append((self.timer(), BACKEND))

    def end_backend(self):
        self.events.append((self.timer(), END_BACKEND))

    def start_running(self):
        self.events.append((self.timer(), RUNNING))

    def end_running(self):
        self.events.append((self.timer(), END_RUNNING))

    def start_blackhole(self):
        self.events.append((self.timer(), BLACKHOLE))

    def end_blackhole(self):
        self.events.append((self.timer(), END_BLACKHOLE))

    def summarize(self):
        current = []
        t = 0
        times = [0, 0, 0, 0]
        for t0, ev in self.events:
            if ev <= LAST_START:
                if current:
                    times[current[-1]] += t0 - t
                current.append(ev)
            else:
                times[current.pop()] += t0 - t
            t = t0
        self.trace_time = times[TRACING]
        self.backend_time = times[BACKEND]
        self.run_time = times[RUNNING]
        self.blackhole_time = times[BLACKHOLE]

    def print_stats(self):
        print "Tracing:     %f" % self.trace_time
        print "Backend:     %f" % self.backend_time
        print "Running asm: %f" % self.run_time
        print "Blackhole:   %f" % self.blackhole_time
        print "TOTAL:       %f" % (self.tk - self.t0)
