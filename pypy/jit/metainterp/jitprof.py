
""" A small helper module for profiling JIT
"""

import time
from pypy.rlib.debug import debug_print, debug_start, debug_stop
from pypy.rlib.debug import have_debug_prints
from pypy.jit.metainterp.jitexc import JitException

counters="""
TRACING
BACKEND
OPS
RECORDED_OPS
GUARDS
OPT_OPS
OPT_GUARDS
OPT_FORCINGS
ABORT_TOO_LONG
ABORT_BRIDGE
ABORT_ESCAPE
ABORT_BAD_LOOP
ABORT_FORCE_QUASIIMMUT
NVIRTUALS
NVHOLES
NVREUSED
TOTAL_COMPILED_LOOPS
TOTAL_COMPILED_BRIDGES
TOTAL_FREED_LOOPS
TOTAL_FREED_BRIDGES
"""

def _setup():
    names = counters.split()
    for i, name in enumerate(names):
        globals()[name] = i
    global ncounters
    ncounters = len(names)
_setup()

JITPROF_LINES = ncounters + 1 + 1 # one for TOTAL, 1 for calls, update if needed
_CPU_LINES = 4       # the last 4 lines are stored on the cpu

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
    calls = 0
    current = None
    cpu = None

    def start(self):
        self.starttime = self.timer()
        self.t1 = self.starttime
        self.times = [0, 0]
        self.counters = [0] * (ncounters - _CPU_LINES)
        self.calls = 0
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

    def count(self, kind, inc=1):
        self.counters[kind] += inc        
    
    def count_ops(self, opnum, kind=OPS):
        from pypy.jit.metainterp.resoperation import rop
        self.counters[kind] += 1
        if opnum == rop.CALL and kind == RECORDED_OPS:# or opnum == rop.OOSEND:
            self.calls += 1

    def print_stats(self):
        debug_start("jit-summary")
        if have_debug_prints():
            self._print_stats()
        debug_stop("jit-summary")

    def _print_stats(self):
        cnt = self.counters
        tim = self.times
        calls = self.calls
        self._print_line_time("Tracing", cnt[TRACING],   tim[TRACING])
        self._print_line_time("Backend", cnt[BACKEND],   tim[BACKEND])
        line = "TOTAL:      \t\t%f" % (self.tk - self.starttime, )
        debug_print(line)
        self._print_intline("ops", cnt[OPS])
        self._print_intline("recorded ops", cnt[RECORDED_OPS])
        self._print_intline("  calls", calls)
        self._print_intline("guards", cnt[GUARDS])
        self._print_intline("opt ops", cnt[OPT_OPS])
        self._print_intline("opt guards", cnt[OPT_GUARDS])
        self._print_intline("forcings", cnt[OPT_FORCINGS])
        self._print_intline("abort: trace too long", cnt[ABORT_TOO_LONG])
        self._print_intline("abort: compiling", cnt[ABORT_BRIDGE])
        self._print_intline("abort: vable escape", cnt[ABORT_ESCAPE])
        self._print_intline("abort: bad loop", cnt[ABORT_BAD_LOOP])
        self._print_intline("abort: force quasi-immut",
                                               cnt[ABORT_FORCE_QUASIIMMUT])
        self._print_intline("nvirtuals", cnt[NVIRTUALS])
        self._print_intline("nvholes", cnt[NVHOLES])
        self._print_intline("nvreused", cnt[NVREUSED])
        cpu = self.cpu
        if cpu is not None:   # for some tests
            self._print_intline("Total # of loops",
                                cpu.total_compiled_loops)
            self._print_intline("Total # of bridges",
                                cpu.total_compiled_bridges)
            self._print_intline("Freed # of loops",
                                cpu.total_freed_loops)
            self._print_intline("Freed # of bridges",
                                cpu.total_freed_bridges)

    def _print_line_time(self, string, i, tim):
        final = "%s:%s\t%d\t%f" % (string, " " * max(0, 13-len(string)), i, tim)
        debug_print(final)

    def _print_intline(self, string, i):
        final = string + ':' + " " * max(0, 16-len(string))
        final += '\t' + str(i)
        debug_print(final)


class BrokenProfilerData(JitException):
    pass
