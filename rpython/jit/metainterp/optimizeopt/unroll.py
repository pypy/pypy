
from rpython.jit.metainterp.history import Const
from rpython.jit.metainterp.optimizeopt.shortpreamble import ShortBoxes,\
     ShortPreambleBuilder, PreambleOp
from rpython.jit.metainterp.optimizeopt import info, intutils
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer,\
     Optimization, LoopInfo, MININT, MAXINT
from rpython.jit.metainterp.optimizeopt.virtualstate import (
    VirtualStateConstructor)
from rpython.jit.metainterp.resoperation import rop, ResOperation

class UnrollableOptimizer(Optimizer):
    def force_op_from_preamble(self, preamble_op):
        if isinstance(preamble_op, PreambleOp):
            op = preamble_op.op
            self.optimizer.inparg_dict[op] = None # XXX ARGH
            # special hack for int_add(x, accumulator-const) optimization
            self.optunroll.short_preamble_producer.use_box(op,
                                                preamble_op.preamble_op, self)
            if not preamble_op.op.is_constant():
                self.optunroll.potential_extra_ops[op] = preamble_op
            return op
        return preamble_op

    def setinfo_from_preamble_list(self, lst, infos):
        for item in lst:
            if item is None:
                continue
            i = infos.get(item, None)
            if i is not None:
                self.setinfo_from_preamble(item, i, infos)

    def setinfo_from_preamble(self, op, preamble_info, exported_infos):
        op = self.get_box_replacement(op)
        if op.get_forwarded() is not None:
            return
        if isinstance(preamble_info, info.PtrInfo):
            if preamble_info.is_virtual():
                # XXX do we want to sanitize this?
                op.set_forwarded(preamble_info)
                self.setinfo_from_preamble_list(preamble_info.all_items(),
                                          exported_infos)
                return
            if op.is_constant():
                return # nothing we can learn
            known_class = preamble_info.get_known_class(self.cpu)
            if known_class:
                self.make_constant_class(op, known_class, False)
            if isinstance(preamble_info, info.ArrayPtrInfo):
                arr_info = info.ArrayPtrInfo(None)
                arr_info.lenbound = preamble_info.getlenbound()
                op.set_forwarded(arr_info)
            if preamble_info.is_nonnull():
                self.make_nonnull(op)
        elif isinstance(preamble_info, intutils.IntBound):
            if preamble_info.lower > MININT/2 or preamble_info.upper < MAXINT/2:
                intbound = self.getintbound(op)
                if preamble_info.lower > MININT/2:
                    intbound.has_lower = True
                    intbound.lower = preamble_info.lower
                if preamble_info.upper < MAXINT/2:
                    intbound.has_upper = True
                    intbound.upper = preamble_info.upper


class UnrollOptimizer(Optimization):
    """Unroll the loop into two iterations. The first one will
    become the preamble or entry bridge (don't think there is a
    distinction anymore)"""

    short_preamble_producer = None

    def __init__(self, metainterp_sd, jitdriver_sd, optimizations):
        self.optimizer = UnrollableOptimizer(metainterp_sd, jitdriver_sd,
                                             optimizations)
        self.optimizer.optunroll = self

    def get_virtual_state(self, args):
        modifier = VirtualStateConstructor(self.optimizer)
        return modifier.get_virtual_state(args)

    def _check_no_forwarding(self, lsts):
        for lst in lsts:
            for op in lst:
                assert op.get_forwarded() is None
        assert not self.optimizer._newoperations
    
    def optimize_preamble(self, start_label, end_label, ops, call_pure_results):
        self._check_no_forwarding([[start_label, end_label], ops])
        info, newops = self.optimizer.propagate_all_forward(
            start_label.getarglist()[:], ops, call_pure_results)
        exported_state = self.export_state(start_label, end_label,
                                           info.inputargs)
        # we need to absolutely make sure that we've cleaned up all
        # the optimization info
        self.optimizer._clean_optimization_info(self.optimizer._newoperations)
        return exported_state, self.optimizer._newoperations

    def optimize_peeled_loop(self, start_label, end_jump, ops, state,
                             call_pure_results):
        self._check_no_forwarding([[start_label, end_jump], ops])
        self.import_state(start_label, state)
        self.potential_extra_ops = {}
        self.optimizer.propagate_all_forward(start_label.getarglist()[:], ops,
                                             call_pure_results, False)
        orig_jump_args = [self.get_box_replacement(op)
                     for op in end_jump.getarglist()]
        jump_args = state.virtual_state.make_inputargs(orig_jump_args,
                                    self.optimizer, force_boxes=True)
        pass_to_short = state.virtual_state.make_inputargs(orig_jump_args,
                                    self.optimizer, force_boxes=True,
                                    append_virtuals=True)
        extra_jump_args = self.inline_short_preamble(pass_to_short)
        # remove duplicates, removes stuff from used boxes too
        label_args, jump_args = self.filter_extra_jump_args(
            start_label.getarglist() + self.short_preamble_producer.used_boxes,
            jump_args + extra_jump_args)
        jump_op = ResOperation(rop.JUMP, jump_args)
        self.optimizer.send_extra_operation(jump_op)
        return (UnrollInfo(self.short_preamble_producer.build_short_preamble(),
                           label_args,
                           self.short_preamble_producer.extra_same_as),
                self.optimizer._newoperations)

    def filter_extra_jump_args(self, label_args, jump_args):
        new_label_args = []
        new_jump_args = []
        assert len(label_args) == len(jump_args)
        d = {}
        for i in range(len(label_args)):
            arg = label_args[i]
            if arg in d:
                continue
            new_label_args.append(arg)
            new_jump_args.append(jump_args[i])
            d[arg] = None
        return new_label_args, new_jump_args

    def inline_short_preamble(self, jump_args):
        sb = self.short_preamble_producer
        assert len(sb.short_inputargs) == len(jump_args)
        for i in range(len(jump_args)):
            sb.short_inputargs[i].set_forwarded(None)
            self.make_equal_to(sb.short_inputargs[i], jump_args[i])
        patchguardop = self.optimizer.patchguardop
        for op in sb.short:
            if op.is_guard():
                op = self.replace_op_with(op, op.getopnum())
                op.rd_snapshot = patchguardop.rd_snapshot
                op.rd_frame_info_list = patchguardop.rd_frame_info_list
            self.optimizer.send_extra_operation(op)
        res = [self.optimizer.get_box_replacement(op) for op in
                sb.short_preamble_jump]
        for op in sb.short_inputargs:
            op.set_forwarded(None)
        return res

    def export_state(self, start_label, end_label, renamed_inputargs):
        original_label_args = end_label.getarglist()
        end_args = [self.get_box_replacement(a) for a in original_label_args]
        virtual_state = self.get_virtual_state(end_args)
        inparg_mapping = [(start_label.getarg(i), end_args[i])
                          for i in range(len(end_args)) if
                          start_label.getarg(i) is not end_args[i]]
        infos = {}
        for arg in end_args:
            infos[arg] = self.optimizer.getinfo(arg)
        label_args = virtual_state.make_inputargs(end_args, self.optimizer)
        for arg in label_args:
            infos[arg] = self.optimizer.getinfo(arg)            
        sb = ShortBoxes()
        label_args_plus_virtuals = virtual_state.make_inputargs(end_args,
                                        self.optimizer, append_virtuals=True)
        short_boxes = sb.create_short_boxes(self.optimizer, renamed_inputargs,
                                            label_args_plus_virtuals)
        short_inputargs = sb.create_short_inputargs(label_args_plus_virtuals)
        for produced_op in short_boxes:
            op = produced_op.short_op.res
            if not isinstance(op, Const):
                infos[op] = self.optimizer.getinfo(op)
        self.optimizer._clean_optimization_info(end_args)
        self.optimizer._clean_optimization_info(start_label.getarglist())
        return ExportedState(label_args, inparg_mapping, virtual_state, infos,
                             short_boxes, renamed_inputargs,
                             short_inputargs)

    def import_state(self, targetop, exported_state):
        # the mapping between input args (from old label) and what we need
        # to actually emit. Update the info
        for source, target in exported_state.inputarg_mapping:
            if source is not target:
                source.set_forwarded(target)
            info = exported_state.exported_infos.get(target, None)
            if info is not None:
                self.optimizer.setinfo_from_preamble(source, info,
                                        exported_state.exported_infos)
        # import the optimizer state, starting from boxes that can be produced
        # by short preamble
        self.short_preamble_producer = ShortPreambleBuilder(
            exported_state.short_boxes, exported_state.short_inputargs,
            exported_state.exported_infos, self.optimizer)

        for produced_op in exported_state.short_boxes:
            produced_op.produce_op(self, exported_state.exported_infos)

    def is_call_pure_with_exception(self, op):
        if op.is_call_pure():
            effectinfo = op.getdescr().get_extra_info()
            # Assert that only EF_ELIDABLE_CANNOT_RAISE or
            # EF_ELIDABLE_OR_MEMORYERROR end up here, not
            # for example EF_ELIDABLE_CAN_RAISE.
            assert effectinfo.extraeffect in (
                effectinfo.EF_ELIDABLE_CANNOT_RAISE,
                effectinfo.EF_ELIDABLE_OR_MEMORYERROR)
            return effectinfo.extraeffect != effectinfo.EF_ELIDABLE_CANNOT_RAISE
        return False


class UnrollInfo(LoopInfo):
    """ A state after optimizing the peeled loop, contains the following:

    * short_preamble - list of operations that go into short preamble
    * label_args - additional things to put in the label
    * extra_same_as - list of extra same as to add at the end of the preamble
    """
    def __init__(self, short_preamble, label_args, extra_same_as):
        self.short_preamble = short_preamble
        self.label_args = label_args
        self.extra_same_as = extra_same_as
            
class ExportedState(LoopInfo):
    """ Exported state consists of a few pieces of information:

    * inputarg_mapping - a list of tuples with original inputarg box
                         as the first element and the second element being
                         what it maps to (potentially const)
    * exported_infos - a mapping from ops to infos, including inputargs
    * end_args - arguments that end up in the label leading to the next
                 iteration
    * virtual_state - instance of VirtualState representing current state
                      of virtuals at this label
    * short boxes - a mapping op -> preamble_op
    * renamed_inputargs - the start label arguments in optimized version
    * short_inputargs - the renamed inputargs for short preamble
    """
    
    def __init__(self, end_args, inputarg_mapping, virtual_state,
                 exported_infos, short_boxes, renamed_inputargs,
                 short_inputargs):
        self.end_args = end_args
        self.inputarg_mapping = inputarg_mapping
        self.virtual_state = virtual_state
        self.exported_infos = exported_infos
        self.short_boxes = short_boxes
        self.renamed_inputargs = renamed_inputargs
        self.short_inputargs = short_inputargs
