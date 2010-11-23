from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.compile import ResumeGuardDescr
from pypy.jit.metainterp.resume import Snapshot
from pypy.jit.metainterp.history import TreeLoop, LoopToken
from pypy.rlib.debug import debug_start, debug_stop, debug_print

# FXIME: Introduce some VirtualOptimizer super class instead

def optimize_unroll(metainterp_sd, loop, optimizations):
    opt = UnrollOptimizer(metainterp_sd, loop, optimizations)
    opt.propagate_all_forward()

class UnrollOptimizer(Optimization):
    """Unroll the loop into two iterations. The first one will
    become the preamble or entry bridge (don't think there is a
    distinction anymore)"""
    
    def __init__(self, metainterp_sd, loop, optimizations):
        self.optimizer = Optimizer(metainterp_sd, loop, optimizations)
        self.cloned_operations = []
        self.originalop = {}
        for op in self.optimizer.loop.operations:
            newop = op.clone()
            self.cloned_operations.append(newop)
            self.originalop[newop] = op
            
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

            short = self.create_short_preamble(loop.preamble.operations,
                                               loop.preamble.inputargs,
                                               loop.operations,
                                               loop.inputargs,
                                               loop.token)
            if short:
                if False:
                    # FIXME: This should save some memory but requires
                    # a lot of tests to be fixed...
                    loop.preamble.operations = short
                    short_loop = loop.preamble
                else:
                    short_loop = TreeLoop('short preamble')
                    short_loop.inputargs = loop.preamble.inputargs[:]
                    short_loop.operations = short

                assert isinstance(loop.preamble.token, LoopToken)
                loop.preamble.token.short_preamble = short_loop

                # Clone ops and boxes to get private versions and forget the
                # values to allow them to be freed
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
                    box = op.result
                    if box:
                        newbox = box.clonebox()
                        boxmap[box] = newbox
                        newbox.forget_value()
                        op.result = newbox
                    short[i] = op
                

    def inline(self, loop_operations, loop_args, jump_args):
        self.argmap = argmap = {}
        assert len(loop_args) == len(jump_args)
        for i in range(len(loop_args)):
           argmap[loop_args[i]] = jump_args[i]
           
        for v in self.optimizer.values.values():
            v.last_guard_index = -1 # FIXME: Are there any more indexes stored?

        self.snapshot_map = {None: None}
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
            #print 'N:', newop
            if newop.getopnum() == rop.JUMP:
                args = inputargs
            else:
                args = newop.getarglist()
            newop.initarglist([self.inline_arg(a) for a in args])
            
            if newop.result:
                old_result = newop.result
                newop.result = newop.result.clonebox()
                argmap[old_result] = newop.result
            #print 'P:', newop

            descr = newop.getdescr()
            if isinstance(descr, ResumeGuardDescr):
                descr.rd_snapshot = self.inline_snapshot(descr.rd_snapshot)

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
            #print 'E: ', str(op)
            boxes_created_this_iteration[op.result] = True
            args = op.getarglist()
            if op.is_guard():
                args = args + op.getfailargs()
            
            for a in args:
                if not isinstance(a, Const) and not a in boxes_created_this_iteration:
                    if a not in inputargs:
                        inputargs.append(a)
                        box = self.inline_arg(a)
                        if box in self.optimizer.values:
                            box = self.optimizer.values[box].force_box()
                        jumpargs.append(box)

        jmp.initarglist(jumpargs)
        self.optimizer.newoperations.append(jmp)
        return inputargs

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

    def sameop(self, preambleop, loopop):
        #if preambleop.getopnum() != loopop.getopnum():
        #    return False
        #pargs = preambleop.getarglist()
        #largs = loopop.getarglist()
        #if len(pargs) != len(largs):
        #    return False
        try:
            return self.originalop[loopop] is preambleop
        except KeyError:
            return False

    def create_short_preamble(self, preamble, preambleargs,
                              loop, inputargs, token):
        #return None # Dissable

        state = ExeState()
        short_preamble = []
        loop_i = preamble_i = 0
        while preamble_i < len(preamble)-1:
            if self.sameop(preamble[preamble_i], loop[loop_i]) \
               and loop_i < len(loop)-1:
                loop_i += 1
            else:
                if not state.safe_to_move(preamble[preamble_i]):
                    debug_print("create_short_preamble failed due to",
                                "unsafe op:", preamble[preamble_i].getopnum(),
                                "at position: ", preamble_i)
                    return None
                short_preamble.append(preamble[preamble_i])
            state.update(preamble[preamble_i])
            preamble_i += 1


        if loop_i < len(loop)-1:
            debug_print("create_short_preamble failed due to",
                        "loop contaning ops not in preamble"
                        "at position", loop_i)
            return None

        jumpargs = [None] * len(inputargs)
        allboxes = preambleargs[:]
        for op in short_preamble:
            if op.result:
                allboxes.append(op.result)
            
        for result in allboxes:
            box = self.inline_arg(result)
            for i in range(len(inputargs)):
                b = inputargs[i]
                if self.optimizer.getvalue(box) is self.optimizer.getvalue(b):
                    jumpargs[i] = result
                    break
        
        for a in jumpargs:
            if a is None:
                debug_print("create_short_preamble failed due to",
                            "input arguments not located")
                return None

        jmp = ResOperation(rop.JUMP, jumpargs[:], None)
        jmp.setdescr(token)
        short_preamble.append(jmp)

        # FIXME: Turn guards into conditional jumps to the preamble

        # Check that boxes used as arguemts are produced. Might not be
        # needed, but let's play it safe.
        seen = {}
        for box in preambleargs:
            seen[box] = True
        for op in short_preamble:
            for box in op.getarglist():
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
        if op.is_always_pure():
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
            short = descr.short_preamble
            if short:
                self.inline(short.operations, short.inputargs, op.getarglist())
                return
        self.emit_operation(op)
                
        
        
    def inline(self, loop_operations, loop_args, jump_args):
        self.argmap = argmap = {}
        assert len(loop_args) == len(jump_args)
        for i in range(len(loop_args)):
           argmap[loop_args[i]] = jump_args[i]

        for op in loop_operations:
            newop = op.clone()
            args = newop.getarglist()
            newop.initarglist([self.inline_arg(a) for a in args])
            
            if newop.result:
                old_result = newop.result
                newop.result = newop.result.clonebox()
                argmap[old_result] = newop.result

            self.emit_operation(newop)

    def inline_arg(self, arg):
        if isinstance(arg, Const):
            return arg
        return self.argmap[arg]
