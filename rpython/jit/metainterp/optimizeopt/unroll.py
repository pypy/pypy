
import sys
from rpython.jit.metainterp.history import Const, TargetToken, JitCellToken
from rpython.jit.metainterp.optimizeopt.shortpreamble import ShortBoxes,\
     ShortPreambleBuilder, ExtendedShortPreambleBuilder, PreambleOp
from rpython.jit.metainterp.optimizeopt import info, intutils
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer,\
     Optimization, LoopInfo, MININT, MAXINT, BasicLoopInfo
from rpython.jit.metainterp.optimizeopt.vstring import StrPtrInfo
from rpython.jit.metainterp.optimizeopt.virtualstate import (
    VirtualStateConstructor, VirtualStatesCantMatch)
from rpython.jit.metainterp.resoperation import rop, ResOperation, GuardResOp,\
     AbstractResOp
from rpython.jit.metainterp import compile
from rpython.rlib.debug import debug_print, debug_start, debug_stop,\
     have_debug_prints

class UnrollableOptimizer(Optimizer):    
    def force_op_from_preamble(self, preamble_op):
        if isinstance(preamble_op, PreambleOp):
            if self.optunroll.short_preamble_producer is None:
                assert False # unreachable code
            op = preamble_op.op
            self.optimizer.inparg_dict[op] = None # XXX ARGH
            # special hack for int_add(x, accumulator-const) optimization
            self.optunroll.short_preamble_producer.use_box(op,
                                                preamble_op.preamble_op, self)
            if not preamble_op.op.is_constant():
                if preamble_op.invented_name:
                    op = self.get_box_replacement(op)
                self.optunroll.potential_extra_ops[op] = preamble_op
            return preamble_op.op
        return preamble_op

    def setinfo_from_preamble_list(self, lst, infos):
        for item in lst:
            if item is None:
                continue
            i = infos.get(item, None)
            if i is not None:
                self.setinfo_from_preamble(item, i, infos)
            else:
                item.set_forwarded(None)
                # let's not inherit stuff we don't
                # know anything about

    def setinfo_from_preamble(self, op, preamble_info, exported_infos):
        op = self.get_box_replacement(op)
        if op.get_forwarded() is not None:
            return
        if op.is_constant():
            return # nothing we can learn
        if isinstance(preamble_info, info.PtrInfo):
            if preamble_info.is_virtual():
                op.set_forwarded(preamble_info)
                self.setinfo_from_preamble_list(preamble_info.all_items(),
                                          exported_infos)
                return
            if preamble_info.is_constant():
                # but op is not
                op.set_forwarded(preamble_info.getconst())
                return
            if preamble_info.get_descr() is not None:
                if isinstance(preamble_info, info.StructPtrInfo):
                    op.set_forwarded(info.StructPtrInfo(
                        preamble_info.get_descr()))
                if isinstance(preamble_info, info.InstancePtrInfo):
                    op.set_forwarded(info.InstancePtrInfo(
                        preamble_info.get_descr()))
            known_class = preamble_info.get_known_class(self.cpu)
            if known_class:
                self.make_constant_class(op, known_class, False)
            if isinstance(preamble_info, info.ArrayPtrInfo):
                arr_info = info.ArrayPtrInfo(preamble_info.descr)
                bound = preamble_info.getlenbound(None).clone()
                assert isinstance(bound, intutils.IntBound)
                arr_info.lenbound = bound
                op.set_forwarded(arr_info)
            if isinstance(preamble_info, StrPtrInfo):
                str_info = StrPtrInfo(preamble_info.mode)
                bound = preamble_info.getlenbound(None).clone()
                assert isinstance(bound, intutils.IntBound)
                str_info.lenbound = bound
                op.set_forwarded(str_info)
            if preamble_info.is_nonnull():
                self.make_nonnull(op)
        elif isinstance(preamble_info, intutils.IntBound):
            if preamble_info.lower > MININT/2 or preamble_info.upper < MAXINT/2:
                intbound = self.getintbound(op)
                if preamble_info.has_lower and preamble_info.lower > MININT/2:
                    intbound.has_lower = True
                    intbound.lower = preamble_info.lower
                if preamble_info.has_upper and preamble_info.upper < MAXINT/2:
                    intbound.has_upper = True
                    intbound.upper = preamble_info.upper
        elif isinstance(preamble_info, info.FloatConstInfo):
            op.set_forwarded(preamble_info._const)


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
    
    def optimize_preamble(self, start_label, end_label, ops, call_pure_results,
                          memo):
        self._check_no_forwarding([[start_label, end_label], ops])
        info, newops = self.optimizer.propagate_all_forward(
            start_label.getarglist()[:], ops, call_pure_results, True,
            flush=False)
        exported_state = self.export_state(start_label, end_label.getarglist(),
                                           info.inputargs, memo)
        exported_state.quasi_immutable_deps = info.quasi_immutable_deps
        # we need to absolutely make sure that we've cleaned up all
        # the optimization info
        self.optimizer._clean_optimization_info(self.optimizer._newoperations)
        return exported_state, self.optimizer._newoperations

    def optimize_peeled_loop(self, start_label, end_jump, ops, state,
                             call_pure_results, inline_short_preamble=True):
        self._check_no_forwarding([[start_label, end_jump], ops])
        try:
            label_args = self.import_state(start_label, state)
        except VirtualStatesCantMatch:
            raise InvalidLoop("Cannot import state, virtual states don't match")
        self.potential_extra_ops = {}
        self.optimizer.init_inparg_dict_from(label_args)
        info, _ = self.optimizer.propagate_all_forward(
            start_label.getarglist()[:], ops, call_pure_results, False,
            flush=False)
        label_op = ResOperation(rop.LABEL, label_args, start_label.getdescr())
        for a in end_jump.getarglist():
            self.optimizer.force_box_for_end_of_preamble(
                self.optimizer.get_box_replacement(a))
        current_vs = self.get_virtual_state(end_jump.getarglist())
        # pick the vs we want to jump to
        celltoken = start_label.getdescr()
        assert isinstance(celltoken, JitCellToken)
        
        target_virtual_state = self.pick_virtual_state(current_vs,
                                                       state.virtual_state,
                                                celltoken.target_tokens)
        # force the boxes for virtual state to match
        try:
            args = target_virtual_state.make_inputargs(
               [self.get_box_replacement(x) for x in end_jump.getarglist()],
               self.optimizer, force_boxes=True)
            for arg in args:
                self.optimizer.force_box(arg)
        except VirtualStatesCantMatch:
            raise InvalidLoop("Virtual states did not match "
                              "after picking the virtual state, when forcing"
                              " boxes")
        extra_same_as = self.short_preamble_producer.extra_same_as[:]
        target_token = self.finalize_short_preamble(label_op,
                                                    state.virtual_state)
        label_op.setdescr(target_token)

        if not inline_short_preamble:
            self.jump_to_preamble(celltoken, end_jump, info)
            return (UnrollInfo(target_token, label_op, [],
                               self.optimizer.quasi_immutable_deps),
                    self.optimizer._newoperations)            

        try:
            new_virtual_state = self.jump_to_existing_trace(end_jump, label_op)
        except InvalidLoop:
            # inlining short preamble failed, jump to preamble
            self.jump_to_preamble(celltoken, end_jump, info)
            return (UnrollInfo(target_token, label_op, [],
                               self.optimizer.quasi_immutable_deps),
                    self.optimizer._newoperations)            
        if new_virtual_state is not None:
            self.jump_to_preamble(celltoken, end_jump, info)
            return (UnrollInfo(target_token, label_op, [],
                               self.optimizer.quasi_immutable_deps),
                    self.optimizer._newoperations)

        self.disable_retracing_if_max_retrace_guards(
            self.optimizer._newoperations, target_token)
        
        return (UnrollInfo(target_token, label_op, extra_same_as,
                           self.optimizer.quasi_immutable_deps),
                self.optimizer._newoperations)

    def disable_retracing_if_max_retrace_guards(self, ops, target_token):
        maxguards = self.optimizer.metainterp_sd.warmrunnerdesc.memory_manager.max_retrace_guards
        count = 0
        for op in ops:
            if op.is_guard():
                count += 1
        if count > maxguards:
            assert isinstance(target_token, TargetToken)
            target_token.targeting_jitcell_token.retraced_count = sys.maxint

    def pick_virtual_state(self, my_vs, label_vs, target_tokens):
        if target_tokens is None:
            return label_vs # for tests
        for token in target_tokens:
            if token.virtual_state is None:
                continue
            if token.virtual_state.generalization_of(my_vs, self.optimizer):
                return token.virtual_state
        return label_vs

    def optimize_bridge(self, start_label, operations, call_pure_results,
                        inline_short_preamble, box_names_memo):
        self._check_no_forwarding([start_label.getarglist(),
                                    operations])
        info, ops = self.optimizer.propagate_all_forward(
            start_label.getarglist()[:], operations[:-1],
            call_pure_results, True)
        jump_op = operations[-1]
        cell_token = jump_op.getdescr()
        assert isinstance(cell_token, JitCellToken)
        if not inline_short_preamble or len(cell_token.target_tokens) == 1:
            return self.jump_to_preamble(cell_token, jump_op, info)
        # force all the information that does not go to the short
        # preamble at all
        self.optimizer.flush()
        for a in jump_op.getarglist():
            self.optimizer.force_box_for_end_of_preamble(a)
        try:
            vs = self.jump_to_existing_trace(jump_op, None)
        except InvalidLoop:
            return self.jump_to_preamble(cell_token, jump_op, info)            
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
        exported_state = self.export_state(start_label,
                                           operations[-1].getarglist(),
                                           info.inputargs, box_names_memo)
        exported_state.quasi_immutable_deps = self.optimizer.quasi_immutable_deps
        self.optimizer._clean_optimization_info(self.optimizer._newoperations)
        return exported_state, self.optimizer._newoperations

    def finalize_short_preamble(self, label_op, virtual_state):
        sb = self.short_preamble_producer
        self.optimizer._clean_optimization_info(sb.short_inputargs)
        short_preamble = sb.build_short_preamble()
        jitcelltoken = label_op.getdescr()
        assert isinstance(jitcelltoken, JitCellToken)
        if jitcelltoken.target_tokens is None:
            jitcelltoken.target_tokens = []
        target_token = TargetToken(jitcelltoken,
                                   original_jitcell_token=jitcelltoken)
        target_token.original_jitcell_token = jitcelltoken
        target_token.virtual_state = virtual_state
        target_token.short_preamble = short_preamble
        jitcelltoken.target_tokens.append(target_token)
        self.short_preamble_producer = ExtendedShortPreambleBuilder(
            target_token, sb)
        label_op.initarglist(label_op.getarglist() + sb.used_boxes)
        return target_token

    def jump_to_preamble(self, cell_token, jump_op, info):
        assert cell_token.target_tokens[0].virtual_state is None
        jump_op = jump_op.copy_and_change(rop.JUMP,
                                          descr=cell_token.target_tokens[0])
        self.optimizer.send_extra_operation(jump_op)
        return info, self.optimizer._newoperations[:]


    def jump_to_existing_trace(self, jump_op, label_op):
        jitcelltoken = jump_op.getdescr()
        assert isinstance(jitcelltoken, JitCellToken)
        virtual_state = self.get_virtual_state(jump_op.getarglist())
        args = [self.get_box_replacement(op) for op in jump_op.getarglist()]
        for target_token in jitcelltoken.target_tokens:
            target_virtual_state = target_token.virtual_state
            if target_virtual_state is None:
                continue
            try:
                extra_guards = target_virtual_state.generate_guards(
                    virtual_state, args, jump_op.getarglist(), self.optimizer)
                patchguardop = self.optimizer.patchguardop
                for guard in extra_guards.extra_guards:
                    if isinstance(guard, GuardResOp):
                        guard.rd_snapshot = patchguardop.rd_snapshot
                        guard.rd_frame_info_list = patchguardop.rd_frame_info_list
                        guard.setdescr(compile.ResumeAtPositionDescr())
                    self.send_extra_operation(guard)
            except VirtualStatesCantMatch:
                continue
            args, virtuals = target_virtual_state.make_inputargs_and_virtuals(
                args, self.optimizer)
            short_preamble = target_token.short_preamble
            extra = self.inline_short_preamble(args + virtuals, args,
                                short_preamble, self.optimizer.patchguardop,
                                target_token, label_op)
            self.send_extra_operation(jump_op.copy_and_change(rop.JUMP,
                                      args=args + extra,
                                      descr=target_token))
            return None # explicit because the return can be non-None
        return virtual_state

    def _map_args(self, mapping, arglist):
        result = []
        for box in arglist:
            if not isinstance(box, Const):
                box = mapping[box]
            result.append(box)
        return result

    def inline_short_preamble(self, jump_args, args_no_virtuals, short,
                              patchguardop, target_token, label_op):
        short_inputargs = short[0].getarglist()
        short_jump_args = short[-1].getarglist()
        if (self.short_preamble_producer and
            self.short_preamble_producer.target_token is target_token):
            # this means we're inlining the short preamble that's being
            # built. Make sure we modify the correct things in-place
            # THIS WILL MODIFY ALL THE LISTS PROVIDED, POTENTIALLY
            self.short_preamble_producer.setup(short_inputargs, short_jump_args,
                                               short, label_op.getarglist())
        if 1:     # (keep indentation)
            self._check_no_forwarding([short_inputargs, short], False)
            assert len(short_inputargs) == len(jump_args)
            # We need to make a list of fresh new operations corresponding
            # to the short preamble operations.  We could temporarily forward
            # the short operations to the fresh ones, but there are obscure
            # issues: send_extra_operation() below might occasionally invoke
            # use_box(), which assumes the short operations are not forwarded.
            # So we avoid such temporary forwarding and just use a dict here.
            mapping = {}
            for i in range(len(jump_args)):
                mapping[short_inputargs[i]] = jump_args[i]
            i = 1
            while i < len(short) - 1:
                sop = short[i]
                arglist = self._map_args(mapping, sop.getarglist())
                if sop.is_guard():
                    op = sop.copy_and_change(sop.getopnum(), arglist,
                                    descr=compile.ResumeAtPositionDescr())
                    assert isinstance(op, GuardResOp)
                    op.rd_snapshot = patchguardop.rd_snapshot
                    op.rd_frame_info_list = patchguardop.rd_frame_info_list
                else:
                    op = sop.copy_and_change(sop.getopnum(), arglist)
                mapping[sop] = op
                i += 1
                self.optimizer.send_extra_operation(op)
            # force all of them except the virtuals
            for arg in args_no_virtuals + short_jump_args:
                self.optimizer.force_box(self.get_box_replacement(arg))
            self.optimizer.flush()
            return [self.get_box_replacement(box)
                    for box in self._map_args(mapping, short_jump_args)]

    def _expand_info(self, arg, infos):
        if isinstance(arg, AbstractResOp) and arg.is_same_as():
            info = self.optimizer.getinfo(arg.getarg(0))
        else:
            info = self.optimizer.getinfo(arg)
        if arg in infos:
            return
        if info:
            infos[arg] = info
            if info.is_virtual():
                self._expand_infos_from_virtual(info, infos)

    def _expand_infos_from_virtual(self, info, infos):
        items = info.all_items()
        for item in items:
            if item is None:
                continue
            self._expand_info(item, infos)

    def export_state(self, start_label, original_label_args, renamed_inputargs,
                     memo):
        end_args = [self.optimizer.force_box_for_end_of_preamble(a)
                    for a in original_label_args]
        self.optimizer.flush()
        virtual_state = self.get_virtual_state(end_args)
        end_args = [self.get_box_replacement(arg) for arg in end_args]
        infos = {}
        for arg in end_args:
            self._expand_info(arg, infos)
        label_args, virtuals = virtual_state.make_inputargs_and_virtuals(
            end_args, self.optimizer)
        for arg in label_args:
            self._expand_info(arg, infos)
        sb = ShortBoxes()
        short_boxes = sb.create_short_boxes(self.optimizer, renamed_inputargs,
                                            label_args + virtuals)
        short_inputargs = sb.create_short_inputargs(label_args + virtuals)
        for produced_op in short_boxes:
            op = produced_op.short_op.res
            if not isinstance(op, Const):
                self._expand_info(op, infos)
        self.optimizer._clean_optimization_info(end_args)
        self.optimizer._clean_optimization_info(start_label.getarglist())
        return ExportedState(label_args, end_args, virtual_state, infos,
                             short_boxes, renamed_inputargs,
                             short_inputargs, memo)

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
        label_args = exported_state.virtual_state.make_inputargs(
            targetop.getarglist(), self.optimizer)
        
        self.short_preamble_producer = ShortPreambleBuilder(
            label_args, exported_state.short_boxes,
            exported_state.short_inputargs, exported_state.exported_infos,
            self.optimizer)

        for produced_op in exported_state.short_boxes:
            produced_op.produce_op(self, exported_state.exported_infos)

        return label_args


class UnrollInfo(BasicLoopInfo):
    """ A state after optimizing the peeled loop, contains the following:

    * target_token - generated target token
    * label_args - label operations at the beginning
    * extra_same_as - list of extra same as to add at the end of the preamble
    """
    def __init__(self, target_token, label_op, extra_same_as,
                 quasi_immutable_deps):
        self.target_token = target_token
        self.label_op = label_op
        self.extra_same_as = extra_same_as
        self.quasi_immutable_deps = quasi_immutable_deps

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
    * quasi_immutable_deps - for tracking quasi immutables
    """
    
    def __init__(self, end_args, next_iteration_args, virtual_state,
                 exported_infos, short_boxes, renamed_inputargs,
                 short_inputargs, memo):
        self.end_args = end_args
        self.next_iteration_args = next_iteration_args
        self.virtual_state = virtual_state
        self.exported_infos = exported_infos
        self.short_boxes = short_boxes
        self.renamed_inputargs = renamed_inputargs
        self.short_inputargs = short_inputargs
        self.dump(memo)

    def dump(self, memo):
        if have_debug_prints():
            debug_start("jit-log-exported-state")
            debug_print("[" + ", ".join([x.repr_short(memo) for x in self.next_iteration_args]) + "]")
            for box in self.short_boxes:
                debug_print("  " + box.repr(memo))
            debug_stop("jit-log-exported-state")

    def final(self):
        return False
