
from rpython.jit.metainterp.resoperation import ResOperation, OpHelpers,\
     rop, AbstractResOp
from rpython.jit.metainterp.history import Const
from rpython.jit.metainterp.optimizeopt import info

class PreambleOp(AbstractResOp):
    """ An operations that's only found in preamble and not
    in the list of constructed operations. When encountered (can be found
    either in pure ops or heap ops), it must be put in inputargs as well
    as short preamble (together with corresponding guards). Extra_ops is
    for extra things to be found in the label, for now only inputargs
    of the preamble that have to be propagated further.

    See force_op_from_preamble for details how the extra things are put.
    """
    
    def __init__(self, op, preamble_op):
        self.op = op
        self.preamble_op = preamble_op

    def getarg(self, i):
        return self.op.getarg(i)

    def __repr__(self):
        return "Preamble(%r)" % (self.op,)


class AbstractShortOp(object):
    """ An operation that is potentially produced by the short preamble
    """

class HeapOp(AbstractShortOp):
    def __init__(self, res, getfield_op):
        self.res = res
        self.getfield_op = getfield_op

    def produce_op(self, opt, preamble_op):
        optheap = opt.optimizer.optheap
        if optheap is None:
            return
        g = preamble_op.copy_and_change(preamble_op.getopnum(),
                                        args=[self.getfield_op.getarg(0)])
        opinfo = opt.optimizer.ensure_ptr_info_arg0(g)
        pop = PreambleOp(self.res, preamble_op)
        assert not opinfo.is_virtual()
        opinfo._fields[preamble_op.getdescr().get_index()] = pop

    def __repr__(self):
        return "HeapOp(%r)" % (self.res,)

class PureOp(AbstractShortOp):
    def __init__(self, res):
        self.res = res

    def produce_op(self, opt, preamble_op):
        optpure = opt.optimizer.optpure
        if optpure is None:
            return
        op = self.res
        opt.pure(op.getopnum(), PreambleOp(op, preamble_op))

    def __repr__(self):
        return "PureOp(%r)" % (self.res,)

class AbstractProducedShortOp(object):
    pass

class ProducedShortOp(AbstractProducedShortOp):
    def __init__(self, short_op, preamble_op):
        self.short_op = short_op
        self.preamble_op = preamble_op

    def produce_op(self, opt):
        self.short_op.produce_op(opt, self.preamble_op)

    def __repr__(self):
        return "%r -> %r" % (self.short_op, self.preamble_op)

class ShortInputArg(AbstractProducedShortOp):
    def __init__(self, preamble_op):
        self.preamble_op = preamble_op

    def produce_op(self, opt):
        pass

    def __repr__(self):
        return "INP(%r)" % (self.preamble_op,)

class ShortBoxes(object):
    def __init__(self):
        #self.extra_same_as = []
        pass

    def create_short_boxes(self, optimizer, inputargs):
        # all the potential operations that can be produced, subclasses
        # of AbstractShortOp
        self.potential_ops = {}
        self.produced_short_boxes = {}
        # a way to produce const boxes, e.g. setfield_gc(p0, Const).
        # We need to remember those, but they don't produce any new boxes
        self.const_short_boxes = []
        self.short_inputargs = []
        for box in inputargs:
            renamed = OpHelpers.inputarg_from_tp(box.type)
            self.produced_short_boxes[box] = ShortInputArg(renamed)
            self.short_inputargs.append(renamed)

        optimizer.produce_potential_short_preamble_ops(self)

        short_boxes = []
        self.boxes_in_production = {}

        for shortop in self.potential_ops.values():
            self.add_op_to_short(shortop)
        #
        for op, produced_op in self.produced_short_boxes.iteritems():
            if isinstance(produced_op, ProducedShortOp):
                short_boxes.append(produced_op)

        for short_op in self.const_short_boxes:
            getfield_op = short_op.getfield_op
            preamble_arg = self.produce_arg(getfield_op.getarg(0))
            if preamble_arg is not None:
                preamble_op = getfield_op.copy_and_change(
                    getfield_op.getopnum(), [preamble_arg])
                produced_op = ProducedShortOp(short_op, preamble_op)
                short_boxes.append(produced_op)
        return short_boxes

    def produce_arg(self, op):
        if op in self.produced_short_boxes:
            return self.produced_short_boxes[op].preamble_op
        elif op in self.boxes_in_production:
            return None
        elif isinstance(op, Const):
            return op
        elif op in self.potential_ops:
            return self.add_op_to_short(self.potential_ops[op])
        else:
            return None

    def add_op_to_short(self, shortop):
        if shortop.res in self.produced_short_boxes:
            return # already added due to dependencies
        self.boxes_in_production[shortop.res] = None
        try:
            op = shortop.res
            if isinstance(shortop, HeapOp):
                sop = shortop.getfield_op
                preamble_arg = self.produce_arg(sop.getarg(0))
                if preamble_arg is None:
                    return None
                preamble_op = ResOperation(sop.getopnum(), [preamble_arg],
                                           descr=sop.getdescr())
            else:
                assert isinstance(shortop, PureOp)
                arglist = []
                for arg in op.getarglist():
                    newarg = self.produce_arg(arg)
                    if newarg is None:
                        return None
                    arglist.append(newarg)
                preamble_op = op.copy_and_change(op.getopnum(), args=arglist)
            self.produced_short_boxes[op] = ProducedShortOp(shortop,
                                                            preamble_op)
        finally:
            del self.boxes_in_production[shortop.res]
        return preamble_op

    def add_pure_op(self, op):
        self.potential_ops[op] = PureOp(op)

    def add_heap_op(self, op, getfield_op):
        # or an inputarg
        if isinstance(op, Const) or op in self.produced_short_boxes:
            self.const_short_boxes.append(HeapOp(op, getfield_op))
            return # we should not be called from anywhere
        self.potential_ops[op] = HeapOp(op, getfield_op)

class EmptyInfo(info.AbstractInfo):
    pass

empty_info = EmptyInfo()

class ShortPreambleBuilder(object):
    def __init__(self, short_boxes, short_inputargs, exported_infos,
                 optimizer=None):
        self.producable_ops = {}
        for produced_op in short_boxes:
            op = produced_op.short_op.res
            preamble_op = produced_op.preamble_op
            if isinstance(op, Const):
                info = optimizer.getinfo(op)
            else:
                self.producable_ops[op] = produced_op.preamble_op
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
        return preamble_op

    def add_preamble_op(self, preamble_op):
        self.used_boxes.append(preamble_op.op)
        self.short_preamble_jump.append(preamble_op.preamble_op)

    def build_short_preamble(self):
        label_op = ResOperation(rop.LABEL, self.short_inputargs[:])
        jump_op = ResOperation(rop.JUMP, self.short_preamble_jump)
        return [label_op] + self.short + [jump_op]
