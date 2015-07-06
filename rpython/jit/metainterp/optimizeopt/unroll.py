import sys

from rpython.jit.metainterp.history import TargetToken, JitCellToken, Const
from rpython.jit.metainterp.inliner import Inliner
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.optimizeopt.generalize import KillHugeIntBounds
from rpython.jit.metainterp.optimizeopt.optimizer import Optimizer, Optimization
from rpython.jit.metainterp.optimizeopt.virtualstate import (VirtualStateConstructor,
        ShortBoxes, BadVirtualState, VirtualStatesCantMatch)
from rpython.jit.metainterp.resoperation import rop, ResOperation, GuardResOp
from rpython.jit.metainterp.resume import Snapshot
from rpython.jit.metainterp import compile
from rpython.rlib.debug import debug_print, debug_start, debug_stop


# FIXME: Introduce some VirtualOptimizer super class instead

def optimize_unroll(metainterp_sd, jitdriver_sd, loop, optimizations,
                    inline_short_preamble=True, start_state=None,
                    export_state=True):
    opt = UnrollOptimizer(metainterp_sd, jitdriver_sd, loop, optimizations)
    opt.inline_short_preamble = inline_short_preamble
    return opt.propagate_all_forward(start_state, export_state)


class UnrollableOptimizer(Optimizer):
    def setup(self):
        self.importable_values = {}
        self.emitting_dissabled = False
        self.emitted_guards = 0

    def ensure_imported(self, value):
        if not self.emitting_dissabled and value in self.importable_values:
            imp = self.importable_values[value]
            del self.importable_values[value]
            imp.import_value(value)

    def emit_operation(self, op):
        if op.returns_bool_result():
            self.bool_boxes[self.getvalue(op.result)] = None
        if self.emitting_dissabled:
            return
        if op.is_guard():
            self.emitted_guards += 1 # FIXME: can we use counter in self._emit_operation?
        self._emit_operation(op)


class UnrollOptimizer(Optimization):
    """Unroll the loop into two iterations. The first one will
    become the preamble or entry bridge (don't think there is a
    distinction anymore)"""

    inline_short_preamble = True

    def __init__(self, metainterp_sd, jitdriver_sd, loop, optimizations):
        self.optimizer = UnrollableOptimizer(metainterp_sd, jitdriver_sd,
                                             loop, optimizations)
        self.boxes_created_this_iteration = None

    def get_virtual_state(self, args):
        modifier = VirtualStateConstructor(self.optimizer)
        return modifier.get_virtual_state(args)

    def fix_snapshot(self, jump_args, snapshot):
        if snapshot is None:
            return None
        snapshot_args = snapshot.boxes
        new_snapshot_args = []
        for a in snapshot_args:
            a = self.getvalue(a).get_key_box()
            new_snapshot_args.append(a)
        prev = self.fix_snapshot(jump_args, snapshot.prev)
        return Snapshot(prev, new_snapshot_args)

    def propagate_all_forward(self, starting_state, export_state=True):
        self.optimizer.exporting_state = export_state
        loop = self.optimizer.loop
        self.optimizer.clear_newoperations()

        start_label = loop.operations[0]
        if start_label.getopnum() == rop.LABEL:
            loop.operations = loop.operations[1:]
            # We need to emit the label op before import_state() as emitting it
            # will clear heap caches
            self.optimizer.send_extra_operation(start_label)
        else:
            start_label = None

        patchguardop = None
        if len(loop.operations) > 1:
            patchguardop = loop.operations[-2]
            if patchguardop.getopnum() != rop.GUARD_FUTURE_CONDITION:
                patchguardop = None

        jumpop = loop.operations[-1]
        if jumpop.getopnum() == rop.JUMP or jumpop.getopnum() == rop.LABEL:
            loop.operations = loop.operations[:-1]
        else:
            jumpop = None

        self.import_state(start_label, starting_state)
        self.optimizer.propagate_all_forward(clear=False)

        if not jumpop:
            return

        cell_token = jumpop.getdescr()
        assert isinstance(cell_token, JitCellToken)
        stop_label = ResOperation(rop.LABEL, jumpop.getarglist(), None, TargetToken(cell_token))

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
                jumpop = ResOperation(rop.JUMP, stop_label.getarglist(), None,
                                      descr=start_label.getdescr())
                if self.short:
                    # Construct our short preamble
                    self.close_loop(start_label, jumpop, patchguardop)
                else:
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
        if export_state:
            KillHugeIntBounds(self.optimizer).apply()

        loop.operations = self.optimizer.get_newoperations()
        if export_state:
            final_state = self.export_state(stop_label)
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


    def export_state(self, targetop):
        original_jump_args = targetop.getarglist()
        jump_args = [self.getvalue(a).get_key_box() for a in original_jump_args]

        virtual_state = self.get_virtual_state(jump_args)

        values = [self.getvalue(arg) for arg in jump_args]
        inputargs = virtual_state.make_inputargs(values, self.optimizer)
        short_inputargs = virtual_state.make_inputargs(values, self.optimizer, keyboxes=True)

        if self.boxes_created_this_iteration is not None:
            for box in self.inputargs:
                self.boxes_created_this_iteration[box] = None

        short_boxes = ShortBoxes(self.optimizer, inputargs)

        self.optimizer.clear_newoperations()
        for i in range(len(original_jump_args)):
            srcbox = jump_args[i]
            if values[i].is_virtual():
                srcbox = values[i].force_box(self.optimizer)
            if original_jump_args[i] is not srcbox:
                op = ResOperation(rop.SAME_AS, [srcbox], original_jump_args[i])
                self.optimizer.emit_operation(op)
        inputarg_setup_ops = self.optimizer.get_newoperations()

        target_token = targetop.getdescr()
        assert isinstance(target_token, TargetToken)
        targetop.initarglist(inputargs)
        target_token.virtual_state = virtual_state
        target_token.short_preamble = [ResOperation(rop.LABEL, short_inputargs, None)]

        exported_values = {}
        for box in inputargs:
            exported_values[box] = self.optimizer.getvalue(box)
        for op in short_boxes.operations():
            if op and op.result:
                box = op.result
                exported_values[box] = self.optimizer.getvalue(box)

        return ExportedState(short_boxes, inputarg_setup_ops, exported_values)

    def import_state(self, targetop, exported_state):
        if not targetop: # Trace did not start with a label
            self.inputargs = self.optimizer.loop.inputargs
            self.short = None
            self.initial_virtual_state = None
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

        self.short = target_token.short_preamble[:]
        self.short_seen = {}
        self.short_boxes = exported_state.short_boxes
        self.initial_virtual_state = target_token.virtual_state

        for box in self.inputargs:
            preamble_value = exported_state.exported_values[box]
            value = self.optimizer.getvalue(box)
            value.import_from(preamble_value, self.optimizer)

        # Setup the state of the new optimizer by emiting the
        # short operations and discarding the result
        self.optimizer.emitting_dissabled = True
        for op in exported_state.inputarg_setup_ops:
            self.optimizer.send_extra_operation(op)

        seen = {}
        for op in self.short_boxes.operations():
            self.ensure_short_op_emitted(op, self.optimizer, seen)
            if op and op.result:
                preamble_value = exported_state.exported_values[op.result]
                value = self.optimizer.getvalue(op.result)
                if not value.is_virtual() and not value.is_constant():
                    imp = ValueImporter(self, preamble_value, op)
                    self.optimizer.importable_values[value] = imp
                newvalue = self.optimizer.getvalue(op.result)
                newresult = newvalue.get_key_box()
                # note that emitting here SAME_AS should not happen, but
                # in case it does, we would prefer to be suboptimal in asm
                # to a fatal RPython exception.
                if newresult is not op.result and \
                   not self.short_boxes.has_producer(newresult) and \
                   not newvalue.is_constant():
                    op = ResOperation(rop.SAME_AS, [op.result], newresult)
                    self.optimizer._newoperations.append(op)
                    #if self.optimizer.loop.logops:
                    #    debug_print('  Falling back to add extra: ' +
                    #                self.optimizer.loop.logops.repr_of_resop(op))

        self.optimizer.flush()
        self.optimizer.emitting_dissabled = False

    def close_bridge(self, start_label):
        inputargs = self.inputargs
        short_jumpargs = inputargs[:]

        # We dont need to inline the short preamble we are creating as we are conneting
        # the bridge to a different trace with a different short preamble
        self.short_inliner = None

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
        values = [self.getvalue(arg) for arg in jumpop.getarglist()]
        try:
            jumpargs = virtual_state.make_inputargs(values, self.optimizer)
        except BadVirtualState:
            raise InvalidLoop('The state of the optimizer at the end of ' +
                              'peeled loop is inconsistent with the ' +
                              'VirtualState at the beginning of the peeled ' +
                              'loop')
        jumpop.initarglist(jumpargs)

        # Inline the short preamble at the end of the loop
        jmp_to_short_args = virtual_state.make_inputargs(values,
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
        self.short_inliner = Inliner(short_inputargs, jmp_to_short_args)
        self._inline_short_preamble(self.short, self.short_inliner,
                                    patchguardop, self.short_boxes.assumed_classes)

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
        self.short.append(ResOperation(rop.JUMP, short_jumpargs, None, descr=jumpop.getdescr()))

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
        for i in range(len(short)):
            op = short[i]
            if op.is_guard():
                op = op.clone()
                op.setfailargs(None)
                op.setdescr(None) # will be set to a proper descr when the preamble is used
                short[i] = op

        # Clone ops and boxes to get private versions and
        short_inputargs = short[0].getarglist()
        boxmap = {}
        newargs = [None] * len(short_inputargs)
        for i in range(len(short_inputargs)):
            a = short_inputargs[i]
            if a in boxmap:
                newargs[i] = boxmap[a]
            else:
                newargs[i] = a.clonebox()
                boxmap[a] = newargs[i]
        inliner = Inliner(short_inputargs, newargs)
        target_token.assumed_classes = {}
        for i in range(len(short)):
            op = short[i]
            newop = inliner.inline_op(op)
            if op.result and op.result in self.short_boxes.assumed_classes:
                target_token.assumed_classes[newop.result] = self.short_boxes.assumed_classes[op.result]
            short[i] = newop

        # Forget the values to allow them to be freed
        for box in short[0].getarglist():
            box.forget_value()
        for op in short:
            if op.result:
                op.result.forget_value()
        target_token.short_preamble = self.short

    def ensure_short_op_emitted(self, op, optimizer, seen):
        if op is None:
            return
        if op.result is not None and op.result in seen:
            return
        for a in op.getarglist():
            if not isinstance(a, Const) and a not in seen:
                self.ensure_short_op_emitted(self.short_boxes.producer(a), optimizer,
                                             seen)

        #if self.optimizer.loop.logops:
        #    debug_print('  Emitting short op: ' +
        #                self.optimizer.loop.logops.repr_of_resop(op))

        optimizer.send_extra_operation(op)
        seen[op.result] = None
        if op.is_ovf():
            guard = ResOperation(rop.GUARD_NO_OVERFLOW, [], None)
            optimizer.send_extra_operation(guard)
        if self.is_call_pure_with_exception(op):    # only for MemoryError
            guard = ResOperation(rop.GUARD_NO_EXCEPTION, [], None)
            optimizer.send_extra_operation(guard)

    def is_call_pure_with_exception(self, op):
        if op.getopnum() == rop.CALL_PURE:
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
        if op.result is not None and op.result in self.short_seen:
            if emit and self.short_inliner:
                return self.short_inliner.inline_arg(op.result)
            else:
                return None

        for a in op.getarglist():
            if not isinstance(a, Const) and a not in self.short_seen:
                self.add_op_to_short(self.short_boxes.producer(a), emit, guards_needed)
        if op.is_guard():
            op.setdescr(None) # will be set to a proper descr when the preamble is used

        if guards_needed and self.short_boxes.has_producer(op.result):
            value_guards = self.getvalue(op.result).make_guards(op.result)
        else:
            value_guards = []

        self.short.append(op)
        self.short_seen[op.result] = None
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

        short_jumpargs.append(short_op.result)
        inputargs.append(box)
        box = newresult
        if box in self.optimizer.values:
            box = self.optimizer.values[box].force_box(self.optimizer)
        jumpargs.append(box)


    def _import_op(self, op, inputargs, short_jumpargs, jumpargs):
        self.boxes_created_this_iteration[op.result] = None
        args = op.getarglist()
        if op.is_guard():
            args = args + op.getfailargs()

        for a in args:
            self.import_box(a, inputargs, short_jumpargs, jumpargs)

    def jump_to_already_compiled_trace(self, jumpop, patchguardop):
        jumpop = jumpop.clone()
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
            inliner = Inliner(short_inputargs, args)

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
                self._inline_short_preamble(target.short_preamble, inliner,
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

    def _inline_short_preamble(self, short_preamble, inliner, patchguardop,
                               assumed_classes):
        i = 1
        # XXX this is intentiontal :-(. short_preamble can change during the
        # loop in some cases
        while i < len(short_preamble):
            shop = short_preamble[i]
            newop = inliner.inline_op(shop)
            if newop.is_guard():
                if not patchguardop:
                    raise InvalidLoop("would like to have short preamble, but it has a guard and there's no guard_future_condition")
                assert isinstance(newop, GuardResOp)
                assert isinstance(patchguardop, GuardResOp)
                newop.rd_snapshot = patchguardop.rd_snapshot
                newop.rd_frame_info_list = patchguardop.rd_frame_info_list
                newop.setdescr(compile.ResumeAtPositionDescr())
            self.optimizer.send_extra_operation(newop)
            if shop.result in assumed_classes:
                classbox = self.getvalue(newop.result).get_constant_class(self.optimizer.cpu)
                if not classbox or not classbox.same_constant(assumed_classes[shop.result]):
                    raise InvalidLoop('The class of an opaque pointer before the jump ' +
                                      'does not mach the class ' +
                                      'it has at the start of the target loop')
            i += 1


class ValueImporter(object):
    def __init__(self, unroll, value, op):
        self.unroll = unroll
        self.preamble_value = value
        self.op = op

    def import_value(self, value):
        value.import_from(self.preamble_value, self.unroll.optimizer)
        self.unroll.add_op_to_short(self.op, False, True)


class ExportedState(object):
    def __init__(self, short_boxes, inputarg_setup_ops, exported_values):
        self.short_boxes = short_boxes
        self.inputarg_setup_ops = inputarg_setup_ops
        self.exported_values = exported_values
