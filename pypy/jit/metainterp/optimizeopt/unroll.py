from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.optimizeopt.virtualstate import VirtualStateAdder
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.compile import ResumeGuardDescr
from pypy.jit.metainterp.resume import Snapshot
from pypy.jit.metainterp.history import TreeLoop, LoopToken
from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.jit.metainterp.optimizeutil import InvalidLoop, RetraceLoop
from pypy.jit.metainterp.jitexc import JitException
from pypy.jit.metainterp.history import make_hashable_int
from pypy.jit.codewriter.effectinfo import EffectInfo

# Assumptions
# ===========
#
# For this to work some assumptions had to be made about the
# optimizations performed. At least for the optimizations that are
# allowed to operate across the loop boundaries. To enforce this, the
# optimizer chain is recreated at the end of the preamble and only the
# state of the optimizations that fulfill those assumptions are kept.
# Since part of this state is stored in virtuals all OptValue objects
# are also recreated to allow virtuals not supported to be forced.
#
# First of all, the optimizations are not allowed to introduce new
# boxes. It is the unoptimized version of the trace that is inlined to 
# form the second iteration of the loop. Otherwise the
# state of the virtuals would not be updated correctly. Whenever some
# box from the first iteration is reused in the second iteration, it
# is added to the input arguments of the loop as well as to the
# arguments of the jump at the end of the preamble. This means that
# inlining the jump from the unoptimized trace will not work since it
# contains too few arguments.  Instead the jump at the end of the
# preamble is inlined. If the arguments of that jump contains boxes
# that were produced by one of the optimizations, and thus never seen
# by the inliner, the inliner will not be able to inline them. There
# is no way of known what these boxes are supposed to contain in the
# third iteration.
#
# The second assumption is that the state of the optimizer should be the
# same after the second iteration as after the first. This have forced
# us to disable store sinking across loop boundaries. Consider the
# following trace
#
#         [p1, p2]
#         i1 = getfield_gc(p1, descr=nextdescr)
#         i2 = int_sub(i1, 1)
#         i2b = int_is_true(i2)
#         guard_true(i2b) []
#         setfield_gc(p2, i2, descr=nextdescr)
#         p3 = new_with_vtable(ConstClass(node_vtable))
#         jump(p2, p3)
#
# At the start of the preamble, p1 and p2 will be pointers. The
# setfield_gc will be removed by the store sinking heap optimizer, and
# p3 will become a virtual. Jumping to the loop will make p1 a pointer
# and p2 a virtual at the start of the loop. The setfield_gc will now
# be absorbed into the virtual p2 and never seen by the heap
# optimizer. At the end of the loop both p2 and p3 are virtuals, but
# the loop needs p2 to be a pointer to be able to call itself. So it
# is forced producing the operations 
#
#         p2 = new_with_vtable(ConstClass(node_vtable))
#         setfield_gc(p2, i2, descr=nextdescr)
#
# In this case the setfield_gc is not store sinked, which means we are
# not in the same state at the end of the loop as at the end of the
# preamble. When we now call the loop again, the first 4 operations of
# the trace were optimized under the wrong assumption that the
# setfield_gc was store sinked which could lead to errors. In this
# case what would happen is that it would be inserted once more in
# front of the guard. 



# FIXME: Introduce some VirtualOptimizer super class instead

def optimize_unroll(metainterp_sd, loop, optimizations):
    opt = UnrollOptimizer(metainterp_sd, loop, optimizations)
    opt.propagate_all_forward()

class Inliner(object):
    def __init__(self, inputargs, jump_args):
        assert len(inputargs) == len(jump_args)
        self.argmap = {}
        for i in range(len(inputargs)):
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

class UnrollOptimizer(Optimization):
    """Unroll the loop into two iterations. The first one will
    become the preamble or entry bridge (don't think there is a
    distinction anymore)"""
    
    def __init__(self, metainterp_sd, loop, optimizations):
        self.optimizer = Optimizer(metainterp_sd, loop, optimizations)
        self.cloned_operations = []
        for op in self.optimizer.loop.operations:
            newop = op.clone()
            self.cloned_operations.append(newop)
            
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

            loop.preamble.operations = self.optimizer.newoperations

            modifier = VirtualStateAdder(self.optimizer)
            virtual_state = modifier.get_virtual_state(jump_args)
            values = [self.getvalue(arg) for arg in jump_args]
            inputargs = virtual_state.make_inputargs(values)

            self.constant_inputargs = {}
            for box in jump_args: 
                const = self.get_constant_box(box)
                if const:
                    self.constant_inputargs[box] = const

            sb = self.optimizer.produce_short_preamble_ops(inputargs +
                                                 self.constant_inputargs.keys())
            self.short_boxes = sb
            preamble_optimizer = self.optimizer
            loop.preamble.quasi_immutable_deps = (
                self.optimizer.quasi_immutable_deps)
            self.optimizer = self.optimizer.reconstruct_for_next_iteration(sb, jump_args)
            loop.quasi_immutable_deps = self.optimizer.quasi_immutable_deps
        
            initial_inputargs_len = len(inputargs)
            self.inliner = Inliner(loop.inputargs, jump_args)

            start_resumedescr = loop.preamble.start_resumedescr.clone_if_mutable()
            self.start_resumedescr = start_resumedescr
            assert isinstance(start_resumedescr, ResumeGuardDescr)
            snapshot = start_resumedescr.rd_snapshot
            while snapshot is not None:
                snapshot_args = snapshot.boxes 
                new_snapshot_args = []
                for a in snapshot_args:
                    if not isinstance(a, Const):
                        a = loop.preamble.inputargs[jump_args.index(a)]
                    a = self.inliner.inline_arg(a)
                    a = self.getvalue(a).get_key_box()
                    new_snapshot_args.append(a)
                snapshot.boxes = new_snapshot_args
                snapshot = snapshot.prev

            inputargs, short_inputargs, short = self.inline(self.cloned_operations,
                                           loop.inputargs, jump_args,
                                           virtual_state)
            
            #except KeyError:
            #    debug_print("Unrolling failed.")
            #    loop.preamble.operations = None
            #    jumpop.initarglist(jump_args)
            #    preamble_optimizer.send_extra_operation(jumpop)
            #    return
            loop.inputargs = inputargs
            jmp = ResOperation(rop.JUMP, loop.inputargs[:], None)
            jmp.setdescr(loop.token)
            loop.preamble.operations.append(jmp)

            loop.operations = self.optimizer.newoperations

            #short = self.create_short_preamble(loop.preamble, loop)
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
                newargs = [a.clonebox() for a in short_loop.inputargs]
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
                
    def inline(self, loop_operations, loop_args, jump_args, virtual_state):
        inliner = self.inliner

        values = [self.getvalue(arg) for arg in jump_args]
        inputargs = virtual_state.make_inputargs(values)
        short_jumpargs = inputargs[:]
        short_inputargs = virtual_state.make_inputargs(values, keyboxes=True)

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
        
        short = []
        short_seen = {}
        for box, const in self.constant_inputargs.items():
            short_seen[box] = True
            self.short_inliner.argmap[box] = const
        
        for result, op in self.short_boxes.items():
            if op is not None:
                for op in self.getvalue(result).make_guards(result):
                    self.add_op_to_short(op, short, short_seen)

        self.optimizer.flush()

        i = j = 0
        while i < len(self.optimizer.newoperations):
            op = self.optimizer.newoperations[i]
            
            self.boxes_created_this_iteration[op.result] = True
            args = op.getarglist()
            if op.is_guard():
                args = args + op.getfailargs()
            
            for a in args:
                self.import_box(a, inputargs, short, short_jumpargs,
                                jumpargs, short_seen)
            i += 1

            if i == len(self.optimizer.newoperations):
                while j < len(jumpargs):
                    a = jumpargs[j]
                    self.import_box(a, inputargs, short, short_jumpargs,
                                    jumpargs, short_seen)
                    j += 1

        jumpop.initarglist(jumpargs)
        self.optimizer.send_extra_operation(jumpop)
        short.append(ResOperation(rop.JUMP, short_jumpargs, None))

        modifier = VirtualStateAdder(self.optimizer)
        final_virtual_state = modifier.get_virtual_state(original_jumpargs)
        debug_start('jit-log-virtualstate')
        virtual_state.debug_print('Closed loop with ')
        if not virtual_state.generalization_of(final_virtual_state):
            # We ended up with a virtual state that is not compatible
            # and we are thus unable to jump to the start of the loop
            # XXX Is it possible to end up here? If so, consider:
            #    - Fallback on having the preamble jump to itself?
            #    - Would virtual_state.generate_guards make sense here?
            final_virtual_state.debug_print("Bad virtual state at end of loop, ")
            debug_stop('jit-log-virtualstate')
            raise InvalidLoop
        debug_stop('jit-log-virtualstate')
        
        return inputargs, short_inputargs, short

    def add_op_to_short(self, op, short, short_seen):
        if op is None:
            return
        if op.result is not None and op.result in short_seen:
            return self.short_inliner.inline_arg(op.result)
        for a in op.getarglist():
            if not isinstance(a, Const) and a not in short_seen:
                self.add_op_to_short(self.short_boxes[a], short, short_seen)
        if op.is_guard():
            descr = self.start_resumedescr.clone_if_mutable()
            op.setdescr(descr)
            
        short.append(op)
        short_seen[op.result] = True
        newop = self.short_inliner.inline_op(op)
        self.optimizer.send_extra_operation(newop)

        if op.is_ovf():
            # FIXME: ensure that GUARD_OVERFLOW:ed ops not end up here
            guard = ResOperation(rop.GUARD_NO_OVERFLOW, [], None)
            self.add_op_to_short(guard, short, short_seen)

        return newop.result
        
    def import_box(self, box, inputargs, short, short_jumpargs,
                   jumpargs, short_seen):

        if isinstance(box, Const) or box in inputargs:
            return
        if box in self.boxes_created_this_iteration:
            return

        short_op = self.short_boxes[box]
        newresult = self.add_op_to_short(short_op, short, short_seen)
        
        short_jumpargs.append(short_op.result)
        inputargs.append(box)
        box = newresult
        if box in self.optimizer.values:
            box = self.optimizer.values[box].force_box()
        jumpargs.append(box)
        
    def sameop(self, op1, op2):
        if op1.getopnum() != op2.getopnum():
            return False

        args1 = op1.getarglist()
        args2 = op2.getarglist()
        if len(args1) != len(args2):
            return False
        for i in range(len(args1)):
            box1, box2 = args1[i], args2[i]
            val1 = self.optimizer.getvalue(box1)
            val2 = self.optimizer.getvalue(box2)
            if val1.is_constant() and val2.is_constant():
                if not val1.box.same_constant(val2.box):
                    return False
            elif val1 is not val2:
                return False

        if not op1.is_guard():
            descr1 = op1.getdescr()
            descr2 = op2.getdescr()
            if descr1 is not descr2:
                return False

        return True

    def create_short_preamble(self, preamble, loop):
        #return None # Dissable

        preamble_ops = preamble.operations
        loop_ops = loop.operations

        boxmap = BoxMap()
        state = ExeState(self.optimizer)
        short_preamble = []
        loop_i = preamble_i = 0
        while preamble_i < len(preamble_ops):

            op = preamble_ops[preamble_i]
            try:
                newop = self.inliner.inline_op(op, ignore_result=True,
                                               ignore_failargs=True)
            except KeyError:
                debug_print("create_short_preamble failed due to",
                            "new boxes created during optimization.",
                            "op:", op.getopnum(),
                            "at preamble position: ", preamble_i,
                            "loop position: ", loop_i)
                return None
                
            if self.sameop(newop, loop_ops[loop_i]) \
               and loop_i < len(loop_ops):
                try:
                    boxmap.link_ops(op, loop_ops[loop_i])
                except ImpossibleLink:
                    debug_print("create_short_preamble failed due to",
                                "impossible link of "
                                "op:", op.getopnum(),
                                "at preamble position: ", preamble_i,
                                "loop position: ", loop_i)
                    return None
                loop_i += 1
            else:
                if not state.safe_to_move(op):
                    debug_print("create_short_preamble failed due to",
                                "unsafe op:", op.getopnum(),
                                "at preamble position: ", preamble_i,
                                "loop position: ", loop_i)
                    return None
                short_preamble.append(op)
                
            state.update(op)
            preamble_i += 1

        if loop_i < len(loop_ops):
            debug_print("create_short_preamble failed due to",
                        "loop contaning ops not in preamble"
                        "at position", loop_i)
            return None

        
        jumpargs = []
        for i in range(len(loop.inputargs)):
            try:
                jumpargs.append(boxmap.get_preamblebox(loop.inputargs[i]))
            except KeyError:
                debug_print("create_short_preamble failed due to",
                            "input arguments not located")
                return None

        jmp = ResOperation(rop.JUMP, jumpargs[:], None)
        jmp.setdescr(loop.token)
        short_preamble.append(jmp)

        # Check that boxes used as arguemts are produced.
        seen = {}
        for box in preamble.inputargs:
            seen[box] = True
        for op in short_preamble:
            for box in op.getarglist():
                if isinstance(box, Const):
                    continue
                if box not in seen:
                    debug_print("create_short_preamble failed due to",
                                "op arguments not produced")
                    return None
            if op.result:
                seen[op.result] = True
        
        return short_preamble

class ExeState(object):
    def __init__(self, optimizer):
        self.optimizer = optimizer
        self.heap_dirty = False
        self.unsafe_getitem = {}
        self.unsafe_getarrayitem = {}
        self.unsafe_getarrayitem_indexes = {}
        
    # Make sure it is safe to move the instrucions in short_preamble
    # to the top making short_preamble followed by loop equvivalent
    # to preamble
    def safe_to_move(self, op):
        opnum = op.getopnum()
        descr = op.getdescr()
        if op.is_always_pure() or op.is_foldable_guard():
            return True
        elif opnum == rop.JUMP:
            return True
        elif (opnum == rop.GETFIELD_GC or
              opnum == rop.GETFIELD_RAW):
            if self.heap_dirty:
                return False
            if descr in self.unsafe_getitem:
                return False
            return True
        elif (opnum == rop.GETARRAYITEM_GC or
              opnum == rop.GETARRAYITEM_RAW):
            if self.heap_dirty:
                return False
            if descr in self.unsafe_getarrayitem:
                return False
            index = op.getarg(1)
            if isinstance(index, Const):
                d = self.unsafe_getarrayitem_indexes.get(descr, None)
                if d is not None:
                    if index.getint() in d:
                        return False
            else:
                if descr in self.unsafe_getarrayitem_indexes:
                    return False
            return True
        elif opnum == rop.CALL:
            effectinfo = descr.get_extra_info()
            if effectinfo is not None:
                if effectinfo.extraeffect == EffectInfo.EF_LOOPINVARIANT or \
                   effectinfo.extraeffect == EffectInfo.EF_PURE:
                    return True
        return False
    
    def update(self, op):
        if (op.has_no_side_effect() or
            op.is_ovf() or
            op.is_guard()): 
            return
        opnum = op.getopnum()
        descr = op.getdescr()
        if (opnum == rop.DEBUG_MERGE_POINT):
            return
        if (opnum == rop.SETFIELD_GC or
            opnum == rop.SETFIELD_RAW):
            self.unsafe_getitem[descr] = True
            return
        if (opnum == rop.SETARRAYITEM_GC or
            opnum == rop.SETARRAYITEM_RAW):
            index = op.getarg(1)
            if isinstance(index, Const):                
                d = self.unsafe_getarrayitem_indexes.get(descr, None)
                if d is None:
                    d = self.unsafe_getarrayitem_indexes[descr] = {}
                d[index.getint()] = True
            else:
                self.unsafe_getarrayitem[descr] = True
            return
        if opnum == rop.CALL:
            effectinfo = descr.get_extra_info()
            if effectinfo is not None:
                for fielddescr in effectinfo.write_descrs_fields:
                    self.unsafe_getitem[fielddescr] = True
                for arraydescr in effectinfo.write_descrs_arrays:
                    self.unsafe_getarrayitem[arraydescr] = True
                return
        debug_print("heap dirty due to op ", opnum)
        self.heap_dirty = True

class ImpossibleLink(JitException):
    pass

class BoxMap(object):
    def __init__(self):
        self.map = {}

    
    def link_ops(self, preambleop, loopop):
        pargs = preambleop.getarglist()
        largs = loopop.getarglist()
        if len(pargs) != len(largs):
            raise ImpossibleLink
        for i in range(len(largs)):
            pbox, lbox = pargs[i], largs[i]
            self.link_boxes(pbox, lbox)

        if preambleop.result:
            if not loopop.result:
                raise ImpossibleLink
            self.link_boxes(preambleop.result, loopop.result)
        

    def link_boxes(self, pbox, lbox):
        if lbox in self.map:
            if self.map[lbox] is not pbox:
                raise ImpossibleLink
        else:
            if isinstance(lbox, Const):
                if not isinstance(pbox, Const) or not pbox.same_constant(lbox):
                    raise ImpossibleLink
            else:
                self.map[lbox] = pbox


    def get_preamblebox(self, loopbox):
        return self.map[loopbox]

class OptInlineShortPreamble(Optimization):
    def __init__(self, retraced):
        self.retraced = retraced
        self.inliner = None
        
    
    def reconstruct_for_next_iteration(self,  short_boxes, surviving_boxes,
                                       optimizer, valuemap):
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

                    debugmsg = 'Did not match '
                    if sh.virtual_state.generalization_of(virtual_state):
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
                    sh.virtual_state.debug_print(debugmsg)
                    
                    if ok:
                        debug_stop('jit-log-virtualstate')
                        # FIXME: Do we still need the dry run
                        #if self.inline(sh.operations, sh.inputargs,
                        #               op.getarglist(), dryrun=True):
                        try:
                            values = [self.getvalue(arg)
                                      for arg in op.getarglist()]
                            args = sh.virtual_state.make_inputargs(values,
                                                                   keyboxes=True)
                            self.inline(sh.operations, sh.inputargs, args)
                        except InvalidLoop:
                            debug_print("Inlining failed unexpectedly",
                                        "jumping to preamble instead")
                            self.emit_operation(op)
                        else:
                            jumpop = self.optimizer.newoperations.pop()
                            assert jumpop.getopnum() == rop.JUMP
                            for guard in extra_guards:
                                if guard.is_guard():
                                    descr = sh.start_resumedescr.clone_if_mutable()
                                    self.inliner.inline_descr_inplace(descr)
                                    guard.setdescr(descr)
                                    
                                self.emit_operation(guard)
                            self.optimizer.newoperations.append(jumpop)
                        return
                debug_stop('jit-log-virtualstate')
                retraced_count = loop_token.retraced_count
                loop_token.retraced_count += 1
                limit = self.optimizer.metainterp_sd.warmrunnerdesc.memory_manager.retrace_limit
                if not self.retraced and retraced_count<limit:
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
                
        
        
    def inline(self, loop_operations, loop_args, jump_args, dryrun=False):
        self.inliner = inliner = Inliner(loop_args, jump_args)

        for op in loop_operations:
            newop = inliner.inline_op(op)
            if not dryrun:
                self.emit_operation(newop)
            else:
                if not self.is_emittable(newop):
                    return False
        
        return True

    #def inline_arg(self, arg):
    #    if isinstance(arg, Const):
    #        return arg
    #    return self.argmap[arg]
