
import py
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.rlib.jit import JitDriver
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp.jitprof import Profiler, JITPROF_LINES
from pypy.jit.tool.jitoutput import parse_prof
from pypy.tool.logparser import parse_log, extract_category

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
                       ProfilerClass=Profiler)
    finally:
        out, err = cap.reset()

    log = parse_log(err.splitlines(True))
    err_sections = list(extract_category(log, 'jit-summary'))
    [err1] = err_sections    # there should be exactly one jit-summary
    assert err1.count("\n") == JITPROF_LINES
    info = parse_prof(err1)
    # assert did not crash
    # asserts below are a bit delicate, possibly they might be deleted
    assert info.tracing_no == 1
    assert info.asm_no == 1
    assert info.blackhole_no == 1
    assert info.backend_no == 1
    assert info.ops.total == 2
    assert info.recorded_ops.total == 2
    assert info.recorded_ops.calls == 0
    assert info.guards == 1
    assert info.opt_ops == 13
    assert info.opt_guards == 2
    assert info.forcings == 0

DATA = '''Tracing:         1       0.006992
Backend:        1       0.000525
Running asm:            1
Blackhole:              1
TOTAL:                  0.025532
ops:                    2
recorded ops:           6
  calls:                3
guards:                 1
opt ops:                6
opt guards:             1
forcings:               1
abort: trace too long:  10
abort: compiling:       11
abort: vable escape:    12
abort: bad loop:        135
abort: force quasi-immut: 3
nvirtuals:              13
nvholes:                14
nvreused:               15
Total # of loops:       100
Total # of bridges:     300
Freed # of loops:       99
Freed # of bridges:     299
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
    assert info.recorded_ops.total == 6
    assert info.recorded_ops.calls == 3
    assert info.guards == 1
    assert info.opt_ops == 6
    assert info.opt_guards == 1
    assert info.forcings == 1
    assert info.abort.trace_too_long == 10
    assert info.abort.compiling == 11
    assert info.abort.vable_escape == 12
    assert info.abort.bad_loop == 135
    assert info.abort.force_quasiimmut == 3
    assert info.nvirtuals == 13
    assert info.nvholes == 14
    assert info.nvreused == 15
