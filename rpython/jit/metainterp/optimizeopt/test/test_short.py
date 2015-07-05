
""" Short preamble tests
"""

from rpython.jit.metainterp.resoperation import InputArgInt, ResOperation, rop
from rpython.jit.metainterp.optimizeopt.shortpreamble import ShortBoxes
from rpython.jit.metainterp.history import AbstractDescr

class Descr(AbstractDescr):
    pass

class Opt(object):
    def __init__(self, oplist):
        self.oplist = oplist
    
    def produce_potential_short_preamble_ops(self, sb):
        for op in self.oplist:
            if isinstance(op, tuple):
                op, r = op
            else:
                op, r = op, op
            sb.add_potential(op, r)

class TestShortBoxes(object):
    def test_pure_ops(self):
        i0 = InputArgInt()
        i1 = InputArgInt()
        op = ResOperation(rop.INT_ADD, [i0, i1])
        sb = ShortBoxes()
        sb.create_short_boxes(Opt([op]), [i0, i1])
        assert sb.short_boxes == {op: None}

    def test_pure_ops_does_not_work(self):
        i0 = InputArgInt()
        i1 = InputArgInt()
        op = ResOperation(rop.INT_ADD, [i0, i1])
        sb = ShortBoxes()
        sb.create_short_boxes(Opt([op]), [i0])
        assert sb.short_boxes == {}

    def test_multiple_similar_ops(self):
        i0 = InputArgInt()
        i1 = InputArgInt()
        op = ResOperation(rop.INT_ADD, [i0, i1])
        op1 = ResOperation(rop.GETFIELD_GC_I, [i0], descr=Descr())
        sb = ShortBoxes()
        sb.create_short_boxes(Opt([op, (op1, op)]), [i0, i1])
        
