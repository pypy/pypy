from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rlib.objectmodel import compute_unique_id
from rpython.jit.backend.llvm.llvm_api import CString

class GuardHandlerBase:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.llvm = dispatcher.llvm
        self.builder = dispatcher.builder
        self.cpu = dispatcher.cpu
        self.debug = dispatcher.debug
        self.func = dispatcher.func
        self.jitframe = dispatcher.jitframe

    def setup_guard(self, op):
        """
        Return basic blocks guard needs to branch to and record metadata
        """
        raise NotImplementedError

    def finalise_guard(self, op, resume, cnd, branch):
        """
        Implement new bailout block or update single bailout as needed,
        record more metadata and position the LLVM instruction builder
        at the start of the resume block
        """
        raise NotImplementedError

    def finalise_bailout(self):
        """
        If using single bailout block, call at the end of op parsing when all
        guards have been seen to update block as needed
        """
        raise NotImplementedError

    def patch_guard(self, faildescr, inputargs):
        """
        Replace a guard with the start of a new bridge and position the LLVM
        instruction builder at the start of the new block
        """
        raise NotImplementedError

class BlockPerGuardImpl(GuardHandlerBase):
    """
    Most basic guard implementation of creating a new bailout block for
    every observed guard, where stores of each failarg into the jitframe
    are hardcoded in each block. Will cause code explosion with a large
    number of guards, but is the simplest to implement and maintain, and has
    little overhead on pypy's side specifically, even if it likely slows down
    LLVM.
    """
    def __init__(self):
        self.bailouts = {} #map guards to their bailout blocks
        self.guard_keys = {}
        self.llvm_failargs = {} #map descrs to a snapshot of their llvm failargs

    def setup_guard(self, op):
        cstring = CString("bailout")
        bailout = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                             cstring.ptr)
        cstring = CString("resume")
        resume = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                             cstring.ptr)
        self.bailouts[op] = bailout

        return (resume, bailout)

    def finalise_guard(self, op, resume, cnd, branch):
        bailout = self.bailouts[op]
        failargs = op.getfailargs()
        descr = op.getdescr()
        self.llvm.PositionBuilderAtEnd(bailout)

        self.llvm_failargs[descr] = [self.dispatcher.ssa_vars[arg]
                                     if arg is not None else arg
                                     for arg in failargs]
        uncast_failargs = [self.dispatcher.uncast(arg, llvm_arg)
                           for arg, llvm_arg in
                           zip(failargs, self.llvm_failargs[descr])
                           if arg is not None]
        descr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                        compute_unique_id(descr), 0)
        self.dispatcher.exit_trace(uncast_failargs, descr_llvm)

        self.guard_keys[descr] = (op, resume, cnd, branch)
        self.llvm.PositionBuilderAtEnd(resume)

    def populate_bailouts(self):
        # This impl doesn't need to do anything at this step
        return

    def patch_guard(self, faildescr, inputargs):
        op, resume, cnd, branch = self.guard_keys[faildescr]
        llvm_failargs = self.llvm_failargs[faildescr]
        bailout = self.bailouts[faildescr]

        self.llvm.PosoitionBuilderBefore(self.builder, branch)
        self.llvm.EraseInstruction(branch)
        cstring = CString("bridge")
        bridge = self.llvm.AppendBasicBlock(self.builder, cstring.ptr)
        self.llvm.BuildCondBr(self.builder, cnd, resume, bridge)

        self.llvm.DeleteBasicBlock(bailout)

        llvm_failargs_no_holes = [arg for arg in llvm_failargs
                                  if arg is not None]
        for c, arg in enumerate(inputargs):
            self.dispatcher.ssa_vars[arg] = llvm_failargs_no_holes[c]

        self.llvm.PositionBuilderAtEnd(self.builder, bridge)

class PhiNodeImpl(GuardHandlerBase):
    """
    Abuse phi nodes by setting a phi per failarg + two more for fail descr
    and number of phi nodes that guard actually has, with the rest set to 0.
    A lot more run time overhead and tracking everything required and is
    incredibly fiddly, but only requires one bailout block for all guards
    in the tree, so is much less prone to code explosion.

    Current impl cannot handle bridges that use failargs that aren't i64, or
    holes in failargs.
    """
    def __init__(self):
        self.guard_blocks = {} #map guard descrs to their blocks
        self.guard_keys = {} #map guard descrs to unique info
        self.llvm_failargs = {} #map guards to llvm values their failargs map to at point of parsing
        self.guards = set() #keep track of seen guards for later
        self.max_failargs = 0 #track max number of failargs seen
        cstring = CString("bailout")
        self.bailout = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                  cstring.ptr)
        self.init_bailout()

    def init_bailout(self):
        self.llvm.PositionBuilderAtEnd(self.builder, self.bailout)
        self.bailout_phis = []
        cstring = CString("descr_phi")
        descr_phi = self.llvm.BuildPhi(self.builder, self.cpu.llvm_int_type,
                                       cstring.ptr)
        self.bailout_phis.append(descr_phi)
        self.llvm.PositionBuilderAtEnd(self.builder, self.dispatcher.entry)

    def setup_guard(self, op):
        self.guards.add(op)
        descr = op.getdescr()
        current_block = self.llvm.GetInsertBlock(self.builder)

        cstring = CString("resume")
        resume = self.llvm.AppendBasicBlock(self.cpu.context,
                                            self.func, cstring.ptr)
        self.guard_blocks[descr] = current_block

        return (resume, self.bailout)

    def finalise_guard(self, op, resume, cnd, branch):
        descr = op.getdescr()
        current_block = self.guard_blocks[descr]
        failargs = op.getfailargs()
        self.llvm.PositionBuilderAtEnd(self.builder, self.bailout)

        num_failargs = len(failargs)
        if num_failargs > self.max_failargs:
            for i in range(num_failargs - self.max_failargs):
                cstring = CString("bailout_phi")
                phi = self.llvm.BuildPhi(self.builder, self.cpu.llvm_int_type,
                                         cstring.ptr)
                self.bailout_phis.append(phi)
            self.max_failargs = num_failargs

        descr_addr = compute_unique_id(descr)
        descr_addr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                             descr_addr, 1)
        self.llvm.AddIncoming(self.bailout_phis[0], descr_addr_llvm, current_block)

        for i in range(1,num_failargs+1):
            arg = failargs[i-1]
            uncast_arg = self.dispatcher.uncast(arg,
                                                self.dispatcher.ssa_vars[arg])
            self.llvm.AddIncoming(self.bailout_phis[i], uncast_arg, current_block)

        self.guard_keys[op.getdescr()] = (op, resume, cnd, branch)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def finalise_bailout(self):
        if len(self.guards) == 0: #is linear loop
            self.llvm.DeleteBasicBlock(self.bailout)
            return
        self.llvm.PositionBuilderAtEnd(self.builder, self.bailout)
        for guard in self.guards:
            failargs = guard.getfailargs()
            num_failargs = len(failargs)
            descr = guard.getdescr()
            block = self.guard_blocks[descr]
            for i in range(self.max_failargs-num_failargs):
                #how far we got + extra phi node we're currently at + 1 for descr phi + 1 for 0 indexing
                indx = num_failargs+i+2
                dummy_value = self.llvm.ConstInt(self.cpu.context,
                                                 0, 0)
                self.llvm.AddIncoming(self.bailout_phis[indx], dummy_value, block)
        if self.max_failargs > 0:
            descr = self.bailout_phis[0]
            self.dispatcher.exit_trace(self.bailout_phis[1:], descr)
        else:
            descr = self.bailout_phis[0]
            self.jitframe.set_elem(descr, 1)
            self.llvm.BuildRet(self.builder, self.jitframe.struct)

    def patch_guard(self, faildescr, inputargs):
        branch, op, cnd, resume = self.guard_keys[faildescr]
        self.guards.remove(op)
        cstring = CString("bridge")
        bridge = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                            cstring.ptr)
        self.llvm.PositionBuilderBefore(self.builder, branch)
        current_block = self.llvm.GetInsertBlock(self.builder)
        self.llvm.EraseInstruction(branch)
        failargs = op.getfailargs()
        num_failargs = len(failargs)
        self.llvm.PositionBuilderAtEnd(self.builder, current_block)
        self.llvm.BuildCondBr(self.builder, cnd, resume, bridge)

        for c, arg in enumerate(inputargs,1):
            phi = self.bailout_phis[c]
            value = self.llvm.getIncomingValueForBlock(phi, current_block)
            self.dispatcher.ssa_vars[arg] = value
        if num_failargs == self.max_failargs:
            self.max_failargs = 0
            for guard in self.guards:
                self.max_failargs = max(len(guard.getfailargs()), self.max_failargs)
            if self.max_failargs < num_failargs:
                for i in range(self.max_failargs, num_failargs):
                    phi = self.bailout_phis[-1]
                    self.bailout_phis.pop()
                    self.llvm.EraseInstruction(phi)
        self.llvm.removePredecessor(self.bailout, current_block)
        block = self.llvm.splitBasicBlockAtPhi(self.bailout)
        terminator = self.llvm.getTerminator(self.bailout)
        self.llvm.EraseInstruction(terminator)
        self.llvm.DeleteBasicBlock(block)

        self.llvm.PositionBuilderAtEnd(self.builder, bridge)

            #arg_array_type = rffi.CArray(self.llvm.ValueRef)
            #arg_array = lltype.malloc(arg_array_type, n=(2+len(failargs)), flavor='raw')
            #ID = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 0)
            #shadow_bytes = self.llvm.ConstInt(self.cpu.llvm_indx_type, 0, 0)
            #arg_array.__setitem__(0, ID)
            #arg_array.__setitem__(1, shadow_bytes)
            #for c, failarg in enumerate(failargs, 2):
                #arg_array.__setitem__(c, self.ssa_vars[failarg])
            #cstring = CString("")
            #self.llvm.BuildCall(self.builder, self.stackmap_intrinsic,
                                #arg_array, 2+len(failargs), cstring.ptr)
            #lltype.free(arg_array, flavor='raw')
