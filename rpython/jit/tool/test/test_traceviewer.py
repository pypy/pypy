import math
import py
from rpython.jit.tool.traceviewer import splitloops, FinalBlock, Block,\
     split_one_loop, postprocess, main, get_gradient_color, guard_number


def test_gradient_color():
    assert get_gradient_color(0.0000000001) == '#01FF00'   # green
    assert get_gradient_color(100000000000) == '#FF0100'   # red
    assert get_gradient_color(math.exp(1.8)) == '#FFFF00'  # yellow
    assert get_gradient_color(math.exp(1.9)) == '#FFB400'  # yellow-a-bit-red
    assert get_gradient_color(math.exp(1.7)) == '#B4FF00'  # yellow-a-bit-green


def preparse(data):
    return "\n".join([i.strip() for i in data.split("\n") if i.strip()])

class TestSplitLoops(object):
    def test_no_of_loops(self):
        data = [preparse("""
        # Loop 0 : loop with 39 ops
        debug_merge_point('', 0)
        guard_class(p4, 141310752, descr=<Guard5>) [p0, p1]
        p60 = getfield_gc(p4, descr=<GcPtrFieldDescr 16>)
        guard_nonnull(p60, descr=<Guard6>) [p0, p1]
        """), preparse("""
        # Loop 1 : loop with 46 ops
        p21 = getfield_gc(p4, descr=<GcPtrFieldDescr 16>)
        """)]
        loops = splitloops(data)
        assert len(loops) == 2

    def test_no_of_loops_hexguards(self):
        data = [preparse("""
        # Loop 0 : loop with 39 ops
        debug_merge_point('', 0)
        guard_class(p4, 141310752, descr=<Guard0x10abcdef0>) [p0, p1]
        p60 = getfield_gc(p4, descr=<GcPtrFieldDescr 16>)
        guard_nonnull(p60, descr=<Guard0x10abcdef1>) [p0, p1]
        """), preparse("""
        # Loop 1 : loop with 46 ops
        p21 = getfield_gc(p4, descr=<GcPtrFieldDescr 16>)
        """)]
        loops = splitloops(data)
        assert len(loops) == 2

    def test_split_one_loop(self):
        real_loops = [FinalBlock(preparse("""
        p21 = getfield_gc(p4, descr=<GcPtrFieldDescr 16>)
        guard_class(p4, 141310752, descr=<Guard51>) [p0, p1]
        """), None), FinalBlock(preparse("""
        p60 = getfield_gc(p4, descr=<GcPtrFieldDescr 16>)
        guard_nonnull(p60, descr=<Guard5>) [p0, p1]
        """), None)]
        real_loops[0].loop_no = 0
        real_loops[1].loop_no = 1
        allloops = real_loops[:]
        split_one_loop(real_loops, 'Guard5', 'extra', 1, 5, allloops)
        loop = real_loops[1]
        assert isinstance(loop, Block)
        assert loop.content.endswith('p1]')
        loop.left = allloops[loop.left]
        loop.right = allloops[loop.right]
        assert loop.left.content == ''
        assert loop.right.content == 'extra'

    def test_split_one_loop_hexguards(self):
        real_loops = [FinalBlock(preparse("""
        p21 = getfield_gc(p4, descr=<GcPtrFieldDescr 16>)
        guard_class(p4, 141310752, descr=<Guard0x10abcdef2>) [p0, p1]
        """), None), FinalBlock(preparse("""
        p60 = getfield_gc(p4, descr=<GcPtrFieldDescr 16>)
        guard_nonnull(p60, descr=<Guard0x10abcdef0>) [p0, p1]
        """), None)]
        real_loops[0].loop_no = 0
        real_loops[1].loop_no = 1
        allloops = real_loops[:]
        split_one_loop(real_loops, 'Guard0x10abcdef0', 'extra', 1, guard_number(("0x10abcdef0", "0x")), allloops)
        loop = real_loops[1]
        assert isinstance(loop, Block)
        assert loop.content.endswith('p1]')
        loop.left = allloops[loop.left]
        loop.right = allloops[loop.right]
        assert loop.left.content == ''
        assert loop.right.content == 'extra'

    def test_postparse(self):
        real_loops = [FinalBlock("debug_merge_point('<code object _runCallbacks, file '/tmp/x/twisted-trunk/twisted/internet/defer.py', line 357> #40 POP_TOP', 0)", None)]
        postprocess(real_loops, real_loops[:], {})
        assert real_loops[0].header.startswith("_runCallbacks, file '/tmp/x/twisted-trunk/twisted/internet/defer.py', line 357")

    def test_postparse_new(self):
        real_loops = [FinalBlock("debug_merge_point(0, 0, '<code object _optimize_charset. file '/usr/local/Cellar/pypy/2.0-beta2/lib-python/2.7/sre_compile.py'. line 207> #351 LOAD_FAST')", None)]
        postprocess(real_loops, real_loops[:], {})
        assert real_loops[0].header.startswith("_optimize_charset. file '/usr/local/Cellar/pypy/2.0-beta2/lib-python/2.7/sre_compile.py'. line 207")

    def test_load_actual(self):
        fname = py.path.local(__file__).join('..', 'data.log.bz2')
        main(str(fname), False, view=False)
        # assert did not explode

    def test_load_actual_f(self):
        fname = py.path.local(__file__).join('..', 'f.pypylog.bz2')
        main(str(fname), False, view=False)
        # assert did not explode
