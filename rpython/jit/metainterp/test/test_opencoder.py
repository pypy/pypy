
from rpython.jit.metainterp.opencoder import Trace, untag, TAGINT, TAGBOX
from rpython.jit.metainterp.resoperation import rop, InputArgInt
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer
from rpython.jit.metainterp import resume
from rpython.jit.metainterp.test.strategies import lists_of_operations
from rpython.jit.metainterp.optimizeopt.test.test_util import BaseTest
from rpython.jit.metainterp.history import TreeLoop, AbstractDescr
from hypothesis import given, strategies

class JitCode(object):
    def __init__(self, index):
        self.index = index

class FakeFrame(object):
    parent_snapshot = None

    def __init__(self, pc, jitcode, boxes):
        self.pc = pc
        self.jitcode = jitcode
        self.boxes = boxes

    def get_list_of_active_boxes(self, flag):
        return self.boxes

def unpack_snapshot(t, op, pos):
    op.framestack = []
    si = t.get_snapshot_iter(op.rd_resume_position)
    virtualizables = si.get_virtualizables()
    vref_boxes = si.get_vref_boxes()
    while not si.done():
        size, jitcode, pc = si.get_size_jitcode_pc()
        if jitcode == 2**16 - 1:
            break
        boxes = []
        for i in range(size):
            boxes.append(si.next())
        op.framestack.append(FakeFrame(JitCode(jitcode), pc, boxes))
    op.framestack.reverse()
    op.virtualizables = virtualizables
    op.vref_boxes = vref_boxes

class TestOpencoder(object):
    def unpack(self, t):
        iter = t.get_iter()
        l = []
        while not iter.done():
            op = iter.next()
            if op.is_guard():
                unpack_snapshot(iter, op, op.rd_resume_position)
            l.append(op)
        return iter.inputargs, l, iter

    def test_simple_iterator(self):
        i0, i1 = InputArgInt(), InputArgInt()
        t = Trace([i0, i1])
        add = t.record_op(rop.INT_ADD, [i0, i1])
        t.record_op(rop.INT_ADD, [add, ConstInt(1)])
        (i0, i1), l, _ = self.unpack(t)
        assert len(l) == 2
        assert l[0].opnum == rop.INT_ADD
        assert l[1].opnum == rop.INT_ADD
        assert l[1].getarg(1).getint() == 1
        assert l[1].getarg(0) is l[0]
        assert l[0].getarg(0) is i0
        assert l[0].getarg(1) is i1

    def test_rd_snapshot(self):
        i0, i1 = InputArgInt(), InputArgInt()
        t = Trace([i0, i1])
        add = t.record_op(rop.INT_ADD, [i0, i1])
        t.record_op(rop.GUARD_FALSE, [add])
        # now we write rd_snapshot and friends
        frame0 = FakeFrame(1, JitCode(2), [i0, i1])
        frame1 = FakeFrame(3, JitCode(4), [i0, i0, add])
        framestack = [frame0]
        resume.capture_resumedata(framestack, None, [], t)
        (i0, i1), l, iter = self.unpack(t)
        assert l[1].opnum == rop.GUARD_FALSE
        assert l[1].framestack[0].boxes == [i0, i1]
        t.record_op(rop.GUARD_FALSE, [add])
        resume.capture_resumedata([frame0, frame1], None, [], t)
        t.record_op(rop.INT_ADD, [add, add])
        (i0, i1), l, iter = self.unpack(t)
        assert l[1].opnum == rop.GUARD_FALSE
        assert l[1].framestack[0].boxes == [i0, i1]
        assert l[2].opnum == rop.GUARD_FALSE
        fstack = l[2].framestack
        assert fstack[0].boxes == [i0, i1]
        assert fstack[1].boxes == [i0, i0, l[0]]

    def test_read_snapshot_interface(self):
        i0, i1, i2 = InputArgInt(), InputArgInt(), InputArgInt()
        t = Trace([i0, i1, i2])
        t.record_op(rop.GUARD_TRUE, [i1])
        frame0 = FakeFrame(1, JitCode(2), [i0, i1])
        frame1 = FakeFrame(3, JitCode(4), [i2, i2])
        resume.capture_resumedata([frame0, frame1], None, [], t)
        t.record_op(rop.GUARD_TRUE, [i1])
        resume.capture_resumedata([frame0, frame1], None, [], t)
        (i0, i1, i2), l, iter = self.unpack(t)
        pos = l[0].rd_resume_position
        snapshot_iter = iter.get_snapshot_iter(pos)
        assert snapshot_iter.get_virtualizables() == []
        assert snapshot_iter.get_vref_boxes() == []
        size, jc_index, pc = snapshot_iter.get_size_jitcode_pc()
        assert size == 2
        assert jc_index == 4
        assert pc == 3
        assert [snapshot_iter.next() for i in range(2)] == [i2, i2]
        size, jc_index, pc = snapshot_iter.get_size_jitcode_pc()
        assert size == 2
        assert jc_index == 2
        assert pc == 1
        assert [snapshot_iter.next() for i in range(2)] == [i0, i1]
        pos = l[1].rd_resume_position
        snapshot_iter = iter.get_snapshot_iter(pos)
        assert snapshot_iter.get_virtualizables() == []
        assert snapshot_iter.get_vref_boxes() == []
        size, jc_index, pc = snapshot_iter.get_size_jitcode_pc()
        assert size == 2
        assert jc_index == 4
        assert pc == 3
        assert [snapshot_iter.next() for i in range(2)] == [i2, i2]

    @given(lists_of_operations())
    def test_random_snapshot(self, lst):
        inputargs, ops = lst
        t = Trace(inputargs)
        for op in ops:
            newop = t.record_op(op.getopnum(), op.getarglist())
            newop.orig_op = op
            if newop.is_guard():
                resume.capture_resumedata(op.framestack,
                    None, [], t)
            op.position = newop.position
        inpargs, l, iter = self.unpack(t)
        loop1 = TreeLoop("loop1")
        loop1.inputargs = inputargs
        loop1.operations = ops
        loop2 = TreeLoop("loop2")
        loop2.inputargs = inpargs
        loop2.operations = l
        BaseTest.assert_equal(loop1, loop2)

    @given(strategies.integers(min_value=0, max_value=2**25))
    def test_packing(self, i):
        t = Trace([])
        t.record_snapshot_link(i)
        iter = t.get_iter()
        assert (((-iter._next() - 1) << 15) | (iter._next())) == i

    def test_cut_trace_from(self):
        i0, i1, i2 = InputArgInt(), InputArgInt(), InputArgInt()
        t = Trace([i0, i1, i2])
        add1 = t.record_op(rop.INT_ADD, [i0, i1])
        cut_point = t.cut_point()
        add2 = t.record_op(rop.INT_ADD, [add1, i1])
        t.record_op(rop.GUARD_TRUE, [add2])
        resume.capture_resumedata([FakeFrame(3, JitCode(4), [add2, add1, i1])],
            None, [], t)
        t.record_op(rop.INT_SUB, [add2, add1])
        t2 = t.cut_trace_from(cut_point, [add1, i1])
        (i0, i1), l, iter = self.unpack(t2)
        assert len(l) == 3
        assert l[0].getarglist() == [i0, i1]

    def test_virtualizable_virtualref(self):
        class SomeDescr(AbstractDescr):
            pass

        i0, i1, i2 = InputArgInt(), InputArgInt(), InputArgInt()
        t = Trace([i0, i1, i2])
        p0 = t.record_op(rop.NEW_WITH_VTABLE, [], descr=SomeDescr())
        t.record_op(rop.GUARD_TRUE, [i0])
        resume.capture_resumedata([], [i1, i2, p0], [p0, i1], t)
        (i0, i1, i2), l, iter = self.unpack(t)
        assert not l[1].framestack
        assert l[1].virtualizables == [l[0], i1, i2]
        assert l[1].vref_boxes == [l[0], i1]