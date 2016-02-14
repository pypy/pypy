
from rpython.jit.metainterp.opencoder import Trace, untag, TAGINT, TAGBOX
from rpython.jit.metainterp.resoperation import rop, InputArgInt
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer

class SimpleOptimizer(Optimizer):
    class metainterp_sd:
        class profiler:
            @staticmethod
            def count(*args):
                pass

    def __init__(self, trace):
        self.trace = trace
        self.optimizer = self # uh?
        self.infos = [None] * trace._count
        self.output = Trace([])

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
        assert l[1].getarg(1).getint() == 1
        assert l[1].getarg(0) is l[0]
        assert l[0].getarg(0) is i0
        assert l[0].getarg(1) is i1
