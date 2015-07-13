import sys

from rpython.jit.metainterp.history import TargetToken, JitCellToken, Const
from rpython.jit.metainterp.optimizeopt.shortpreamble import ShortBoxes
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.optimizeopt import info, intutils
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer,\
     Optimization, LoopInfo, MININT, MAXINT
from rpython.jit.metainterp.optimizeopt.virtualstate import (VirtualStateConstructor,
        BadVirtualState, VirtualStatesCantMatch)
from rpython.jit.metainterp.resoperation import rop, ResOperation,\
     OpHelpers, AbstractInputArg, GuardResOp, AbstractResOp
from rpython.jit.metainterp import compile
from rpython.rlib.debug import debug_print, debug_start, debug_stop



class PreambleOp(AbstractResOp):
    """ An operations that's only found in preamble and not
    in the list of constructed operations. When encountered (can be found
    either in pure ops or heap ops), it must be put in inputargs as well
    as short preamble (together with corresponding guards). Extra_ops is
    for extra things to be found in the label, for now only inputargs
    of the preamble that have to be propagated further.

    See force_op_from_preamble for details how the extra things are put.
    """
    
    def __init__(self, op, preamble_op, info):
        self.op = op
        self.preamble_op = preamble_op
        self.info = info

    def getarg(self, i):
        return self.op.getarg(i)

    def __repr__(self):
        return "Preamble(%r)" % (self.op,)


class UnrollableOptimizer(Optimizer):
    def force_op_from_preamble(self, preamble_op):
        op = preamble_op.op
        self.optunroll.short.append(preamble_op.preamble_op)
        if preamble_op.info:
            preamble_op.info.make_guards(op, self.optunroll.short)
        return op

    def setinfo_from_preamble(self, op, preamble_info):
        op = self.get_box_replacement(op)
        if isinstance(preamble_info, info.PtrInfo):
            if preamble_info.is_virtual():
                # XXX do we want to sanitize this?
                op.set_forwarded(preamble_info)
                return
            if op.is_constant():
                return # nothing we can learn
            known_class = preamble_info.get_known_class(self.cpu)
            if known_class:
                self.make_constant_class(op, known_class, False)
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

    inline_short_preamble = True
    ops_to_import = None

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
    
    def optimize_preamble(self, start_label, end_label, ops):
        self._check_no_forwarding([[start_label, end_label], ops])
        info, newops = self.optimizer.propagate_all_forward(
            start_label.getarglist()[:], ops)
        exported_state = self.export_state(start_label, end_label,
                                           info.inputargs)
        # we need to absolutely make sure that we've cleaned up all
        # the optimization info
        self.optimizer._clean_optimization_info(self.optimizer._newoperations)
        return exported_state, self.optimizer._newoperations

    def optimize_peeled_loop(self, start_label, end_jump, ops, state):
        self.short = []
        self.extra_label_args = []
        self._check_no_forwarding([[start_label, end_jump], ops])
        self.import_state(start_label, state)
        self.optimizer.propagate_all_forward(start_label.getarglist()[:], ops,
                                             rename_inputargs=False)
        jump_args = [self.get_box_replacement(op)
                     for op in end_jump.getarglist()]
        args_from_extras = [self.get_box_replacement(op) for op in
                            self.extra_label_args]
        jump_args = state.virtual_state.make_inputargs(jump_args,
                    self.optimizer, force_boxes=True) + args_from_extras
        
        jump_op = ResOperation(rop.JUMP, jump_args)
        self.optimizer._newoperations.append(jump_op)
        return (UnrollInfo(self.make_short_preamble(start_label.getarglist()),
                           self.extra_label_args),
                self.optimizer._newoperations)

    def make_short_preamble(self, args):
        label = ResOperation(rop.LABEL, args)
        short = [label] + self.short
        return short

    def random_garbage(self):
        # WTF is the rest of this function
        if not jumpop:
            return

        cell_token = jumpop.getdescr()
        assert isinstance(cell_token, JitCellToken)
        stop_label = ResOperation(rop.LABEL, jumpop.getarglist(), TargetToken(cell_token))

        if jumpop.getopnum() == rop.JUMP:
            if self.jump_to_already_compiled_trace(jumpop, patchguardop):
                # Found a compiled trace to jump to
                if self.short:
                    # Construct our short preamble
                    assert start_label
                    self.close_bridge(start_label)
                return

            if start_label and self.jump_to_start_label(start_label, stop_label):
                # Initial label matches, jump to it
                vs = start_label.getdescr().virtual_state
                if vs is not None:
                    args = vs.make_inputargs(stop_label.getarglist(),
                                             self.optimizer)
                else:
                    args = stop_label.getarglist()
                jumpop = ResOperation(rop.JUMP, args,
                                      descr=start_label.getdescr())
                #if self.short:
                #    # Construct our short preamble
                #    self.close_loop(start_label, jumpop, patchguardop)
                #else:
                start_label.getdescr().short_preamble = self.short
                self.optimizer.send_extra_operation(jumpop)
                return

            if cell_token.target_tokens:
                limit = self.optimizer.metainterp_sd.warmrunnerdesc.memory_manager.retrace_limit
                if cell_token.retraced_count < limit:
                    cell_token.retraced_count += 1
                    debug_print('Retracing (%d/%d)' % (cell_token.retraced_count, limit))
                else:
                    debug_print("Retrace count reached, jumping to preamble")
                    assert cell_token.target_tokens[0].virtual_state is None
                    jumpop = jumpop.clone()
                    jumpop.setdescr(cell_token.target_tokens[0])
                    self.optimizer.send_extra_operation(jumpop)
                    return

        # Found nothing to jump to, emit a label instead

        if self.short:
            # Construct our short preamble
            assert start_label
            self.close_bridge(start_label)

        self.optimizer.flush()

        loop.operations = self.optimizer.get_newoperations()
        if export_state:
            jd_sd = self.optimizer.jitdriver_sd
            try:
                threshold = jd_sd.warmstate.disable_unrolling_threshold
            except AttributeError:    # tests only
                threshold = sys.maxint
            if len(loop.operations) > threshold:
                if loop.operations[0].getopnum() == rop.LABEL:
                    # abandoning unrolling, too long
                    new_descr = stop_label.getdescr()
                    if loop.operations[0].getopnum() == rop.LABEL:
                        new_descr = loop.operations[0].getdescr()
                    stop_label = stop_label.copy_and_change(rop.JUMP,
                                        descr=new_descr)
                    self.optimizer.send_extra_operation(stop_label)
                    loop.operations = self.optimizer.get_newoperations()
                    return None
            final_state = self.export_state(start_label, stop_label)
        else:
            final_state = None
        loop.operations.append(stop_label)
        return final_state

    def jump_to_start_label(self, start_label, stop_label):
        if not start_label or not stop_label:
            return False

        stop_target = stop_label.getdescr()
        start_target = start_label.getdescr()
        assert isinstance(stop_target, TargetToken)
        assert isinstance(start_target, TargetToken)
        return stop_target.targeting_jitcell_token is start_target.targeting_jitcell_token

    def export_state(self, start_label, end_label, renamed_inputargs):
        original_label_args = end_label.getarglist()
        end_args = [self.get_box_replacement(a) for a in original_label_args]
        virtual_state = self.get_virtual_state(end_args)
        sb = ShortBoxes()
        sb.create_short_boxes(self.optimizer, end_args)
        inparg_mapping = [(start_label.getarg(i), end_args[i])
                          for i in range(len(end_args)) if
                          start_label.getarg(i) is not end_args[i]]
        infos = {}
        for arg in end_args:
            infos[arg] = self.optimizer.getinfo(arg)
        for box in sb.short_boxes:
            infos[box] = self.optimizer.getinfo(box)
        label_args = virtual_state.make_inputargs(end_args, self.optimizer)
        self.optimizer._clean_optimization_info(end_args)
        self.optimizer._clean_optimization_info(start_label.getarglist())
        return ExportedState(label_args, inparg_mapping, virtual_state, infos,
                             sb.short_boxes, renamed_inputargs)


        inputargs = virtual_state.make_inputargs(jump_args, self.optimizer)
        short_inputargs = virtual_state.make_inputargs(jump_args,
                                            self.optimizer, keyboxes=True)

        #proven_constants = []
        #for i in range(len(original_jump_args)):
        #    srcbox = jump_args[i]
        ##    if srcbox is not original_jump_args[i]:
        #        if srcbox.type == 'r':
        #            info = self.optimizer.getptrinfo(srcbox)
        #            if info and info.is_virtual():
        #                xxx
        #    if original_jump_args[i] is not srcbox and srcbox.is_constant():
        #        proven_constants.append((original_jump_args[i], srcbox))
                #opnum = OpHelpers.same_as_for_type(original_jump_args[i].type)
                #op = ResOperation(opnum, [srcbox])
                #self.optimizer.emit_operation(op)
            
        #     if srcbox.type != 'r':
        #         continue
        #     info = self.optimizer.getptrinfo(srcbox)
        #     if info and info.is_virtual():
        #         xxx
        #         srcbox = values[i].force_box(self.optimizer)
        #     if original_jump_args[i] is not srcbox:
        #         opnum = OpHelpers.same_as_for_type(original_jump_args[i].type)
        #         op = self.optimizer.replace_op_with(original_jump_args[i],
        #                                             opnum, [srcbox],
        #                                             descr=DONT_CHANGE)
        #         self.optimizer.emit_operation(op)
        #inputarg_setup_ops = original_jump_args
        #inputarg_setup_ops = self.optimizer.get_newoperations()

        target_token.short_preamble = [ResOperation(rop.LABEL, short_inputargs, None)]

        #exported_values = {}
        #for box in inputargs:
        #    exported_values[box] = self.optimizer.getinfo(box)
        #for op in short_boxes.operations():
        #    if op and op.type != 'v':
        #        exported_values[op] = self.optimizer.getinfo(op)

        return ExportedState([], [])

    def import_state(self, targetop, exported_state):
        # the mapping between input args (from old label) and what we need
        # to actually emit. Update the info
        self.ops_to_import = {}
        for source, target in exported_state.inputarg_mapping:
            if source is not target:
                source.set_forwarded(target)
            info = exported_state.exported_infos.get(target, None)
            if info is not None:
                self.optimizer.setinfo_from_preamble(source, info)
        # import the optimizer state, starting from boxes that can be produced
        # by short preamble
        for op, preamble_op in exported_state.short_boxes.items():
            self.ops_to_import[op] = preamble_op
            if preamble_op.is_always_pure():
                self.pure(op.getopnum(), PreambleOp(op, preamble_op,
                                exported_state.exported_infos.get(op, None)))
            else:
                assert preamble_op.is_getfield()
                optheap = self.optimizer.optheap
                if optheap is None:
                    continue
                opinfo = self.optimizer.ensure_ptr_info_arg0(preamble_op)
                pre_info = exported_state.exported_infos[op]
                pop = PreambleOp(op, preamble_op, pre_info)
                assert not opinfo.is_virtual()
                opinfo._fields[preamble_op.getdescr().get_index()] = pop

        return
        self.inputargs = targetop.getarglist()
        target_token = targetop.getdescr()
        assert isinstance(target_token, TargetToken)
        if not exported_state:
            # No state exported, construct one without virtuals
            self.short = None
            virtual_state = self.get_virtual_state(self.inputargs)
            self.initial_virtual_state = virtual_state
            return

        self.short = [] # target_token.short_preamble[:]
        #self.short_seen = {}
        self.initial_virtual_state = target_token.virtual_state

        #inpargs = self.initial_virtual_state.make_inputargs(
        #    exported_state.orig_inputargs, self.optimizer)
        #for i, arg in enumerate(inpargs):
        #    if arg is not self.inputargs[i]:
        #        arg.set_forwarded(self.inputargs[i])
        #for box in self.inputargs:
        #    preamble_info = exported_state.exported_values[box]
        #    self.optimizer.setinfo_from_preamble(box, preamble_info)
        #for box, const in exported_state.state:
        #    box.set_forwarded(const)

        # Setup the state of the new optimizer by emiting the
        # short operations and discarding the result
        #self.optimizer.emitting_dissabled = True
        # think about it, it seems to be just for consts
        #for source, target in exported_state.inputarg_setup_ops:
        #    source.set_forwarded(target)
        for source, target in exported_state.inputarg_mapping:
            source.set_forwarded(target)

        for op, preamble_op in exported_state.short_boxes.iteritems():
            if preamble_op.is_always_pure():
                self.pure(op.getopnum(), PreambleOp(op, None))
            else:
                xxx
        return
        seen = {}
        for op in self.short_boxes.operations():
            yyy
            self.ensure_short_op_emitted(op, self.optimizer, seen)
            if op and op.type != 'v':
                preamble_value = exported_state.exported_values[op]
                continue
                value = self.optimizer.getvalue(op)
                if not value.is_virtual() and not value.is_constant():
                    imp = ValueImporter(self, preamble_value, op)
                    self.optimizer.importable_values[value] = imp
                newvalue = self.optimizer.getvalue(op)
                newresult = newvalue.get_key_box()
                # note that emitting here SAME_AS should not happen, but
                # in case it does, we would prefer to be suboptimal in asm
                # to a fatal RPython exception.
                # XXX investigate what is it
                xxxx
                if source_op is not op and \
                   not self.short_boxes.has_producer(newresult) and \
                   not newvalue.is_constant():
                    xxx
                    opnum = OpHelpers.same_as_for_type(op.type)
                    op = ResOperation(opnum, [op])
                    self.optimizer._newoperations.append(op)
                    #if self.optimizer.loop.logops:
                    #    debug_print('  Falling back to add extra: ' +
                    #                self.optimizer.loop.logops.repr_of_resop(op))

        #self.optimizer.flush()
        #self.optimizer.emitting_dissabled = False

    def close_bridge(self, start_label):
        inputargs = self.inputargs
        short_jumpargs = inputargs[:]

        # We dont need to inline the short preamble we are creating as we are conneting
        # the bridge to a different trace with a different short preamble
        self.memo = None

        newoperations = self.optimizer.get_newoperations()
        self.boxes_created_this_iteration = {}
        i = 0
        while i < len(newoperations):
            self._import_op(newoperations[i], inputargs, short_jumpargs, [])
            i += 1
            newoperations = self.optimizer.get_newoperations()
        self.short.append(ResOperation(rop.JUMP, short_jumpargs, None, descr=start_label.getdescr()))
        self.finalize_short_preamble(start_label)

    def close_loop(self, start_label, jumpop, patchguardop):
        virtual_state = self.initial_virtual_state
        short_inputargs = self.short[0].getarglist()
        inputargs = self.inputargs
        short_jumpargs = inputargs[:]

        # Construct jumpargs from the virtual state
        original_jumpargs = jumpop.getarglist()[:]
        jump_boxes = [self.get_box_replacement(arg) for arg in
                      jumpop.getarglist()]
        try:
            jumpargs = virtual_state.make_inputargs(jump_boxes, self.optimizer)
        except BadVirtualState:
            raise InvalidLoop('The state of the optimizer at the end of ' +
                              'peeled loop is inconsistent with the ' +
                              'VirtualState at the beginning of the peeled ' +
                              'loop')
        jumpop.initarglist(jumpargs)

        # Inline the short preamble at the end of the loop
        jmp_to_short_args = virtual_state.make_inputargs(jump_boxes,
                                                         self.optimizer,
                                                         keyboxes=True)
        assert len(short_inputargs) == len(jmp_to_short_args)
        args = {}
        for i in range(len(short_inputargs)):
            if short_inputargs[i] in args:
                if args[short_inputargs[i]] != jmp_to_short_args[i]:
                    raise InvalidLoop('The short preamble wants the ' +
                                      'same box passed to multiple of its ' +
                                      'inputargs, but the jump at the ' +
                                      'end of this bridge does not do that.')

            args[short_inputargs[i]] = jmp_to_short_args[i]
        self.memo = Memo(short_inputargs, jmp_to_short_args)
        self._inline_short_preamble(self.short, self.memo,
                                    patchguardop,
                                    self.short_boxes.assumed_classes)

        # Import boxes produced in the preamble but used in the loop
        newoperations = self.optimizer.get_newoperations()
        self.boxes_created_this_iteration = {}
        i = j = 0
        while i < len(newoperations) or j < len(jumpargs):
            if i == len(newoperations):
                while j < len(jumpargs):
                    a = jumpargs[j]
                    #if self.optimizer.loop.logops:
                    #    debug_print('J:  ' + self.optimizer.loop.logops.repr_of_arg(a))
                    self.import_box(a, inputargs, short_jumpargs, jumpargs)
                    j += 1
            else:
                self._import_op(newoperations[i], inputargs, short_jumpargs, jumpargs)
                i += 1
            newoperations = self.optimizer.get_newoperations()

        jumpop.initarglist(jumpargs)
        self.optimizer.send_extra_operation(jumpop)
        self.short.append(ResOperation(rop.JUMP, short_jumpargs, descr=jumpop.getdescr()))

        # Verify that the virtual state at the end of the loop is one
        # that is compatible with the virtual state at the start of the loop
        final_virtual_state = self.get_virtual_state(original_jumpargs)
        #debug_start('jit-log-virtualstate')
        #virtual_state.debug_print('Closed loop with ')
        bad = {}
        if not virtual_state.generalization_of(final_virtual_state, bad,
                                               cpu=self.optimizer.cpu):
            # We ended up with a virtual state that is not compatible
            # and we are thus unable to jump to the start of the loop
            #final_virtual_state.debug_print("Bad virtual state at end of loop, ",
            #                                bad)
            #debug_stop('jit-log-virtualstate')
            raise InvalidLoop('The virtual state at the end of the peeled ' +
                              'loop is not compatible with the virtual ' +
                              'state at the start of the loop which makes ' +
                              'it impossible to close the loop')

        #debug_stop('jit-log-virtualstate')

        maxguards = self.optimizer.metainterp_sd.warmrunnerdesc.memory_manager.max_retrace_guards
        if self.optimizer.emitted_guards > maxguards:
            target_token = jumpop.getdescr()
            assert isinstance(target_token, TargetToken)
            target_token.targeting_jitcell_token.retraced_count = sys.maxint

        self.finalize_short_preamble(start_label)

    def finalize_short_preamble(self, start_label):
        short = self.short
        assert short[-1].getopnum() == rop.JUMP
        target_token = start_label.getdescr()
        assert isinstance(target_token, TargetToken)
        # Turn guards into conditional jumps to the preamble
        #for i in range(len(short)):
        #    op = short[i]
        #    if op.is_guard():
                #op = op.clone(self.memo)
                #op.is_source_op = True
        #        op.setfailargs(None)
        #        op.setdescr(None) # will be set to a proper descr when the preamble is used
        #        short[i] = op

        # Clone ops and boxes to get private versions and
        return
        short_inputargs = short[0].getarglist()
        boxmap = {}
        newargs = [None] * len(short_inputargs)
        for i in range(len(short_inputargs)):
            a = short_inputargs[i]
            if a in boxmap:
                newargs[i] = boxmap[a]
            else:
                newargs[i] = a.clone_input_arg()
                boxmap[a] = newargs[i]
        #memo = Memo(short_inputargs, newargs)
        #target_token.assumed_classes = {}
        for i in range(len(short)):
            op = short[i]
            newop = op.clone(memo)
            if newop.is_guard():
                newop.setfailargs(None)
                newop.setdescr(None)
            if op in self.short_boxes.assumed_classes:
                target_token.assumed_classes[newop] = self.short_boxes.assumed_classes[op]
            short[i] = newop

        # Forget the values to allow them to be freed
        for box in short[0].getarglist():
            box.forget_value()
        for op in short:
            op.forget_value()
        target_token.short_preamble = self.short

    def ensure_short_op_emitted(self, op, optimizer, seen):
        if op is None:
            return
        if op.type != 'v' and op in seen:
            return
        for a in op.getarglist():
            if not isinstance(a, Const) and not isinstance(a, AbstractInputArg) and a not in seen:
                self.ensure_short_op_emitted(self.short_boxes.producer(a), optimizer,
                                             seen)

        #if self.optimizer.loop.logops:
        #    debug_print('  Emitting short op: ' +
        #                self.optimizer.loop.logops.repr_of_resop(op))

        optimizer.send_extra_operation(op)
        seen[op] = None
        if op.is_ovf():
            guard = ResOperation(rop.GUARD_NO_OVERFLOW, [])
            optimizer.send_extra_operation(guard)
        if self.is_call_pure_with_exception(op):    # only for MemoryError
            guard = ResOperation(rop.GUARD_NO_EXCEPTION, [], None)
            optimizer.send_extra_operation(guard)

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

    def add_op_to_short(self, op, emit=True, guards_needed=False):
        if op is None:
            return None
        if op is not None and op in self.short_seen:
            if emit and self.memo:
                return self.memo.get(op, op)
            else:
                return None

        for a in op.getarglist():
            if not isinstance(a, Const) and a not in self.short_seen:
                self.add_op_to_short(self.short_boxes.producer(a), emit, guards_needed)
        if op.is_guard():
            op.setdescr(None) # will be set to a proper descr when the preamble is used

        if guards_needed and self.short_boxes.has_producer(op):
            value_guards = self.getvalue(op).make_guards(op)
        else:
            value_guards = []

        self.short.append(op)
        self.short_seen[op] = None
        if emit and self.short_inliner:
            newop = self.short_inliner.inline_op(op)
            self.optimizer.send_extra_operation(newop)
        else:
            newop = None

        if op.is_ovf():
            # FIXME: ensure that GUARD_OVERFLOW:ed ops not end up here
            guard = ResOperation(rop.GUARD_NO_OVERFLOW, [], None)
            self.add_op_to_short(guard, emit, guards_needed)
        if self.is_call_pure_with_exception(op):    # only for MemoryError
            guard = ResOperation(rop.GUARD_NO_EXCEPTION, [], None)
            self.add_op_to_short(guard, emit, guards_needed)
        for guard in value_guards:
            self.add_op_to_short(guard, emit, guards_needed)

        if newop:
            return newop.result
        return None

    def import_box(self, box, inputargs, short_jumpargs, jumpargs):
        if isinstance(box, Const) or box in inputargs:
            return
        if box in self.boxes_created_this_iteration:
            return

        short_op = self.short_boxes.producer(box)
        newresult = self.add_op_to_short(short_op)

        short_jumpargs.append(short_op)
        inputargs.append(box)
        box = newresult
        if box in self.optimizer.values:
            box = self.optimizer.values[box].force_box(self.optimizer)
        jumpargs.append(box)


    def _import_op(self, op, inputargs, short_jumpargs, jumpargs):
        self.boxes_created_this_iteration[op] = None
        args = op.getarglist()
        if op.is_guard():
            args = args + op.getfailargs()

        for a in args:
            self.import_box(a, inputargs, short_jumpargs, jumpargs)

    def jump_to_already_compiled_trace(self, jumpop, patchguardop):
        jumpop = jumpop.copy_and_change(jumpop.getopnum())
        assert jumpop.getopnum() == rop.JUMP
        cell_token = jumpop.getdescr()

        assert isinstance(cell_token, JitCellToken)
        if not cell_token.target_tokens:
            return False

        if not self.inline_short_preamble:
            assert cell_token.target_tokens[0].virtual_state is None
            jumpop.setdescr(cell_token.target_tokens[0])
            self.optimizer.send_extra_operation(jumpop)
            return True

        args = jumpop.getarglist()
        virtual_state = self.get_virtual_state(args)
        values = [self.getvalue(arg)
                  for arg in jumpop.getarglist()]
        debug_start('jit-log-virtualstate')
        virtual_state.debug_print("Looking for ", metainterp_sd=self.optimizer.metainterp_sd)

        for target in cell_token.target_tokens:
            if not target.virtual_state:
                continue
            extra_guards = []

            try:
                cpu = self.optimizer.cpu
                state = target.virtual_state.generate_guards(virtual_state,
                                                             values,
                                                             cpu)

                extra_guards = state.extra_guards
                if extra_guards:
                    debugmsg = 'Guarded to match '
                else:
                    debugmsg = 'Matched '
            except VirtualStatesCantMatch, e:
                debugmsg = 'Did not match:\n%s\n' % (e.msg, )
                target.virtual_state.debug_print(debugmsg, e.state.bad, metainterp_sd=self.optimizer.metainterp_sd)
                continue

            assert patchguardop is not None or (extra_guards == [] and len(target.short_preamble) == 1)

            target.virtual_state.debug_print(debugmsg, {})

            debug_stop('jit-log-virtualstate')

            args = target.virtual_state.make_inputargs(values, self.optimizer,
                                                       keyboxes=True)
            short_inputargs = target.short_preamble[0].getarglist()
            memo = Memo(short_inputargs, args)

            for guard in extra_guards:
                if guard.is_guard():
                    assert isinstance(patchguardop, GuardResOp)
                    assert isinstance(guard, GuardResOp)
                    guard.rd_snapshot = patchguardop.rd_snapshot
                    guard.rd_frame_info_list = patchguardop.rd_frame_info_list
                    guard.setdescr(compile.ResumeAtPositionDescr())
                self.optimizer.send_extra_operation(guard)

            try:
                # NB: the short_preamble ends with a jump
                self._inline_short_preamble(target.short_preamble, memo,
                                            patchguardop,
                                            target.assumed_classes)
            except InvalidLoop:
                #debug_print("Inlining failed unexpectedly",
                #            "jumping to preamble instead")
                assert cell_token.target_tokens[0].virtual_state is None
                jumpop.setdescr(cell_token.target_tokens[0])
                self.optimizer.send_extra_operation(jumpop)
            return True
        debug_stop('jit-log-virtualstate')
        return False

    def _inline_short_preamble(self, short_preamble, memo, patchguardop,
                               assumed_classes):
        i = 1
        # XXX this is intentiontal :-(. short_preamble can change during the
        # loop in some cases
        while i < len(short_preamble):
            shop = short_preamble[i]
            newop = shop.clone(memo)
            if newop.is_guard():
                if not patchguardop:
                    raise InvalidLoop("would like to have short preamble, but it has a guard and there's no guard_future_condition")
                assert isinstance(newop, GuardResOp)
                assert isinstance(patchguardop, GuardResOp)
                newop.rd_snapshot = patchguardop.rd_snapshot
                newop.rd_frame_info_list = patchguardop.rd_frame_info_list
                newop.setdescr(compile.ResumeAtPositionDescr())
            self.optimizer.send_extra_operation(newop)
            if shop in assumed_classes:
                classbox = self.getvalue(newop.result).get_constant_class(self.optimizer.cpu)
                if not classbox or not classbox.same_constant(assumed_classes[shop.result]):
                    raise InvalidLoop('The class of an opaque pointer before the jump ' +
                                      'does not mach the class ' +
                                      'it has at the start of the target loop')
            i += 1


class UnrollInfo(LoopInfo):
    """ A state after optimizing the peeled loop, contains the following:

    * short_preamble - list of operations that go into short preamble
    * extra_label_args - list of extra operations that go into the label
    """
    def __init__(self, short_preamble, extra_label_args):
        self.short_preamble = short_preamble
        self.extra_label_args = extra_label_args
            
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
    """
    
    def __init__(self, end_args, inputarg_mapping, virtual_state,
                 exported_infos, short_boxes, renamed_inputargs):
        self.end_args = end_args
        self.inputarg_mapping = inputarg_mapping
        self.virtual_state = virtual_state
        self.exported_infos = exported_infos
        self.short_boxes = short_boxes
        self.renamed_inputargs = renamed_inputargs
