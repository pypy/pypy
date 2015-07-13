
from rpython.jit.metainterp.resoperation import ResOperation, OpHelpers,\
     AbstractInputArg
from rpython.jit.metainterp.history import Const



class ShortBoxes(object):
    def __init__(self):
        self.potential_ops = []
        self.produced_short_boxes = {}
        self.extra_same_as = []

    def create_short_boxes(self, optimizer, inputargs):
        for box in inputargs:
            self.produced_short_boxes[box] = None

        optimizer.produce_potential_short_preamble_ops(self)

        self.short_boxes = []
        # short boxes is a list of (op, preamble_op)
        # where op can be
        # anything, but the preamble_op has to be either pure
        # or a heap cache op

        for op, preamble_op in self.potential_ops:
            self.produce_short_preamble_op(op, preamble_op)
        self.produced_short_boxes = None
        return self.short_boxes

    def add_to_short(self, op, short_op):
        self.short_boxes.append((op, short_op))
        self.produced_short_boxes[op] = None

    def produce_short_preamble_op(self, op, preamble_op):
        for arg in preamble_op.getarglist():
            if isinstance(arg, Const):
                pass
            elif arg in self.produced_short_boxes:
                pass
            else:
                return # can't produce
        if op in self.produced_short_boxes:
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
