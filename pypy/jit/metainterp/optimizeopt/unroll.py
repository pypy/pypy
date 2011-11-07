from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.metainterp.optimizeopt.virtualstate import VirtualStateAdder, ShortBoxes
from pypy.jit.metainterp.compile import ResumeGuardDescr
from pypy.jit.metainterp.history import TreeLoop, TargetToken, JitCellToken
from pypy.jit.metainterp.jitexc import JitException
from pypy.jit.metainterp.optimize import InvalidLoop, RetraceLoop
from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.optimizeopt.generalize import KillHugeIntBounds
from pypy.jit.metainterp.inliner import Inliner
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.resume import Snapshot
from pypy.rlib.debug import debug_print
import sys, os

# FIXME: Introduce some VirtualOptimizer super class instead

def optimize_unroll(metainterp_sd, loop, optimizations):
    opt = UnrollOptimizer(metainterp_sd, loop, optimizations)
    opt.propagate_all_forward()

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

    def new(self):
        new = UnrollableOptimizer(self.metainterp_sd, self.loop)
        return self._new(new)


class UnrollOptimizer(Optimization):
    """Unroll the loop into two iterations. The first one will
    become the preamble or entry bridge (don't think there is a
    distinction anymore)"""

    def __init__(self, metainterp_sd, loop, optimizations):
        self.optimizer = UnrollableOptimizer(metainterp_sd, loop, optimizations)

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
            
    def propagate_all_forward(self):
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

        jumpop = loop.operations[-1]
        if jumpop.getopnum() == rop.JUMP:
            loop.operations = loop.operations[:-1]
        else:
            jumpop = None

        self.import_state(start_label)
        self.optimizer.propagate_all_forward(clear=False)

        if not jumpop:
            return 
        if self.jump_to_already_compiled_trace(jumpop):
            # Found a compiled trace to jump to
            if self.did_import:

                self.close_bridge(start_label)
                self.finilize_short_preamble(start_label)
            return

        cell_token = jumpop.getdescr()
        assert isinstance(cell_token, JitCellToken)
        stop_label = ResOperation(rop.LABEL, jumpop.getarglist(), None, TargetToken(cell_token))

        if not self.did_import: # Enforce the previous behaviour of always peeling  exactly one iteration (for now)
            self.optimizer.flush()
            KillHugeIntBounds(self.optimizer).apply()

            loop.operations = self.optimizer.get_newoperations()
            self.export_state(stop_label)
            loop.operations.append(stop_label)            
        else:
            assert stop_label.getdescr().targeting_jitcell_token is start_label.getdescr().targeting_jitcell_token
            jumpop = ResOperation(rop.JUMP, stop_label.getarglist(), None, descr=start_label.getdescr())

            self.close_loop(jumpop)
            self.finilize_short_preamble(start_label)

    def export_state(self, targetop):
        original_jump_args = targetop.getarglist()
        jump_args = [self.getvalue(a).get_key_box() for a in original_jump_args]

        assert self.optimizer.loop.start_resumedescr
        start_resumedescr = self.optimizer.loop.start_resumedescr.clone_if_mutable()
        assert isinstance(start_resumedescr, ResumeGuardDescr)
        start_resumedescr.rd_snapshot = self.fix_snapshot(jump_args, start_resumedescr.rd_snapshot)
        # FIXME: I dont thnik we need fix_snapshot anymore

        modifier = VirtualStateAdder(self.optimizer)
        virtual_state = modifier.get_virtual_state(jump_args)
            
        values = [self.getvalue(arg) for arg in jump_args]
        inputargs = virtual_state.make_inputargs(values, self.optimizer)
        short_inputargs = virtual_state.make_inputargs(values, self.optimizer, keyboxes=True)

        constant_inputargs = {}
        for box in jump_args: 
            const = self.get_constant_box(box)
            if const:
                constant_inputargs[box] = const

        short_boxes = ShortBoxes(self.optimizer, inputargs + constant_inputargs.keys())
        for i in range(len(original_jump_args)):
            if original_jump_args[i] is not jump_args[i]:
                short_boxes.alias(original_jump_args[i], jump_args[i])

        self.optimizer.clear_newoperations()
        for box in short_inputargs:
            value = self.getvalue(box)
            if value.is_virtual():
                value.force_box(self.optimizer)
        inputarg_setup_ops = self.optimizer.get_newoperations()

        target_token = targetop.getdescr()
        assert isinstance(target_token, TargetToken)
        targetop.initarglist(inputargs)
        target_token.virtual_state = virtual_state
        target_token.short_preamble = [ResOperation(rop.LABEL, short_inputargs, None)]
        target_token.start_resumedescr = start_resumedescr
        target_token.exported_state = ExportedState(constant_inputargs, short_boxes,
                                                    inputarg_setup_ops, self.optimizer)

    def import_state(self, targetop):
        self.did_import = False
        if not targetop:
            # FIXME: Set up some sort of empty state with no virtuals?
            return
        target_token = targetop.getdescr()
        if not target_token:
            return
        assert isinstance(target_token, TargetToken)
        exported_state = target_token.exported_state
        if not exported_state:
            # FIXME: Set up some sort of empty state with no virtuals
            return
        self.did_import = True
        
        self.short = target_token.short_preamble
        self.short_seen = {}
        self.short_boxes = exported_state.short_boxes
        for box, const in exported_state.constant_inputargs.items():
            self.short_seen[box] = True
        self.imported_state = exported_state
        self.inputargs = targetop.getarglist()
        self.initial_virtual_state = target_token.virtual_state
        self.start_resumedescr = target_token.start_resumedescr

        seen = {}
        for box in self.inputargs:
            if box in seen:
                continue
            seen[box] = True
            preamble_value = exported_state.optimizer.getvalue(box)
            value = self.optimizer.getvalue(box)
            value.import_from(preamble_value, self.optimizer)

        for newbox, oldbox in self.short_boxes.aliases.items():
            self.optimizer.make_equal_to(newbox, self.optimizer.getvalue(oldbox))
        
        # Setup the state of the new optimizer by emiting the
        # short operations and discarding the result
        self.optimizer.emitting_dissabled = True
        for op in exported_state.inputarg_setup_ops:
            self.optimizer.send_extra_operation(op)
        seen = {}
        for op in self.short_boxes.operations():
            self.ensure_short_op_emitted(op, self.optimizer, seen)
            if op and op.result:
                preamble_value = exported_state.optimizer.getvalue(op.result)
                value = self.optimizer.getvalue(op.result)
                if not value.is_virtual():
                    imp = ValueImporter(self, preamble_value, op)
                    self.optimizer.importable_values[value] = imp
                newvalue = self.optimizer.getvalue(op.result)
                newresult = newvalue.get_key_box()
                if newresult is not op.result and not newvalue.is_constant():
                    self.short_boxes.alias(newresult, op.result)
                    op = ResOperation(rop.SAME_AS, [op.result], newresult)
                    self.optimizer._newoperations = [op] + self.optimizer._newoperations # XXX
                    #self.optimizer.getvalue(op.result).box = op.result # FIXME: HACK!!!
        self.optimizer.flush()
        self.optimizer.emitting_dissabled = False

    def close_bridge(self, start_label):
        inputargs = self.inputargs        
        short_jumpargs = inputargs[:]
        
        newoperations = self.optimizer.get_newoperations()
        self.boxes_created_this_iteration = {}
        i = 0
        while newoperations[i].getopnum() != rop.LABEL:
            i += 1
        while i < len(newoperations):
            op = newoperations[i]
            self.boxes_created_this_iteration[op.result] = True
            args = op.getarglist()
            if op.is_guard():
                args = args + op.getfailargs()
            for a in args:
                self.import_box(a, inputargs, short_jumpargs, [])
            i += 1
            newoperations = self.optimizer.get_newoperations()
        self.short.append(ResOperation(rop.JUMP, short_jumpargs, None, descr=start_label.getdescr()))
        
    def close_loop(self, jumpop):
        virtual_state = self.initial_virtual_state
        short_inputargs = self.short[0].getarglist()
        constant_inputargs = self.imported_state.constant_inputargs
        inputargs = self.inputargs
        short_jumpargs = inputargs[:]

        # Construct jumpargs from the virtual state
        original_jumpargs = jumpop.getarglist()[:]
        values = [self.getvalue(arg) for arg in jumpop.getarglist()]
        jumpargs = virtual_state.make_inputargs(values, self.optimizer)
        jumpop.initarglist(jumpargs)

        # Inline the short preamble at the end of the loop
        jmp_to_short_args = virtual_state.make_inputargs(values, self.optimizer, keyboxes=True)
        self.short_inliner = Inliner(short_inputargs, jmp_to_short_args)
        for box, const in constant_inputargs.items():
            self.short_inliner.argmap[box] = const
        for op in self.short[1:]:
            newop = self.short_inliner.inline_op(op)
            self.optimizer.send_extra_operation(newop)

        # Import boxes produced in the preamble but used in the loop
        newoperations = self.optimizer.get_newoperations()
        self.boxes_created_this_iteration = {}
        i = j = 0
        while newoperations[i].getopnum() != rop.LABEL:
            i += 1
        while i < len(newoperations) or j < len(jumpargs):
            if i == len(newoperations):
                while j < len(jumpargs):
                    a = jumpargs[j]
                    if self.optimizer.loop.logops:
                        debug_print('J:  ' + self.optimizer.loop.logops.repr_of_arg(a))
                    self.import_box(a, inputargs, short_jumpargs, jumpargs)
                    j += 1
            else:
                op = newoperations[i]

                self.boxes_created_this_iteration[op.result] = True
                args = op.getarglist()
                if op.is_guard():
                    args = args + op.getfailargs()

                if self.optimizer.loop.logops:
                    debug_print('OP: ' + self.optimizer.loop.logops.repr_of_resop(op))
                for a in args:
                    if self.optimizer.loop.logops:
                        debug_print('A:  ' + self.optimizer.loop.logops.repr_of_arg(a))
                    self.import_box(a, inputargs, short_jumpargs, jumpargs)
                i += 1
            newoperations = self.optimizer.get_newoperations()

        jumpop.initarglist(jumpargs)
        self.optimizer.send_extra_operation(jumpop)
        self.short.append(ResOperation(rop.JUMP, short_jumpargs, None, descr=jumpop.getdescr()))

        # Verify that the virtual state at the end of the loop is one
        # that is compatible with the virtual state at the start of the loop
        modifier = VirtualStateAdder(self.optimizer)
        final_virtual_state = modifier.get_virtual_state(original_jumpargs)
        debug_start('jit-log-virtualstate')
        virtual_state.debug_print('Closed loop with ')
        bad = {}
        if not virtual_state.generalization_of(final_virtual_state, bad):
            # We ended up with a virtual state that is not compatible
            # and we are thus unable to jump to the start of the loop
            # XXX Is it possible to end up here? If so, consider:
            #    - Fallback on having the preamble jump to itself?
            #    - Would virtual_state.generate_guards make sense here?
            final_virtual_state.debug_print("Bad virtual state at end of loop, ",
                                            bad)
            debug_stop('jit-log-virtualstate')
            raise InvalidLoop
        debug_stop('jit-log-virtualstate')

    def finilize_short_preamble(self, start_label):
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
                descr = target_token.start_resumedescr.clone_if_mutable()
                op.setdescr(descr)
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
        for box, const in self.imported_state.constant_inputargs.items():
            inliner.argmap[box] = const
        for i in range(len(short)):
            short[i] = inliner.inline_op(short[i])

        target_token.start_resumedescr = self.start_resumedescr.clone_if_mutable()            
        inliner.inline_descr_inplace(target_token.start_resumedescr)

        # Forget the values to allow them to be freed
        for box in short[0].getarglist():
            box.forget_value()
        for op in short:
            if op.result:
                op.result.forget_value()
        target_token.short_preamble = self.short
        target_token.exported_state = None

        
    def FIXME_old_stuff():
            preamble_optimizer = self.optimizer
            loop.preamble.quasi_immutable_deps = (
                self.optimizer.quasi_immutable_deps)
            self.optimizer = self.optimizer.new()
            loop.quasi_immutable_deps = self.optimizer.quasi_immutable_deps

            
            loop.inputargs = inputargs
            args = [preamble_optimizer.getvalue(self.short_boxes.original(a)).force_box(preamble_optimizer)\
                    for a in inputargs]
            jmp = ResOperation(rop.JUMP, args, None)
            jmp.setdescr(loop.token)
            loop.preamble.operations.append(jmp)

            loop.operations = self.optimizer.get_newoperations()
            maxguards = self.optimizer.metainterp_sd.warmrunnerdesc.memory_manager.max_retrace_guards
            
            if self.optimizer.emitted_guards > maxguards:
                loop.preamble.token.retraced_count = sys.maxint

            if short:
                pass

    def ensure_short_op_emitted(self, op, optimizer, seen):
        if op is None:
            return
        if op.result is not None and op.result in seen:
            return
        for a in op.getarglist():
            if not isinstance(a, Const) and a not in seen:
                self.ensure_short_op_emitted(self.short_boxes.producer(a), optimizer, seen)
        optimizer.send_extra_operation(op)
        seen[op.result] = True
        if op.is_ovf():
            guard = ResOperation(rop.GUARD_NO_OVERFLOW, [], None)
            optimizer.send_extra_operation(guard)

    def add_op_to_short(self, op, emit=True, guards_needed=False):
        if op is None:
            return None
        if op.result is not None and op.result in self.short_seen:
            if emit:
                return self.short_inliner.inline_arg(op.result)
            else:
                return None
        
        for a in op.getarglist():
            if not isinstance(a, Const) and a not in self.short_seen:
                self.add_op_to_short(self.short_boxes.producer(a), emit, guards_needed)
        if op.is_guard():
            descr = self.start_resumedescr.clone_if_mutable()
            op.setdescr(descr)

        if guards_needed and self.short_boxes.has_producer(op.result):
            value_guards = self.getvalue(op.result).make_guards(op.result)
        else:
            value_guards = []            

        self.short.append(op)
        self.short_seen[op.result] = True
        if emit:
            newop = self.short_inliner.inline_op(op)
            self.optimizer.send_extra_operation(newop)
        else:
            newop = None

        if op.is_ovf():
            # FIXME: ensure that GUARD_OVERFLOW:ed ops not end up here
            guard = ResOperation(rop.GUARD_NO_OVERFLOW, [], None)
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

    def jump_to_already_compiled_trace(self, jumpop):
        assert jumpop.getopnum() == rop.JUMP
        cell_token = jumpop.getdescr()

        assert isinstance(cell_token, JitCellToken)
        if not cell_token.target_tokens:
            return False

        args = jumpop.getarglist()
        modifier = VirtualStateAdder(self.optimizer)
        virtual_state = modifier.get_virtual_state(args)
        debug_start('jit-log-virtualstate')
        virtual_state.debug_print("Looking for ")

        for target in cell_token.target_tokens:
            if not target.virtual_state:
                continue
            ok = False
            extra_guards = []

            bad = {}
            debugmsg = 'Did not match '
            if target.virtual_state.generalization_of(virtual_state, bad):
                ok = True
                debugmsg = 'Matched '
            else:
                try:
                    cpu = self.optimizer.cpu
                    target.virtual_state.generate_guards(virtual_state,
                                                         args, cpu,
                                                         extra_guards)

                    ok = True
                    debugmsg = 'Guarded to match '
                except InvalidLoop:
                    pass
            target.virtual_state.debug_print(debugmsg, bad)

            if ok:
                debug_stop('jit-log-virtualstate')

                values = [self.getvalue(arg)
                          for arg in jumpop.getarglist()]
                args = target.virtual_state.make_inputargs(values, self.optimizer,
                                                           keyboxes=True)
                short_inputargs = target.short_preamble[0].getarglist()
                inliner = Inliner(short_inputargs, args)

                for guard in extra_guards:
                    if guard.is_guard():
                        descr = target.start_resumedescr.clone_if_mutable()
                        inliner.inline_descr_inplace(descr)
                        guard.setdescr(descr)
                    self.optimizer.send_extra_operation(guard)

                try:
                    for shop in target.short_preamble[1:]:
                        newop = inliner.inline_op(shop)
                        self.optimizer.send_extra_operation(newop)
                except InvalidLoop:
                    debug_print("Inlining failed unexpectedly",
                                "jumping to preamble instead")
                    assert cell_token.target_tokens[0].virtual_state is None
                    jumpop.setdescr(cell_token.target_tokens[0])
                    self.optimizer.send_extra_operation(jumpop)
                return True
        debug_stop('jit-log-virtualstate')

        retraced_count = cell_token.retraced_count
        limit = self.optimizer.metainterp_sd.warmrunnerdesc.memory_manager.retrace_limit
        if retraced_count<limit:
            debug_print('Retracing (%d/%d)', retraced_count, limit)
            cell_token.retraced_count += 1
            return False

        
# FIXME: kill
class OptInlineShortPreamble(Optimization):
    def __init__(self, retraced):
        self.retraced = retraced

    def new(self):
        return OptInlineShortPreamble(self.retraced)

    def propagate_forward(self, op):
            ## # We should not be failing much anymore...
            ##     if not procedure_token.failed_states:
            ##         debug_print("Retracing (%d of %d)" % (retraced_count,
            ##                                               limit))
            ##         raise RetraceLoop
            ##     for failed in loop_token.failed_states:
            ##         if failed.generalization_of(virtual_state):
            ##             # Retracing once more will most likely fail again
            ##             break
            ##     else:
            ##         debug_print("Retracing (%d of %d)" % (retraced_count,
            ##                                               limit))

            ##         raise RetraceLoop
            ## else:
            ##     if not loop_token.failed_states:
            ##         loop_token.failed_states=[virtual_state]
            ##     else:
            ##         loop_token.failed_states.append(virtual_state)
            self.emit_operation(op)


class ValueImporter(object):
    def __init__(self, unroll, value, op):
        self.unroll = unroll
        self.preamble_value = value
        self.op = op

    def import_value(self, value):
        value.import_from(self.preamble_value, self.unroll.optimizer)
        self.unroll.add_op_to_short(self.op, False, True)        

class ExportedState(object):
    def __init__(self, constant_inputargs,
                 short_boxes, inputarg_setup_ops, optimizer):
        self.constant_inputargs = constant_inputargs
        self.short_boxes = short_boxes
        self.inputarg_setup_ops = inputarg_setup_ops
        self.optimizer = optimizer
        
