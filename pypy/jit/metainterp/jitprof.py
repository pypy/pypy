
""" A small helper module for profiling JIT
"""

import os
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
OPT_OPS
OPT_GUARDS
OPT_FORCINGS
ABORT_TOO_LONG
ABORT_BRIDGE
ABORT_ESCAPE
NVIRTUALS
NVHOLES
NVREUSED
"""

def _setup():
    names = counters.split()
    for i, name in enumerate(names):
        globals()[name] = i
    global ncounters
    ncounters = len(names)
_setup()

JITPROF_LINES = ncounters + 1 + 5 # one for TOTAL, 5 for calls, update if needed

class BaseProfiler(object):
    pass

class EmptyProfiler(BaseProfiler):
    initialized = True
    
    def start(self):
        pass

    def finish(self):
        pass

    def set_printing(self, printing):
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
    printing = True

    def start(self):
        self.starttime = self.timer()
        self.t1 = self.starttime
        self.times = [0, 0]
        self.counters = [0] * ncounters
        self.calls = [[0, 0], [0, 0], [0, 0]]
        self.current = []

    def finish(self):
        self.tk = self.timer()
        if self.printing:
            self.print_stats()

    def set_printing(self, printing):
        self.printing = printing

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

    # Don't record times for 'running' and 'blackhole' because there are
    # too many of them: calling time.time() is a major blocker.
    # If you are interested in these numbers, use 'PYPYLOG=file' and
    # look at the resulting file with pypy/tool/logparser.py.
    def start_running(self): self.count(RUNNING)
    def end_running(self):   pass

    def start_blackhole(self): self.count(BLACKHOLE)
    def end_blackhole(self):   pass

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
        self._print_line_time("Tracing", cnt[TRACING],   tim[TRACING])
        self._print_line_time("Backend", cnt[BACKEND],   tim[BACKEND])
        self._print_intline("Running asm", cnt[RUNNING])
        self._print_intline("Blackhole", cnt[BLACKHOLE])
        line = "TOTAL:      \t\t%f\n" % (self.tk - self.starttime, )
        os.write(2, line)
        self._print_intline("ops", cnt[OPS])
        self._print_intline("  calls", calls[0][0])
        self._print_intline("  pure calls", calls[0][1])
        self._print_intline("recorded ops", cnt[RECORDED_OPS])
        self._print_intline("  calls", calls[1][0])
        self._print_intline("  pure calls", calls[1][1])
        self._print_intline("guards", cnt[GUARDS])
        self._print_intline("blackholed ops", calls[2][0])
        self._print_intline("  pure calls", calls[2][1])
        self._print_intline("opt ops", cnt[OPT_OPS])
        self._print_intline("opt guards", cnt[OPT_GUARDS])
        self._print_intline("forcings", cnt[OPT_FORCINGS])
        self._print_intline("abort: trace too long", cnt[ABORT_TOO_LONG])
        self._print_intline("abort: compiling", cnt[ABORT_BRIDGE])
        self._print_intline("abort: vable escape", cnt[ABORT_ESCAPE])
        self._print_intline("nvirtuals", cnt[NVIRTUALS])
        self._print_intline("nvholes", cnt[NVHOLES])
        self._print_intline("nvreused", cnt[NVREUSED])

    def _print_line_time(self, string, i, tim):
        final = "%s:%s\t%d\t%f\n" % (string, " " * max(0, 13-len(string)), i, tim)
        os.write(2, final)

    def _print_intline(self, string, i):
        final = string + ':' + " " * max(0, 16-len(string))
        final += '\t' + str(i) + '\n'
        os.write(2, final)
        
        

class BrokenProfilerData(Exception):
    pass
