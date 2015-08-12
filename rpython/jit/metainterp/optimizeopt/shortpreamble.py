
from rpython.jit.metainterp.resoperation import ResOperation, OpHelpers,\
     rop, AbstractResOp
from rpython.jit.metainterp.history import Const, make_hashable_int,\
     TreeLoop
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

    def numargs(self):
        return self.op.numargs()

    def getarglist(self):
        return self.op.getarglist()

    def getarg(self, i):
        return self.op.getarg(i)

    def getdescr(self):
        return self.op.getdescr()

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
                                        args=self.getfield_op.getarglist())
        opinfo = opt.optimizer.ensure_ptr_info_arg0(g)
        pop = PreambleOp(self.res, preamble_op)
        assert not opinfo.is_virtual()
        descr = self.getfield_op.getdescr()
        if g.is_getfield():
            cf = optheap.field_cache(descr)
            opinfo.setfield(preamble_op.getdescr(), self.res, pop,
                            optheap, cf)
        else:
            index = g.getarg(1).getint()
            assert index >= 0
            opinfo.setitem(index, self.res, pop, optheap=optheap)

    def add_op_to_short(self, sb):
        sop = self.getfield_op
        preamble_arg = sb.produce_arg(sop.getarg(0))
        if preamble_arg is None:
            return None
        if sop.is_getfield():
            preamble_op = ResOperation(sop.getopnum(), [preamble_arg],
                                       descr=sop.getdescr())
        else:
            preamble_op = ResOperation(sop.getopnum(), [preamble_arg,
                                                        sop.getarg(1)],
                                       descr=sop.getdescr())
        return ProducedShortOp(self, preamble_op)

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
        if preamble_op.is_call():
            optpure.extra_call_pure.append(PreambleOp(op, preamble_op))
        else:
            opt.pure(op.getopnum(), PreambleOp(op, preamble_op))

    def add_op_to_short(self, sb):
        op = self.res
        arglist = []
        for arg in op.getarglist():
            newarg = sb.produce_arg(arg)
            if newarg is None:
                return None
            arglist.append(newarg)
        if op.is_call():
            opnum = OpHelpers.call_pure_for_descr(op.getdescr())
        else:
            opnum = op.getopnum()
        return ProducedShortOp(self, op.copy_and_change(opnum, args=arglist))

    def __repr__(self):
        return "PureOp(%r)" % (self.res,)

class LoopInvariantOp(AbstractShortOp):
    def __init__(self, res):
        self.res = res

    def produce_op(self, opt, preamble_op):
        optrewrite = opt.optimizer.optrewrite
        if optrewrite is None:
            return
        op = self.res
        key = make_hashable_int(op.getarg(0).getint())
        optrewrite.loop_invariant_results[key] = PreambleOp(op, preamble_op)

    def add_op_to_short(self, sb):
        op = self.res
        arglist = []
        for arg in op.getarglist():
            newarg = sb.produce_arg(arg)
            if newarg is None:
                return None
            arglist.append(newarg)
        opnum = OpHelpers.call_loopinvariant_for_descr(op.getdescr())
        return ProducedShortOp(self, op.copy_and_change(opnum, args=arglist))

    def __repr__(self):
        return "LoopInvariantOp(%r)" % (self.res,)

class CompoundOp(AbstractShortOp):
    def __init__(self, res, one, two):
        self.res = res
        self.one = one
        self.two = two

    def flatten(self, sb, l):
        pop = self.one.add_op_to_short(sb)
        if pop is not None:
            l.append(pop)
        two = self.two
        if isinstance(two, CompoundOp):
            two.flatten(sb, l)
        else:
            pop = two.add_op_to_short(sb)
            if pop is not None:
                l.append(pop)
        return l

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

dummy_short_op = ProducedShortOp(None, None)


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

    def create_short_boxes(self, optimizer, inputargs, label_args):
        # all the potential operations that can be produced, subclasses
        # of AbstractShortOp
        self.potential_ops = {}
        self.produced_short_boxes = {}
        # a way to produce const boxes, e.g. setfield_gc(p0, Const).
        # We need to remember those, but they don't produce any new boxes
        self.const_short_boxes = []
        label_d = {}
        for arg in label_args:
            label_d[arg] = None
        for box in inputargs:
            if box in label_d:
                renamed = OpHelpers.inputarg_from_tp(box.type)
                self.produced_short_boxes[box] = ShortInputArg(renamed)

        optimizer.produce_potential_short_preamble_ops(self)

        short_boxes = []
        self.boxes_in_production = {}

        for shortop in self.potential_ops.values():
            self.add_op_to_short(shortop)
        #
        for op, produced_op in self.produced_short_boxes.iteritems():
            if not isinstance(produced_op, ShortInputArg):
                short_boxes.append(produced_op)

        for short_op in self.const_short_boxes:
            getfield_op = short_op.getfield_op
            args = getfield_op.getarglist()
            preamble_arg = self.produce_arg(args[0])
            if preamble_arg is not None:
                preamble_op = getfield_op.copy_and_change(
                      getfield_op.getopnum(), [preamble_arg] + args[1:])
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
            r = self.add_op_to_short(self.potential_ops[op])
            if r is None:
                return None
            return r.preamble_op
        else:
            return None

    def add_op_to_short(self, shortop):
        if shortop.res in self.produced_short_boxes:
            return # already added due to dependencies
        self.boxes_in_production[shortop.res] = None
        try:
            if isinstance(shortop, CompoundOp):
                lst = shortop.flatten(self, [])
                if len(lst) == 0:
                    return None
                else:
                    index = -1
                    for i, item in enumerate(lst):
                        if not isinstance(item.short_op, HeapOp):
                            assert index == -1
                            index = i
                    if index == -1:
                        index = 0
                    pop = lst[index]
                    for i in range(len(lst)):
                        if i == index:
                            continue
                        opnum = OpHelpers.same_as_for_type(shortop.res.type)
                        new_name = ResOperation(opnum, [shortop.res])
                        assert lst[i].short_op is not pop.short_op
                        lst[i].short_op.res = new_name
                        self.produced_short_boxes[new_name] = lst[i]
            else:
                pop = shortop.add_op_to_short(self)
            if pop is None:
                return
            self.produced_short_boxes[shortop.res] = pop
        finally:
            del self.boxes_in_production[shortop.res]
        return pop

    def create_short_inputargs(self, label_args):
        short_inpargs = []
        for i in range(len(label_args)):
            inparg = self.produced_short_boxes.get(label_args[i], None)
            if inparg is None:
                renamed = OpHelpers.inputarg_from_tp(label_args[i].type)
                short_inpargs.append(renamed)
            else:
                #assert isinstance(inparg, ShortInputArg)
                short_inpargs.append(inparg.preamble_op)
        return short_inpargs

    def add_potential_op(self, op, pop):
        prev_op = self.potential_ops.get(op, None)
        if prev_op is None:
            self.potential_ops[op] = pop
            return
        self.potential_ops[op] = CompoundOp(op, pop, prev_op)

    def add_pure_op(self, op):
        assert op not in self.potential_ops
        self.add_potential_op(op, PureOp(op))

    def add_loopinvariant_op(self, op):
        self.add_potential_op(op, LoopInvariantOp(op))

    def add_heap_op(self, op, getfield_op):
        # or an inputarg
        if isinstance(op, Const) or op in self.produced_short_boxes:
            self.const_short_boxes.append(HeapOp(op, getfield_op))
            return # we should not be called from anywhere
        self.add_potential_op(op, HeapOp(op, getfield_op))

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
                #self.force_info_from(arg) <- XXX?
        self.short.append(preamble_op)
        if preamble_op.is_ovf():
            self.short.append(ResOperation(rop.GUARD_NO_OVERFLOW, [], None))
        info = preamble_op.get_forwarded()
        preamble_op.set_forwarded(None)
        if info is not empty_info:
            info.make_guards(preamble_op, self.short)
        if optimizer is not None:
            optimizer.setinfo_from_preamble(box, info, None)
        return preamble_op

    def add_preamble_op(self, preamble_op):
        self.used_boxes.append(preamble_op.op)
        self.short_preamble_jump.append(preamble_op.preamble_op)

    def build_short_preamble(self):
        label_op = ResOperation(rop.LABEL, self.short_inputargs[:])
        jump_op = ResOperation(rop.JUMP, self.short_preamble_jump)
        TreeLoop.check_consistency_of(self.short_inputargs,
                                      self.short + [jump_op], check_descr=False)
        return [label_op] + self.short + [jump_op]
