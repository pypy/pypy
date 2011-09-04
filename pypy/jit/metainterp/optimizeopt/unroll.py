from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.metainterp.optimizeopt.virtualstate import VirtualStateAdder, ShortBoxes
from pypy.jit.metainterp.compile import ResumeGuardDescr
from pypy.jit.metainterp.history import TreeLoop, LoopToken
from pypy.jit.metainterp.jitexc import JitException
from pypy.jit.metainterp.optimize import InvalidLoop, RetraceLoop
from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.optimizeopt.generalize import KillHugeIntBounds
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.resume import Snapshot
from pypy.rlib.debug import debug_print
import sys, os

# FIXME: Introduce some VirtualOptimizer super class instead

def optimize_unroll(metainterp_sd, loop, optimizations):
    opt = UnrollOptimizer(metainterp_sd, loop, optimizations)
    opt.propagate_all_forward()

class Inliner(object):
    def __init__(self, inputargs, jump_args):
        assert len(inputargs) == len(jump_args)
        self.argmap = {}
        for i in range(len(inputargs)):
            if inputargs[i] in self.argmap:
                assert self.argmap[inputargs[i]] == jump_args[i]
            else:
                self.argmap[inputargs[i]] = jump_args[i]
        self.snapshot_map = {None: None}

    def inline_op(self, newop, ignore_result=False, clone=True,
                  ignore_failargs=False):
        if clone:
            newop = newop.clone()
        args = newop.getarglist()
        newop.initarglist([self.inline_arg(a) for a in args])

        if newop.is_guard():
            args = newop.getfailargs()
            if args and not ignore_failargs:
                newop.setfailargs([self.inline_arg(a) for a in args])
            else:
                newop.setfailargs([])

        if newop.result and not ignore_result:
            old_result = newop.result
            newop.result = newop.result.clonebox()
            self.argmap[old_result] = newop.result

        self.inline_descr_inplace(newop.getdescr())

        return newop

    def inline_descr_inplace(self, descr):
        if isinstance(descr, ResumeGuardDescr):
            descr.rd_snapshot = self.inline_snapshot(descr.rd_snapshot)

    def inline_arg(self, arg):
        if arg is None:
            return None
        if isinstance(arg, Const):
            return arg
        return self.argmap[arg]

    def inline_snapshot(self, snapshot):
        if snapshot in self.snapshot_map:
            return self.snapshot_map[snapshot]
        boxes = [self.inline_arg(a) for a in snapshot.boxes]
        new_snapshot = Snapshot(self.inline_snapshot(snapshot.prev), boxes)
        self.snapshot_map[snapshot] = new_snapshot
        return new_snapshot

class UnrollableOptimizer(Optimizer):
    def setup(self):
        self.importable_values = {}
        self.emitting_dissabled = False
        self.emitted_guards = 0
        self.emitted_pure_operations = {}

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

    def remember_emitting_pure(self, op):
        self.emitted_pure_operations[op] = True

    def produce_potential_short_preamble_ops(self, sb):
        for op in self.emitted_pure_operations:
            if op.getopnum() == rop.GETARRAYITEM_GC_PURE or \
               op.getopnum() == rop.STRGETITEM or \
               op.getopnum() == rop.UNICODEGETITEM:
                if not self.getvalue(op.getarg(1)).is_constant():
                    continue
            sb.add_potential(op)
        for opt in self.optimizations:
            opt.produce_potential_short_preamble_ops(sb)



class UnrollOptimizer(Optimization):
    """Unroll the loop into two iterations. The first one will
    become the preamble or entry bridge (don't think there is a
    distinction anymore)"""

    def __init__(self, metainterp_sd, loop, optimizations):
        self.optimizer = UnrollableOptimizer(metainterp_sd, loop, optimizations)
        self.cloned_operations = []
        for op in self.optimizer.loop.operations:
            newop = op.clone()
            self.cloned_operations.append(newop)

    def fix_snapshot(self, loop, jump_args, snapshot):
        if snapshot is None:
            return None
        snapshot_args = snapshot.boxes 
        new_snapshot_args = []
        for a in snapshot_args:
            a = self.getvalue(a).get_key_box()
            new_snapshot_args.append(a)
        prev = self.fix_snapshot(loop, jump_args, snapshot.prev)
        return Snapshot(prev, new_snapshot_args)
            
    def propagate_all_forward(self):
        loop = self.optimizer.loop
        jumpop = loop.operations[-1]
        if jumpop.getopnum() == rop.JUMP:
            loop.operations = loop.operations[:-1]
        else:
            loopop = None

        self.optimizer.propagate_all_forward()


        if jumpop:
            assert jumpop.getdescr() is loop.token
            jump_args = jumpop.getarglist()
            jumpop.initarglist([])
            self.optimizer.flush()

            KillHugeIntBounds(self.optimizer).apply()
            
            loop.preamble.operations = self.optimizer.newoperations
            jump_args = [self.getvalue(a).get_key_box() for a in jump_args]

            start_resumedescr = loop.preamble.start_resumedescr.clone_if_mutable()
            self.start_resumedescr = start_resumedescr
            assert isinstance(start_resumedescr, ResumeGuardDescr)
            start_resumedescr.rd_snapshot = self.fix_snapshot(loop, jump_args,
                                                              start_resumedescr.rd_snapshot)

            modifier = VirtualStateAdder(self.optimizer)
            virtual_state = modifier.get_virtual_state(jump_args)
            
            values = [self.getvalue(arg) for arg in jump_args]
            inputargs = virtual_state.make_inputargs(values)
            short_inputargs = virtual_state.make_inputargs(values, keyboxes=True)

            self.constant_inputargs = {}
            for box in jump_args: 
                const = self.get_constant_box(box)
                if const:
                    self.constant_inputargs[box] = const

            sb = ShortBoxes(self.optimizer, inputargs + self.constant_inputargs.keys())
            self.short_boxes = sb
            preamble_optimizer = self.optimizer
            loop.preamble.quasi_immutable_deps = (
                self.optimizer.quasi_immutable_deps)
            self.optimizer = self.optimizer.new()
            loop.quasi_immutable_deps = self.optimizer.quasi_immutable_deps

            logops = self.optimizer.loop.logops
            if logops:
                args = ", ".join([logops.repr_of_arg(arg) for arg in inputargs])
                debug_print('inputargs:       ' + args)
                args = ", ".join([logops.repr_of_arg(arg) for arg in short_inputargs])
                debug_print('short inputargs: ' + args)
                self.short_boxes.debug_print(logops)
                

            # Force virtuals amoung the jump_args of the preamble to get the
            # operations needed to setup the proper state of those virtuals
            # in the peeled loop
            inputarg_setup_ops = []
            preamble_optimizer.newoperations = []
            seen = {}
            for box in inputargs:
                if box in seen:
                    continue
                seen[box] = True
                preamble_value = preamble_optimizer.getvalue(box)
                value = self.optimizer.getvalue(box)
                value.import_from(preamble_value, self.optimizer)
            for box in short_inputargs:
                if box in seen:
                    continue
                seen[box] = True
                value = preamble_optimizer.getvalue(box)
                value.force_box()
            preamble_optimizer.flush()
            inputarg_setup_ops += preamble_optimizer.newoperations

            # Setup the state of the new optimizer by emiting the
            # short preamble operations and discarding the result
            self.optimizer.emitting_dissabled = True
            for op in inputarg_setup_ops:
                self.optimizer.send_extra_operation(op)
            seen = {}
            for op in self.short_boxes.operations():
                self.ensure_short_op_emitted(op, self.optimizer, seen)
                if op and op.result:
                    preamble_value = preamble_optimizer.getvalue(op.result)
                    value = self.optimizer.getvalue(op.result)
                    imp = ValueImporter(self, preamble_value, op)
                    self.optimizer.importable_values[value] = imp
                    newresult = self.optimizer.getvalue(op.result).get_key_box()
                    if newresult is not op.result:
                        self.short_boxes.alias(newresult, op.result)
            self.optimizer.flush()
            self.optimizer.emitting_dissabled = False

            initial_inputargs_len = len(inputargs)
            self.inliner = Inliner(loop.inputargs, jump_args)


            short = self.inline(inputargs, self.cloned_operations,
                                loop.inputargs, short_inputargs,
                                virtual_state)
            
            loop.inputargs = inputargs
            args = [preamble_optimizer.getvalue(self.short_boxes.original(a)).force_box()\
                    for a in inputargs]
            jmp = ResOperation(rop.JUMP, args, None)
            jmp.setdescr(loop.token)
            loop.preamble.operations.append(jmp)

            loop.operations = self.optimizer.newoperations
            maxguards = self.optimizer.metainterp_sd.warmrunnerdesc.memory_manager.max_retrace_guards
            
            if self.optimizer.emitted_guards > maxguards:
                loop.preamble.token.retraced_count = sys.maxint

            if short:
                assert short[-1].getopnum() == rop.JUMP
                short[-1].setdescr(loop.token)

                # Turn guards into conditional jumps to the preamble
                for i in range(len(short)):
                    op = short[i]
                    if op.is_guard():
                        op = op.clone()
                        op.setfailargs(None)
                        descr = self.start_resumedescr.clone_if_mutable()
                        op.setdescr(descr)
                        short[i] = op

                short_loop = TreeLoop('short preamble')
                short_loop.inputargs = short_inputargs
                short_loop.operations = short

                # Clone ops and boxes to get private versions and
                boxmap = {}
                newargs = [None] * len(short_loop.inputargs)
                for i in range(len(short_loop.inputargs)):
                    a = short_loop.inputargs[i]
                    if a in boxmap:
                        newargs[i] = boxmap[a]
                    else:
                        newargs[i] = a.clonebox()
                        boxmap[a] = newargs[i]
                inliner = Inliner(short_loop.inputargs, newargs)
                for box, const in self.constant_inputargs.items():
                    inliner.argmap[box] = const
                short_loop.inputargs = newargs
                ops = [inliner.inline_op(op) for op in short_loop.operations]
                short_loop.operations = ops
                descr = self.start_resumedescr.clone_if_mutable()
                inliner.inline_descr_inplace(descr)
                short_loop.start_resumedescr = descr

                assert isinstance(loop.preamble.token, LoopToken)
                if loop.preamble.token.short_preamble:
                    loop.preamble.token.short_preamble.append(short_loop)
                else:
                    loop.preamble.token.short_preamble = [short_loop]
                short_loop.virtual_state = virtual_state

                # Forget the values to allow them to be freed
                for box in short_loop.inputargs:
                    box.forget_value()
                for op in short_loop.operations:
                    if op.result:
                        op.result.forget_value()

    def inline(self, inputargs, loop_operations, loop_args, short_inputargs, virtual_state):
        inliner = self.inliner

        short_jumpargs = inputargs[:]

        short = self.short = []
        short_seen = self.short_seen = {}
        for box, const in self.constant_inputargs.items():
            short_seen[box] = True

        # This loop is equivalent to the main optimization loop in
        # Optimizer.propagate_all_forward
        jumpop = None
        for newop in loop_operations:
            newop = inliner.inline_op(newop, clone=False)
            if newop.getopnum() == rop.JUMP:
                jumpop = newop
                break

            #self.optimizer.first_optimization.propagate_forward(newop)
            self.optimizer.send_extra_operation(newop)

        self.boxes_created_this_iteration = {}

        assert jumpop
        original_jumpargs = jumpop.getarglist()[:]
        values = [self.getvalue(arg) for arg in jumpop.getarglist()]
        jumpargs = virtual_state.make_inputargs(values)
        jumpop.initarglist(jumpargs)
        jmp_to_short_args = virtual_state.make_inputargs(values, keyboxes=True)
        self.short_inliner = Inliner(short_inputargs, jmp_to_short_args)
        
        for box, const in self.constant_inputargs.items():
            self.short_inliner.argmap[box] = const

        for op in short:
            newop = self.short_inliner.inline_op(op)
            self.optimizer.send_extra_operation(newop)
        
        self.optimizer.flush()

        i = j = 0
        while i < len(self.optimizer.newoperations) or j < len(jumpargs):
            if i == len(self.optimizer.newoperations):
                while j < len(jumpargs):
                    a = jumpargs[j]
                    if self.optimizer.loop.logops:
                        debug_print('J:  ' + self.optimizer.loop.logops.repr_of_arg(a))
                    self.import_box(a, inputargs, short, short_jumpargs,
                                    jumpargs, short_seen)
                    j += 1
            else:
                op = self.optimizer.newoperations[i]

                self.boxes_created_this_iteration[op.result] = True
                args = op.getarglist()
                if op.is_guard():
                    args = args + op.getfailargs()

                if self.optimizer.loop.logops:
                    debug_print('OP: ' + self.optimizer.loop.logops.repr_of_resop(op))
                for a in args:
                    if self.optimizer.loop.logops:
                        debug_print('A:  ' + self.optimizer.loop.logops.repr_of_arg(a))
                    self.import_box(a, inputargs, short, short_jumpargs,
                                    jumpargs, short_seen)
                i += 1

        jumpop.initarglist(jumpargs)
        self.optimizer.send_extra_operation(jumpop)
        short.append(ResOperation(rop.JUMP, short_jumpargs, None))

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
        
        return short

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

    def add_op_to_short(self, op, short, short_seen, emit=True, guards_needed=False):
        if op is None:
            return None
        if op.result is not None and op.result in short_seen:
            if emit:
                return self.short_inliner.inline_arg(op.result)
            else:
                return None
        
        for a in op.getarglist():
            if not isinstance(a, Const) and a not in short_seen:
                self.add_op_to_short(self.short_boxes.producer(a), short, short_seen,
                                     emit, guards_needed)
        if op.is_guard():
            descr = self.start_resumedescr.clone_if_mutable()
            op.setdescr(descr)

        if guards_needed and self.short_boxes.has_producer(op.result):
            value_guards = self.getvalue(op.result).make_guards(op.result)
        else:
            value_guards = []            

        short.append(op)
        short_seen[op.result] = True
        if emit:
            newop = self.short_inliner.inline_op(op)
            self.optimizer.send_extra_operation(newop)
        else:
            newop = None

        if op.is_ovf():
            # FIXME: ensure that GUARD_OVERFLOW:ed ops not end up here
            guard = ResOperation(rop.GUARD_NO_OVERFLOW, [], None)
            self.add_op_to_short(guard, short, short_seen, emit, guards_needed)
        for guard in value_guards:
            self.add_op_to_short(guard, short, short_seen, emit, guards_needed)

        if newop:
            return newop.result
        return None
        
    def import_box(self, box, inputargs, short, short_jumpargs,
                   jumpargs, short_seen):
        if isinstance(box, Const) or box in inputargs:
            return
        if box in self.boxes_created_this_iteration:
            return

        short_op = self.short_boxes.producer(box)
        newresult = self.add_op_to_short(short_op, short, short_seen)

        short_jumpargs.append(short_op.result)
        inputargs.append(box)
        box = newresult
        if box in self.optimizer.values:
            box = self.optimizer.getvalue(box).force_box()
        jumpargs.append(box)
        

class OptInlineShortPreamble(Optimization):
    def __init__(self, retraced):
        self.retraced = retraced

    def new(self):
        return OptInlineShortPreamble(self.retraced)

    def propagate_forward(self, op):
        if op.getopnum() == rop.JUMP:
            loop_token = op.getdescr()
            assert isinstance(loop_token, LoopToken)
            # FIXME: Use a tree, similar to the tree formed by the full
            # preamble and it's bridges, instead of a list to save time and
            # memory. This should also allow better behaviour in
            # situations that the is_emittable() chain currently cant
            # handle and the inlining fails unexpectedly belwo.
            short = loop_token.short_preamble
            if short:
                args = op.getarglist()
                modifier = VirtualStateAdder(self.optimizer)
                virtual_state = modifier.get_virtual_state(args)
                debug_start('jit-log-virtualstate')
                virtual_state.debug_print("Looking for ")

                for sh in short:
                    ok = False
                    extra_guards = []

                    bad = {}
                    debugmsg = 'Did not match '
                    if sh.virtual_state.generalization_of(virtual_state, bad):
                        ok = True
                        debugmsg = 'Matched '
                    else:
                        try:
                            cpu = self.optimizer.cpu
                            sh.virtual_state.generate_guards(virtual_state,
                                                             args, cpu,
                                                             extra_guards)

                            ok = True
                            debugmsg = 'Guarded to match '
                        except InvalidLoop:
                            pass
                    sh.virtual_state.debug_print(debugmsg, bad)
                    
                    if ok:
                        debug_stop('jit-log-virtualstate')

                        values = [self.getvalue(arg)
                                  for arg in op.getarglist()]
                        args = sh.virtual_state.make_inputargs(values,
                                                               keyboxes=True)
                        inliner = Inliner(sh.inputargs, args)
                        
                        for guard in extra_guards:
                            if guard.is_guard():
                                descr = sh.start_resumedescr.clone_if_mutable()
                                inliner.inline_descr_inplace(descr)
                                guard.setdescr(descr)
                            self.emit_operation(guard)
                        
                        try:
                            for shop in sh.operations:
                                newop = inliner.inline_op(shop)
                                self.emit_operation(newop)
                        except InvalidLoop:
                            debug_print("Inlining failed unexpectedly",
                                        "jumping to preamble instead")
                            self.emit_operation(op)
                        return
                debug_stop('jit-log-virtualstate')
                retraced_count = loop_token.retraced_count
                limit = self.optimizer.metainterp_sd.warmrunnerdesc.memory_manager.retrace_limit
                if not self.retraced and retraced_count<limit:
                    loop_token.retraced_count += 1
                    if not loop_token.failed_states:
                        debug_print("Retracing (%d of %d)" % (retraced_count,
                                                              limit))
                        raise RetraceLoop
                    for failed in loop_token.failed_states:
                        if failed.generalization_of(virtual_state):
                            # Retracing once more will most likely fail again
                            break
                    else:
                        debug_print("Retracing (%d of %d)" % (retraced_count,
                                                              limit))

                        raise RetraceLoop
                else:
                    if not loop_token.failed_states:
                        loop_token.failed_states=[virtual_state]
                    else:
                        loop_token.failed_states.append(virtual_state)
        self.emit_operation(op)

class ValueImporter(object):
    def __init__(self, unroll, value, op):
        self.unroll = unroll
        self.preamble_value = value
        self.op = op

    def import_value(self, value):
        value.import_from(self.preamble_value, self.unroll.optimizer)
        self.unroll.add_op_to_short(self.op, self.unroll.short, self.unroll.short_seen, False, True)        
        
