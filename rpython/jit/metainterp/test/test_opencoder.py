
from rpython.jit.metainterp.opencoder import Trace, untag, TAGINT, TAGBOX
from rpython.jit.metainterp.resoperation import rop, InputArgInt
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer
from rpython.jit.metainterp import resume

class JitCode(object):
    def __init__(self, index):
        self.index = index

class FakeFrame(object):
    parent_resumedata_position = -1

    def __init__(self, pc, jitcode, boxes):
        self.pc = pc
        self.jitcode = jitcode
        self.boxes = boxes

    def get_list_of_active_boxes(self, flag):
        return self.boxes

class TestOpencoder(object):
    def unpack(self, t):
        iter = t.get_iter()
        l = []
        while not iter.done():
            l.append(iter.next())
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

    def unpack_snapshot(self, t, pos):
        trace = t.trace
        first = trace._ops[pos] # this is the size
        pos += 1
        boxes = []
        while first > pos + 1:
            snapshot_size = trace._ops[pos]
            # 2 for jitcode and pc
            pos += 1 + 2
            boxes += [t._get(trace._ops[i + pos]) for i in range(snapshot_size)]
            pos += len(boxes)
        return boxes

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
        boxes = self.unpack_snapshot(iter, l[1].rd_resume_position)
        assert boxes == [i0, i1]
        t.record_op(rop.GUARD_FALSE, [add])
        resume.capture_resumedata([frame0, frame1], None, [], t)
        (i0, i1), l, iter = self.unpack(t)
        assert l[1].opnum == rop.GUARD_FALSE
        boxes = self.unpack_snapshot(iter, l[1].rd_resume_position)
        assert boxes == [i0, i1]
        assert l[2].opnum == rop.GUARD_FALSE
        boxes = self.unpack_snapshot(iter, l[2].rd_resume_position)
        assert boxes == [i0, i0, l[0], i0, i1]

    def test_read_snapshot_interface(self):
        i0, i1, i2 = InputArgInt(), InputArgInt(), InputArgInt()
        t = Trace([i0, i1, i2])
        t.record_op(rop.GUARD_TRUE, [i1])
        frame0 = FakeFrame(1, JitCode(2), [i0, i1])
        frame1 = FakeFrame(3, JitCode(4), [i2, i2])
        resume.capture_resumedata([frame0, frame1], None, [], t)
        (i0, i1, i2), l, iter = self.unpack(t)
        pos = l[0].rd_resume_position
        snapshot_iter = iter.get_snapshot_iter(pos)
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
