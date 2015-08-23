
import sys
from rpython.jit.metainterp.history import Const
from rpython.jit.metainterp.optimizeopt.shortpreamble import ShortBoxes,\
     ShortPreambleBuilder, PreambleOp
from rpython.jit.metainterp.optimizeopt import info, intutils
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer,\
     Optimization, LoopInfo, MININT, MAXINT
from rpython.jit.metainterp.optimizeopt.virtualstate import (
    VirtualStateConstructor, VirtualStatesCantMatch)
from rpython.jit.metainterp.resoperation import rop, ResOperation, GuardResOp
from rpython.jit.metainterp import compile
from rpython.rlib.debug import debug_print

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
                arr_info = info.ArrayPtrInfo(preamble_info.arraydescr)
                arr_info.lenbound = preamble_info.getlenbound(None)
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

    def _check_no_forwarding(self, lsts, check_newops=True):
        for lst in lsts:
            for op in lst:
                assert op.get_forwarded() is None
        if check_newops:
            assert not self.optimizer._newoperations
    
    def optimize_preamble(self, start_label, end_label, ops, call_pure_results):
        self._check_no_forwarding([[start_label, end_label], ops])
        info, newops = self.optimizer.propagate_all_forward(
            start_label.getarglist()[:], ops, call_pure_results)
        exported_state = self.export_state(start_label, end_label.getarglist(),
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
        label_args = state.virtual_state.make_inputargs(
            start_label.getarglist(), self.optimizer)
        self.optimizer.init_inparg_dict_from(label_args)
        self.optimizer.propagate_all_forward(start_label.getarglist()[:], ops,
                                             call_pure_results, False)
        orig_jump_args = [self.get_box_replacement(op)
                     for op in end_jump.getarglist()]
        jump_args = state.virtual_state.make_inputargs(orig_jump_args,
                                    self.optimizer, force_boxes=True)
        pass_to_short = state.virtual_state.make_inputargs(orig_jump_args,
                                    self.optimizer, force_boxes=True,
                                    append_virtuals=True)
        sb = self.short_preamble_producer
        self.optimizer._clean_optimization_info(sb.short_inputargs)
        extra_jump_args = self.inline_short_preamble(pass_to_short,
                                sb.short_inputargs, sb.short,
                                sb.short_preamble_jump,
                                self.optimizer.patchguardop)
        # remove duplicates, removes stuff from used boxes too
        label_args, jump_args = self.filter_extra_jump_args(
            label_args + self.short_preamble_producer.used_boxes,
            jump_args + extra_jump_args)
        jump_op = ResOperation(rop.JUMP, jump_args)
        self.optimizer.send_extra_operation(jump_op)
        return (UnrollInfo(self.short_preamble_producer.build_short_preamble(),
                           label_args,
                           self.short_preamble_producer.extra_same_as),
                self.optimizer._newoperations)

    def optimize_bridge(self, start_label, operations, call_pure_results,
                        inline_short_preamble):
        self._check_no_forwarding([start_label.getarglist(),
                                    operations])
        info, ops = self.optimizer.propagate_all_forward(
            start_label.getarglist()[:], operations[:-1],
            call_pure_results, True)
        jump_op = operations[-1]
        cell_token = jump_op.getdescr()
        if not inline_short_preamble or len(cell_token.target_tokens) == 1:
            return self.jump_to_preamble(cell_token, jump_op, info)
        vs = self.jump_to_existing_trace(jump_op, inline_short_preamble)
        if vs is None:
            return info, self.optimizer._newoperations[:]
        warmrunnerdescr = self.optimizer.metainterp_sd.warmrunnerdesc
        limit = warmrunnerdescr.memory_manager.retrace_limit
        if cell_token.retraced_count < limit:
            cell_token.retraced_count += 1
            debug_print('Retracing (%d/%d)' % (cell_token.retraced_count, limit))
        else:
            debug_print("Retrace count reached, jumping to preamble")
            return self.jump_to_preamble(cell_token, jump_op, info)
        maxguards = warmrunnerdescr.memory_manager.max_retrace_guards
        guard_count = 0
        for op in self.optimizer._newoperations:
            if op.is_guard():
                guard_count += 1
        if guard_count > maxguards:
            target_token = cell_token.target_tokens[0]
            target_token.targeting_jitcell_token.retraced_count = sys.maxint
            return self.jump_to_preamble(cell_token, jump_op, info)
        exported_state = self.export_state(start_label,
                                           operations[-1].getarglist(),
                                           info.inputargs)
        self.optimizer._clean_optimization_info(self.optimizer._newoperations)
        return exported_state, self.optimizer._newoperations

    def jump_to_preamble(self, cell_token, jump_op, info):
        assert cell_token.target_tokens[0].virtual_state is None
        jump_op = jump_op.copy_and_change(rop.JUMP,
                                          descr=cell_token.target_tokens[0])
        self.optimizer.send_extra_operation(jump_op)
        return info, self.optimizer._newoperations[:]


    def jump_to_existing_trace(self, jump_op, inline_short_preamble):
        jitcelltoken = jump_op.getdescr()
        args = [self.get_box_replacement(op) for op in jump_op.getarglist()]
        virtual_state = self.get_virtual_state(args)
        infos = [self.optimizer.getinfo(arg) for arg in args]
        for target_token in jitcelltoken.target_tokens:
            target_virtual_state = target_token.virtual_state
            if target_virtual_state is None:
                continue
            try:
                extra_guards = target_virtual_state.generate_guards(
                    virtual_state, jump_op.getarglist(), infos,
                    self.optimizer.cpu)
                patchguardop = self.optimizer.patchguardop
                for guard in extra_guards.extra_guards:
                    if isinstance(guard, GuardResOp):
                        guard.rd_snapshot = patchguardop.rd_snapshot
                        guard.rd_frame_info_list = patchguardop.rd_frame_info_list
                        guard.setdescr(compile.ResumeAtPositionDescr())
                    self.send_extra_operation(guard)
            except VirtualStatesCantMatch:
                continue
            short_preamble = target_token.short_preamble
            pass_to_short = target_virtual_state.make_inputargs(args,
                self.optimizer, force_boxes=True, append_virtuals=True)
            args = target_virtual_state.make_inputargs(args,
                self.optimizer)
            extra = self.inline_short_preamble(pass_to_short,
                short_preamble[0].getarglist(), short_preamble[1:-1],
                short_preamble[-1].getarglist(), self.optimizer.patchguardop)
            self.send_extra_operation(jump_op.copy_and_change(rop.JUMP,
                                      args=args + extra,
                                      descr=target_token))
            return None # explicit because the return can be non-None
        return virtual_state

    def filter_extra_jump_args(self, label_args, jump_args):
        label_args = [self.get_box_replacement(x, True) for x in label_args]
        jump_args = [self.get_box_replacement(x) for x in jump_args]
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

    def inline_short_preamble(self, jump_args, short_inputargs, short_ops,
                              short_jump_op, patchguardop):
        try:
            self._check_no_forwarding([short_inputargs, short_ops], False)
            assert len(short_inputargs) == len(jump_args)
            for i in range(len(jump_args)):
                short_inputargs[i].set_forwarded(None)
                self.make_equal_to(short_inputargs[i], jump_args[i])
            for op in short_ops:
                if op.is_guard():
                    op = self.replace_op_with(op, op.getopnum(),
                                    descr=compile.ResumeAtPositionDescr())
                    op.rd_snapshot = patchguardop.rd_snapshot
                    op.rd_frame_info_list = patchguardop.rd_frame_info_list
                self.optimizer.send_extra_operation(op)
            res = [self.optimizer.get_box_replacement(op) for op in
                    short_jump_op]
            return res
        finally:
            for op in short_inputargs:
                op.set_forwarded(None)
            for op in short_ops:
                op.set_forwarded(None)

    def export_state(self, start_label, original_label_args, renamed_inputargs):
        end_args = [self.get_box_replacement(a) for a in original_label_args]
        virtual_state = self.get_virtual_state(end_args)
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
        return ExportedState(label_args, end_args, virtual_state, infos,
                             short_boxes, renamed_inputargs,
                             short_inputargs)

    def import_state(self, targetop, exported_state):
        # the mapping between input args (from old label) and what we need
        # to actually emit. Update the info
        assert (len(exported_state.next_iteration_args) ==
                len(targetop.getarglist()))
        for i, target in enumerate(exported_state.next_iteration_args):
            source = targetop.getarg(i)
            assert source is not target
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

    def final(self):
        return True
            
class ExportedState(LoopInfo):
    """ Exported state consists of a few pieces of information:

    * next_iteration_args - starting arguments for next iteration
    * exported_infos - a mapping from ops to infos, including inputargs
    * end_args - arguments that end up in the label leading to the next
                 iteration
    * virtual_state - instance of VirtualState representing current state
                      of virtuals at this label
    * short boxes - a mapping op -> preamble_op
    * renamed_inputargs - the start label arguments in optimized version
    * short_inputargs - the renamed inputargs for short preamble
    """
    
    def __init__(self, end_args, next_iteration_args, virtual_state,
                 exported_infos, short_boxes, renamed_inputargs,
                 short_inputargs):
        self.end_args = end_args
        self.next_iteration_args = next_iteration_args
        self.virtual_state = virtual_state
        self.exported_infos = exported_infos
        self.short_boxes = short_boxes
        self.renamed_inputargs = renamed_inputargs
        self.short_inputargs = short_inputargs

    def final(self):
        return False
