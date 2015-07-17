
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
                if getfield_op is None:
                    short_boxes.append((op, None, preamble_op))
                else:
                    short_boxes.append((op, getfield_op.getarg(0), preamble_op))
        for op, getfield_op in self.const_short_boxes:
            preamble_arg = self.produce_arg(getfield_op.getarg(0))
            if preamble_arg is not None:
                short_boxes.append((op, getfield_op.getarg(0),
                    getfield_op.copy_and_change(getfield_op.getopnum(),
                                                [preamble_arg])))
        return short_boxes

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
                return None
            preamble_op = ResOperation(sop.getopnum(), [preamble_arg],
                                       descr=sop.getdescr())
        else:
            arglist = []
            for arg in op.getarglist():
                newarg = self.produce_arg(arg)
                if newarg is None:
                    return None
                arglist.append(newarg)
            preamble_op = op.copy_and_change(op.getopnum(), args=arglist)
        self.produced_short_boxes[op] = (sop, preamble_op)
        return preamble_op

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
    def __init__(self, short_boxes, short_inputargs, exported_infos,
                 optimizer=None):
        self.producable_ops = {}
        for op, sop, preamble_op in short_boxes:
            self.producable_ops[op] = preamble_op
            if isinstance(op, Const):
                info = optimizer.getinfo(op)
            else:
                info = exported_infos[op]
                if info is None:
                    info = empty_info
            preamble_op.set_forwarded(info)
        self.short = []
        self.used_boxes = []
        self.short_preamble_jump = []
        self.short_inputargs = short_inputargs

    def use_box(self, box, optimizer=None):
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
                self.short.append(arg)
                info = arg.get_forwarded()
                if info is not empty_info:
                    info.make_guards(arg, self.short)
                arg.set_forwarded(None)
                self.force_info_from(arg)
        self.short.append(preamble_op)
        info = preamble_op.get_forwarded()
        preamble_op.set_forwarded(None)
        if info is not empty_info:
            info.make_guards(preamble_op, self.short)
        if optimizer is not None:
            optimizer.setinfo_from_preamble(box, info)

    def add_preamble_op(self, op, preamble_op):
        self.used_boxes.append(op)
        self.short_preamble_jump.append(preamble_op)        

    def build_short_preamble(self):
        label_op = ResOperation(rop.LABEL, self.short_inputargs[:])
        jump_op = ResOperation(rop.JUMP, self.short_preamble_jump)
        return [label_op] + self.short + [jump_op]
