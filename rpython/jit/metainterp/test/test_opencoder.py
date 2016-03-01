
from rpython.jit.metainterp.opencoder import Trace, untag, TAGINT, TAGBOX
from rpython.jit.metainterp.resoperation import rop, InputArgInt
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer
from rpython.jit.metainterp import resume

class TestOpencoder(object):
    def unpack(self, t):
        iter = t.get_iter()
        l = []
        while not iter.done():
            l.append(iter.next())
        return iter.inputargs, l

    def test_simple_iterator(self):
        i0, i1 = InputArgInt(), InputArgInt()
        t = Trace([i0, i1])
        add = t.record_op(rop.INT_ADD, [i0, i1])
        t.record_op(rop.INT_ADD, [add, ConstInt(1)])
        (i0, i1), l = self.unpack(t)
        assert len(l) == 2
        assert l[0].opnum == rop.INT_ADD
        assert l[1].opnum == rop.INT_ADD
        assert l[1].getarg(1).getint() == 1
        assert l[1].getarg(0) is l[0]
        assert l[0].getarg(0) is i0
        assert l[0].getarg(1) is i1

    def test_rd_snapshot(self):
        class JitCode(object):
            def __init__(self, index):
                self.index = index

        class FakeFrame(object):
            parent_resumedata_frame_info_list = None
            parent_resumedata_snapshot = None

            def __init__(self, pc, jitcode, boxes):
                self.pc = pc
                self.jitcode = jitcode
                self.boxes = boxes

            def get_list_of_active_boxes(self, flag):
                return self.boxes

        i0, i1 = InputArgInt(), InputArgInt()
        t = Trace([i0, i1])
        add = t.record_op(rop.INT_ADD, [i0, i1])
        t.record_op(rop.GUARD_FALSE, [add])
        # now we write rd_snapshot and friends
        virtualizable_boxes = []
        virutalref_boxes = []
        framestack = [FakeFrame(1, JitCode(2), [i0, i1])]
        resume.capture_resumedata(framestack, virtualizable_boxes,
                                  virutalref_boxes, t)
        (i0, i1), l = self.unpack(t)
        assert l[1].opnum == rop.GUARD_FALSE
        assert l[1].rd_snapshot.boxes == [i0, i1]
