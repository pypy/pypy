from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.compile import ResumeGuardDescr
from pypy.jit.metainterp.resume import Snapshot
from pypy.jit.metainterp.history import TreeLoop, LoopToken
from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.jit.metainterp.optimizeutil import InvalidLoop, RetraceLoop

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

    def inline_op(self, newop, ignore_result=False, clone=True):
        if clone:
            newop = newop.clone()
        args = newop.getarglist()
        newop.initarglist([self.inline_arg(a) for a in args])

        if newop.is_guard():
            args = newop.getfailargs()
            if args:
                newop.setfailargs([self.inline_arg(a) for a in args])

        if newop.result and not ignore_result:
            old_result = newop.result
            newop.result = newop.result.clonebox()
            self.argmap[old_result] = newop.result

        descr = newop.getdescr()
        if isinstance(descr, ResumeGuardDescr):
            descr.rd_snapshot = self.inline_snapshot(descr.rd_snapshot)

        return newop
    
    def inline_arg(self, arg):
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
            loop.preamble.operations = self.optimizer.newoperations

            self.optimizer = self.optimizer.reconstruct_for_next_iteration()

            jump_args = jumpop.getarglist()
            jumpop.initarglist([])            
            inputargs = self.inline(self.cloned_operations,
                                    loop.inputargs, jump_args)
            loop.inputargs = inputargs
            jmp = ResOperation(rop.JUMP, loop.inputargs[:], None)
            jmp.setdescr(loop.token)
            loop.preamble.operations.append(jmp)

            loop.operations = self.optimizer.newoperations

            short = self.create_short_preamble(loop.preamble, loop)
            if short:
                if False:
                    # FIXME: This should save some memory but requires
                    # a lot of tests to be fixed...
                    loop.preamble.operations = short[:]
                    
                # Turn guards into conditional jumps to the preamble
                for i in range(len(short)):
                    op = short[i]
                    if op.is_guard():
                        op = op.clone()
                        op.setfailargs(loop.preamble.inputargs)
                        op.setjumptarget(loop.preamble.token)
                        short[i] = op

                short_loop = TreeLoop('short preamble')
                short_loop.inputargs = loop.preamble.inputargs[:]
                short_loop.operations = short

                assert isinstance(loop.preamble.token, LoopToken)
                if loop.preamble.token.short_preamble:
                    loop.preamble.token.short_preamble.append(short_loop)
                else:
                    loop.preamble.token.short_preamble = [short_loop]

                # Clone ops and boxes to get private versions and 
                newargs = [a.clonebox() for a in short_loop.inputargs]
                inliner = Inliner(short_loop.inputargs, newargs)
                short_loop.inputargs = newargs
                ops = [inliner.inline_op(op) for op in short_loop.operations]
                short_loop.operations = ops

                # Forget the values to allow them to be freed
                for box in short_loop.inputargs:
                    box.forget_value()
                for op in short_loop.operations:
                    if op.result:
                        op.result.forget_value()
                
                if False:
                    boxmap = {}
                    for i in range(len(short_loop.inputargs)):
                        box = short_loop.inputargs[i]
                        newbox = box.clonebox()
                        boxmap[box] = newbox
                        newbox.forget_value()
                        short_loop.inputargs[i] = newbox
                    for i in range(len(short)):
                        oldop = short[i]
                        op = oldop.clone()
                        args = []
                        for a in op.getarglist():
                            if not isinstance(a, Const):
                                a = boxmap[a]
                            args.append(a)
                        op.initarglist(args)
                        if op.is_guard():
                            args = []
                            for a in op.getfailargs():
                                if not isinstance(a, Const):
                                    a = boxmap[a]
                                args.append(a)
                            op.setfailargs(args)
                        box = op.result
                        if box:
                            newbox = box.clonebox()
                            boxmap[box] = newbox
                            newbox.forget_value()
                            op.result = newbox
                        short[i] = op
                

    def inline(self, loop_operations, loop_args, jump_args):
        self.inliner = inliner = Inliner(loop_args, jump_args)
           
        for v in self.optimizer.values.values():
            v.last_guard_index = -1 # FIXME: Are there any more indexes stored?

        inputargs = []
        seen_inputargs = {}
        for arg in jump_args:
            boxes = []
            self.getvalue(arg).enum_forced_boxes(boxes, seen_inputargs)
            for a in boxes:
                if not isinstance(a, Const):
                    inputargs.append(a)

        # This loop is equivalent to the main optimization loop in
        # Optimizer.propagate_all_forward
        for newop in loop_operations:
            if newop.getopnum() == rop.JUMP:
                newop.initarglist(inputargs)
            newop = inliner.inline_op(newop, clone=False)

            self.optimizer.first_optimization.propagate_forward(newop)

        # Remove jump to make sure forced code are placed before it
        newoperations = self.optimizer.newoperations
        jmp = newoperations[-1]
        assert jmp.getopnum() == rop.JUMP
        self.optimizer.newoperations = newoperations[:-1]

        boxes_created_this_iteration = {}
        jumpargs = jmp.getarglist()

        # FIXME: Should also loop over operations added by forcing things in this loop
        for op in newoperations: 
            boxes_created_this_iteration[op.result] = True
            args = op.getarglist()
            if op.is_guard():
                args = args + op.getfailargs()
            
            for a in args:
                if not isinstance(a, Const) and not a in boxes_created_this_iteration:
                    if a not in inputargs:
                        inputargs.append(a)
                        box = inliner.inline_arg(a)
                        if box in self.optimizer.values:
                            box = self.optimizer.values[box].force_box()
                        jumpargs.append(box)

        jmp.initarglist(jumpargs)
        self.optimizer.newoperations.append(jmp)
        return inputargs

    def sameop(self, op1, op2):
        if op1.getopnum() != op2.getopnum():
            return False
        
        args1 = op1.getarglist()
        args2 = op2.getarglist()
        if len(args1) != len(args2):
            return False
        for i in range(len(args1)):
            box1, box2 = args1[i], args2[i]
            if box1 in self.optimizer.values:
                box1 = self.optimizer.values[box1].force_box()
            if box2 in self.optimizer.values:
                box2 = self.optimizer.values[box2].force_box()

            if box1 is not box2:
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

        state = ExeState()
        short_preamble = []
        loop_i = preamble_i = 0
        while preamble_i < len(preamble_ops)-1:

            op = preamble_ops[preamble_i]
            try:
                newop = self.inliner.inline_op(op, True)
            except KeyError:
                debug_print("create_short_preamble failed due to",
                            "new boxes created during optimization")
                return None
                
            if self.sameop(newop, loop_ops[loop_i]) \
               and loop_i < len(loop_ops)-1:
                loop_i += 1
            else:
                if not state.safe_to_move(op):                    
                    debug_print("create_short_preamble failed due to",
                                "unsafe op:", op.getopnum(),
                                "at position: ", preamble_i)
                    return None
                short_preamble.append(op)
                
            state.update(op)
            preamble_i += 1

        if loop_i < len(loop_ops)-1:
            debug_print("create_short_preamble failed due to",
                        "loop contaning ops not in preamble"
                        "at position", loop_i)
            return None

        jumpargs = [None] * len(loop.inputargs)
        allboxes = preamble.inputargs[:]
        for op in short_preamble:
            if op.result:
                allboxes.append(op.result)
            
        for result in allboxes:
            box = self.inliner.inline_arg(result)
            for i in range(len(loop.inputargs)):
                b = loop.inputargs[i]
                if self.optimizer.getvalue(box) is self.optimizer.getvalue(b):
                    jumpargs[i] = result
                    break
        
        for a in jumpargs:
            if a is None:
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
    def __init__(self):
        self.heap_dirty = False
        self.unsafe_getitem = {}

    # Make sure it is safe to move the instrucions in short_preamble
    # to the top making short_preamble followed by loop equvivalent
    # to preamble
    def safe_to_move(self, op):
        opnum = op.getopnum()
        if op.is_always_pure() or op.is_foldable_guard():
            return True
        elif opnum == rop.JUMP:
            return True
        elif (opnum == rop.GETFIELD_GC or
              opnum == rop.GETFIELD_RAW):
            if self.heap_dirty:
                return False
            descr = op.getdescr()
            if descr in self.unsafe_getitem:
                return False
            return True
        return False
    
    def update(self, op):
        if (op.has_no_side_effect() or
            op.is_ovf() or
            op.is_guard()): 
            return
        opnum = op.getopnum()
        if (opnum == rop.DEBUG_MERGE_POINT):
            return
        if (opnum == rop.SETFIELD_GC or
            opnum == rop.SETFIELD_RAW):
            descr = op.getdescr()
            self.unsafe_getitem[descr] = True
            return
        self.heap_dirty = True

class OptInlineShortPreamble(Optimization):
    def reconstruct_for_next_iteration(self, optimizer, valuemap):
        return self
    
    def propagate_forward(self, op):
        if op.getopnum() == rop.JUMP:
            descr = op.getdescr()
            assert isinstance(descr, LoopToken)
            # FIXME: Use a tree, similar to the tree formed by the full
            # preamble and it's bridges, instead of a list to save time and
            # memory  
            short = descr.short_preamble
            if short:
                for sh in short:                    
                    if self.inline(sh.operations, sh.inputargs,
                                   op.getarglist(), dryrun=True):
                        self.inline(sh.operations, sh.inputargs,
                                   op.getarglist())
                        return
                    
                raise RetraceLoop
        self.emit_operation(op)
                
        
        
    def inline(self, loop_operations, loop_args, jump_args, dryrun=False):
        inliner = Inliner(loop_args, jump_args)

        for op in loop_operations:
            newop = inliner.inline_op(op)
            
            if not dryrun:
                # FIXME: Emit a proper guard instead to move these
                # forceings into the the small bridge back to the preamble
                if newop.is_guard():
                    for box in newop.getfailargs():
                        if box in self.optimizer.values:
                            box = self.optimizer.values[box].force_box()
                
                self.emit_operation(newop)
            else:
                if not self.is_emittable(newop):
                    return False
        
        return True

    def inline_arg(self, arg):
        if isinstance(arg, Const):
            return arg
        return self.argmap[arg]
