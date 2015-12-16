
from rpython.jit.metainterp.opencoder import Trace, untag, TAGINT, TAGBOX
from rpython.jit.metainterp.resoperation import rop, InputArgInt
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer

class SimpleOptimizer(Optimizer):
    def __init__(self, trace):
        self.trace = trace
        self.infos = [None] * trace._count

class TestOpencoder(object):
    def unpack(self, t):
        iter = t.get_iter()
        l = []
        while not iter.done():
            l.append(iter.next())
        return l

    def test_simple_iterator(self):
        i0, i1 = InputArgInt(), InputArgInt()
        t = Trace([i0, i1])
        add = t.record_op(rop.INT_ADD, [i0, i1])
        t.record_op(rop.INT_ADD, [add, ConstInt(1)])
        l = self.unpack(t)
        assert len(l) == 2
        assert l[0].opnum == rop.INT_ADD
        assert l[1].opnum == rop.INT_ADD
        assert (untag(l[1].args[1]) == TAGINT, 1)
        assert (untag(l[1].args[0]) == TAGBOX, l[0]._pos)
        assert (untag(l[0].args[0]) == TAGBOX, 0)
        assert (untag(l[0].args[1]) == TAGBOX, 1)

    def test_forwarding(self):
        i0, i1 = InputArgInt(), InputArgInt()
        t = Trace([i0, i1])
        add = t.record_op(rop.INT_ADD, [i0, i1])
        t.record_op(rop.INT_ADD, [add, ConstInt(1)])
        opt = SimpleOptimizer(t)
        add, add2 = self.unpack(t)
        assert (untag(opt.get_box_replacement(add.get_tag())) == TAGBOX, add._pos)
        newtag = opt.replace_op_with(add, rop.INT_NEG, [i0])
        assert opt.get_box_replacement(add.get_tag()) == newtag

    def test_infos(self):
        i0 = InputArgInt()
        t = Trace([i0])
        t.record_op(rop.INT_ADD, [i0, ConstInt(1)])
        opt = SimpleOptimizer(t)
        add,  = self.unpack(t)
        assert opt.getintbound(add.get_tag())

    def test_output(self):
        pass