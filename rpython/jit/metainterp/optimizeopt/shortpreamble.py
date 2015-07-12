
from rpython.jit.metainterp.resoperation import ResOperation, OpHelpers,\
     AbstractInputArg
from rpython.jit.metainterp.history import Const



class ShortBoxes(object):
    def __init__(self):
        self.potential_ops = []
        self.ops_used = {}
        self.extra_same_as = []

    def create_short_boxes(self, optimizer, inputargs):
        for box in inputargs:
            self.ops_used[box] = None
        optimizer.produce_potential_short_preamble_ops(self)

        self.short_boxes = {}
        # short boxes has a map of "op from preamble" ->
        # "op going to short preamble", where "op from preamble" can be
        # anything, but the one going to short_preamble has to be either pure
        # or a heap cache op

        for op, preamble_op in self.potential_ops:
            self.produce_short_preamble_op(op, preamble_op)
        return self.short_boxes

    def add_to_short(self, op, short_op):
        self.short_boxes[op] = short_op

    def produce_short_preamble_op(self, op, preamble_op):
        if isinstance(op, AbstractInputArg):
            if op not in self.ops_used:
                return
        else:
            for arg in op.getarglist():
                if isinstance(arg, Const):
                    pass
                elif arg in self.ops_used:
                    pass
                else:
                    return # can't produce
        if op in self.short_boxes:
            opnum = OpHelpers.same_as_for_type(op.type)
            same_as_op = ResOperation(opnum, [op])
            self.extra_same_as.append(same_as_op)
            self.add_to_short(same_as_op, preamble_op)
        else:
            self.add_to_short(op, preamble_op)

    def add_potential(self, op, short_preamble_op=None):
        if short_preamble_op is None:
            self.potential_ops.append((op, op))
        else:
            self.potential_ops.append((op, short_preamble_op))
        self.ops_used[op] = None
