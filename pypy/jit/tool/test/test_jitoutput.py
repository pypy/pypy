
import py
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.rlib.jit import JitDriver, DEBUG_PROFILE
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp.jitprof import Profiler, JITPROF_LINES
from pypy.jit.tool.jitoutput import parse_prof

def test_really_run():
    """ This test checks whether output of jitprof did not change.
    It'll explode when someone touches jitprof.py
    """
    mydriver = JitDriver(reds = ['i', 'n'], greens = [])
    def f(n):
        i = 0
        while i < n:
            mydriver.can_enter_jit(i=i, n=n)
            mydriver.jit_merge_point(i=i, n=n)
            i += 1

    cap = py.io.StdCaptureFD()
    try:
        ll_meta_interp(f, [10], CPUClass=runner.LLtypeCPU, type_system='lltype',
                       ProfilerClass=Profiler, debug_level=DEBUG_PROFILE)
    finally:
        out, err = cap.reset()
    err = "\n".join(err.splitlines()[-JITPROF_LINES:])
    print err
    assert err.count("\n") == JITPROF_LINES - 1
    info = parse_prof(err)
    # assert did not crash
    # asserts below are a bit delicate, possibly they might be deleted
    assert info.tracing_no == 1
    assert info.asm_no == 1
    assert info.blackhole_no == 1
    assert info.backend_no == 1
    assert info.ops.total == 2
    assert info.ops.calls == 0
    assert info.ops.pure_calls == 0
    assert info.recorded_ops.total == 2
    assert info.recorded_ops.calls == 0
    assert info.recorded_ops.pure_calls == 0
    assert info.guards == 1
    assert info.blackholed_ops.total == 0
    assert info.blackholed_ops.pure_calls == 0
    assert info.opt_ops == 6
    assert info.opt_guards == 1
    assert info.forcings == 0

DATA = '''Tracing:         1       0.006992
Backend:        1       0.000525
Running asm:            1
Blackhole:              1
TOTAL:                  0.025532
ops:                    2
  calls:                1
  pure calls:           1
recorded ops:           6
  calls:                3
  pure calls:           2
guards:                 1
blackholed ops:         5
  pure calls:           3
opt ops:                6
opt guards:             1
forcings:               1
abort: trace too long:  10
abort: compiling:       11
abort: vable escape:    12
nvirtuals:              13
nvholes:                14
nvreused:               15
'''

def test_parse():
    info = parse_prof(DATA)
    assert info.tracing_no == 1
    assert info.tracing_time == 0.006992
    assert info.asm_no == 1
    assert info.blackhole_no == 1
    assert info.backend_no == 1
    assert info.backend_time == 0.000525
    assert info.ops.total == 2
    assert info.ops.calls == 1
    assert info.ops.pure_calls == 1
    assert info.recorded_ops.total == 6
    assert info.recorded_ops.calls == 3
    assert info.recorded_ops.pure_calls == 2
    assert info.guards == 1
    assert info.blackholed_ops.total == 5
    assert info.blackholed_ops.pure_calls == 3
    assert info.opt_ops == 6
    assert info.opt_guards == 1
    assert info.forcings == 1
    assert info.abort.trace_too_long == 10
    assert info.abort.compiling == 11
    assert info.abort.vable_escape == 12
    assert info.nvirtuals == 13
    assert info.nvholes == 14
    assert info.nvreused == 15
