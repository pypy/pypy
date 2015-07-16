
from rpython.jit.metainterp.resoperation import ResOperation, OpHelpers,\
     AbstractInputArg, rop
from rpython.jit.metainterp.history import Const
from rpython.jit.metainterp.optimizeopt import info

class InputArgPlaceholder(AbstractInputArg):
    def __repr__(self):
        return "placeholder"

placeholder = InputArgPlaceholder()

class ShortBoxes(object):
    def __init__(self):
        self.potential_ops = {}
        #self.extra_same_as = []

    def create_short_boxes(self, optimizer, inputargs):
        self.produced_short_boxes = {}
        self.const_short_boxes = []
        self.short_inputargs = []
        for box in inputargs:
            renamed = OpHelpers.inputarg_from_tp(box.type)
            self.produced_short_boxes[box] = (placeholder, renamed)
            self.short_inputargs.append(renamed)

        optimizer.produce_potential_short_preamble_ops(self)

        short_boxes = []

        for op, getfield_op in self.potential_ops.items():
            self.add_op_to_short(op, getfield_op)
        #
        for op, (getfield_op, preamble_op) in self.produced_short_boxes.iteritems():
            if getfield_op is not placeholder:
                short_boxes.append((op, preamble_op))
        return short_boxes + self.const_short_boxes

    def produce_short_inputargs(self):
        return self.short_inputargs

    def produce_arg(self, op):
        if op in self.produced_short_boxes:
            return self.produced_short_boxes[op][1]
        elif isinstance(op, Const):
            return op
        elif op in self.potential_ops:
            return self.add_op_to_short(op, self.potential_ops[op])
        else:
            return None

    def add_op_to_short(self, op, sop):
        if sop:
            preamble_arg = self.produce_arg(sop.getarg(0))
            if preamble_arg is None:
                return False
            preamble_op = ResOperation(sop.getopnum(), [preamble_arg],
                                       descr=sop.getdescr())
        else:
            arglist = []
            for arg in op.getarglist():
                newarg = self.produce_arg(arg)
                if newarg is None:
                    return False
                arglist.append(newarg)
            preamble_op = op.copy_and_change(op.getopnum(), args=arglist)
        self.produced_short_boxes[op] = (sop, preamble_op)
        return True

    def add_pure_op(self, op):
        assert not self.potential_ops.get(op, None)
        self.potential_ops[op] = None

    def add_heap_op(self, op, getfield_op):
        assert not self.potential_ops.get(op, None)
        if isinstance(op, Const):
            self.const_short_boxes.append((op, getfield_op))
            return # we should not be called from anywhere
        self.potential_ops[op] = getfield_op

class EmptyInfo(info.AbstractInfo):
    pass

empty_info = EmptyInfo()

class ShortPreambleBuilder(object):
    def __init__(self, short_boxes, short_inputargs, exported_infos):
        self.producable_ops = {}
        for op, preamble_op in short_boxes:
            self.producable_ops[op] = preamble_op
            preamble_op.set_forwarded(exported_infos.get(op, empty_info))
        self.short = []
        self.used_boxes = []
        self.short_inputargs = short_inputargs

    def use_box(self, box):
        preamble_op = self.producable_ops.get(box, None)
        if preamble_op is None:
            return
        del self.producable_ops[box]
        for arg in preamble_op.getarglist():
            if isinstance(arg, Const):
                pass
            elif arg.get_forwarded() is None:
                pass
            else:
                xxx
        self.short.append(preamble_op)
        info = preamble_op.get_forwarded()
        if info is not empty_info:
            info.make_guards(preamble_op, self.short)
            if info.is_constant():
                return
        self.used_boxes.append(preamble_op)

    def build_short_preamble(self):
        label_op = ResOperation(rop.LABEL, self.short_inputargs[:])
        jump_op = ResOperation(rop.JUMP, self.used_boxes)
        return [label_op] + self.short + [jump_op]
