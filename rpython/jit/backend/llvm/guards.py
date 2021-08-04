from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rlib.objectmodel import compute_unique_id
from rpython.jit.backend.llvm.llvm_api import CString
from rpython.jit.backend.llsupport.jitframe import JITFRAMEPTR
import ctypes

class GuardHandlerBase:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.llvm = dispatcher.llvm
        self.builder = dispatcher.builder
        self.cpu = dispatcher.cpu
        self.debug = self.cpu.debug
        self.func = dispatcher.func
        self.jitframe = dispatcher.jitframe
        self.ssa_vars = dispatcher.ssa_vars

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
    every guard, where stores of each failarg into the jitframe are hardcoded
    in each block. Will cause code explosion with a large number of guards,
    but is the simplest to implement and maintain, and has little overhead
    on pypy's side specifically (but still slows down LLVM).
    """
    def __init__(self, dispatcher):
        GuardHandlerBase.__init__(self, dispatcher)
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
        self.llvm.PositionBuilderAtEnd(self.builder, bailout)


        self.llvm_failargs[descr] = [self.ssa_vars[arg]
                                     if arg is not None else None
                                     for arg in failargs]
        uncast_failargs = [self.dispatcher.uncast(arg, llvm_arg)
                           for arg, llvm_arg in
                           zip(failargs, self.llvm_failargs[descr])
                           if arg is not None]
        descr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                        compute_unique_id(descr), 0)
        # ID = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 0)
        # shadow_bytes = self.llvm.ConstInt(self.cpu.llvm_indx_type, 0, 0)
        # args = [ID, shadow_bytes]+uncast_failargs
        # arg_array = self.dispatcher.rpython_array(args, self.llvm.ValueRef)

        # cstring = CString("")
        # self.llvm.BuildCall(self.builder,
        #                     self.dispatcher.stackmap_intrinsic,
        #                     arg_array, len(args), cstring.ptr)
        # lltype.free(arg_array, flavor='raw')

        self.dispatcher.exit_trace(uncast_failargs, descr_llvm)

        self.guard_keys[descr] = (op, resume, cnd, branch)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def populate_bailouts(self):
        # This impl doesn't need to do anything at this step
        return

    def finalise_bailout(self):
        return

    def patch_guard(self, faildescr, inputargs):
        op, resume, cnd, branch = self.guard_keys[faildescr]
        llvm_failargs = self.llvm_failargs[faildescr]
        bailout = self.bailouts[op]

        self.llvm.PositionBuilderBefore(self.builder, branch)
        cstring = CString("bridge")
        bridge = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                            cstring.ptr)
        self.llvm.BuildCondBr(self.builder, cnd, resume, bridge)
        self.llvm.EraseInstruction(branch)

        self.llvm.DeleteBasicBlock(bailout)

        llvm_failargs_no_holes = [arg for arg in llvm_failargs
                                  if arg is not None]
        for c, arg in enumerate(inputargs):
            self.ssa_vars[arg] = llvm_failargs_no_holes[c]

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
    def __init__(self, dispatcher):
        GuardHandlerBase.__init__(self, dispatcher)
        self.guard_blocks = {} #map guard descrs to their blocks
        self.guard_keys = {} #map guard descrs to unique info
        self.llvm_failargs = {} #map guards to llvm values their failargs map to at point of parsing
        self.guards = set() #keep track of seen guards for later
        self.max_failargs = 0 #track max number of failargs seen
        self.bailout = self.init_bailout()

    def init_bailout(self):
        cstring = CString("bailout")
        bailout = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                  cstring.ptr)
        self.llvm.PositionBuilderAtEnd(self.builder, bailout)
        self.bailout_phis = []
        cstring = CString("descr_phi")
        descr_phi = self.llvm.BuildPhi(self.builder, self.cpu.llvm_int_type,
                                       cstring.ptr)
        self.bailout_phis.append(descr_phi)

        self.llvm.PositionBuilderAtEnd(self.builder, self.dispatcher.entry)
        return bailout

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
                                                self.ssa_vars[arg])
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
        op, resume, cnd, branch = self.guard_keys[faildescr]
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
            self.ssa_vars[arg] = value
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

class StackmapImpl(GuardHandlerBase):
    """
    Branch all guards to a single bailout block which makes a call to the
    LLVM stackmap intrinsic taking every seen failarg as arguments.
    Bailout block then calls back to the runtime which parses out the
    memory locations of the failargs in the live binary and stores them
    in the jitframe itself. Minimal overhead and no code explosion,
    however the stackmap intrinsic is both still experimental and may
    interfere with the optimiser (although *shouldn't* do in our case).
    """
    def __init__(self):
        self.failarg_index = 0
        self.failarg_order = {} #map of llvm failarg values to tuple of index and ref count
        self.llvm_failargs = {}
        self.guard_blocks = {}
        self.guard_keys = {}
        self.bailout = self.init_bailout()

    def init_bailout(self):
        cstring = CString("bailout")
        bailout = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                cstring.ptr)
        self.llvm.PositionBuilderAtEnd(self.builder, bailout)

        cstring = CString("descr_phi")
        self.descr_phi = self.llvm.BuildPhi(self.builder,
                                            self.cpu.llvm_int_type,
                                            cstring.ptr)

        self.llvm.PositionBuilderAtEnd(self.builder, self.dispatcher.entry)
        return bailout

    def setup_guard(self, op):
        current_block = self.llvm.GetInsertBlock(self.builder)
        descr = op.getdescr()
        self.guard_blocks[descr] = current_block

        cstring = CString("resume")
        resume = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                            cstring.ptr)

        return (resume, self.bailout)

    def finalise_guard(self, op, resume, cnd, branch):
        descr = op.getdescr()
        current_block = self.guard_blocks[descr]

        for arg in op.getfailargs():
            if arg is not None:
                llvm_arg = self.ssa_vars[arg]
                if llvm_arg not in self.failarg_order:
                    self.failarg_order[llvm_arg] = (self.failarg_index, 0)
                    self.failarg_index += 1
                else:
                    index, ref_count = self.failarg_order[llvm_arg]
                    self.failarg_order[llvm_arg] = (index, ref_count+1)
                    self.llvm_failargs[descr].append(llvm_arg)
            else:
                self.llvm_failargs[descr].append(None)

        llvm_descr = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                        compute_unique_id(descr), 0)
        self.llvm.AddIncoming(self.descr_phi, llvm_descr, current_block)

        self.guard_keys[descr] = (op, resume, cnd, branch)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def runtime_callback(self, descr_int_ptr, jitframe_ptr):
        descr = ctypes.cast(descr_int_ptr, ctypes.py_object).value
        jitframe = lltype.cast_opaque_ptr(JITFRAMEPTR, jitframe_ptr)
        llvm_failargs = self.llvm_failargs[descr]
        indices = [self.failarg_order[arg][0] for arg in llvm_failargs]

        Stackmap = lltype.Struct("Stackmap",
            ("type", lltype.Char), ("reserved_1", lltype.Char),
            ("size", lltype.Short), ("regnum", lltype.Short),
            ("reserved_2", lltype.Short), ("offset", rffi.INT)
        )
        Locations = lltype.Array()
        #define this struct in wrapper.c and write a function that takes the stackmap addr and
        #index to return the value as needed in C

        for c, index in enumerate(indices): #TODO: not sure if rpython level requires 1 elem offset
            failarg = self.parse_stackmap(index, stackmap)
            #remember to cast failarg
            jitframe.jf_frame[c] = failarg

        jitframe.jf_descr = cast_instance_to_gcref(descr)

    def finalise_bailout(self):
        self.llvm.PositionBuilderAtEnd(self.bailout)

        ID = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 0)
        shadow_bytes = self.llvm.ConstInt(self.cpu.llvm_indx_type, 0, 0)
        args = [ID, shadow_bytes]+list(self.failarg_order.keys())
        arg_array = self.dispatcher.rpython_array(args, self.llvm.ValueRef)

        cstring = CString("")
        self.llvm.BuildCall(self.builder,
                            self.dispatcher.stackmap_intrinsic,
                            arg_array, self.failarg_index, cstring.ptr)
        lltype.free(arg_array, flavor='raw')

        arg_types = []
        ret_type = lltype.Void
        callback_int_ptr = self.dispatcher.get_func_ptr(self.runtime_callback,
                                                    arg_types, ret_type)
        callback_int_ptr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                callback_int_ptr, 0)
        arg_types_llvm = [self.cpu.llvm_int_type, self.cpu.llvm_void_ptr]
        args_llvm = [self.descr_phi, self.jitframe.struct]
        ret_type_llvm = self.cpu.llvm_void_type
        self.dispatcher.call_function(callback_int_ptr_llvm, ret_type_llvm,
                                        arg_types_llvm, args_llvm, "")

        self.jitframe.set_elem(self.descr_phi, 1)
        self.llvm.BuildRet(self.builder, self.jitframe.struct)

    def patch_guard(self, faildescr, inputargs):
        op, resume, cnd, branch = self.guard_keys[faildescr]
        current_block = self.guard_blocks[faildescr]
        llvm_failargs = self.llvm_failargs[faildescr]

        self.llvm.PosoitionBuilderBefore(self.builder, branch)
        self.llvm.EraseInstruction(branch)
        cstring = CString("bridge")
        bridge = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                            cstring.ptr)
        self.llvm.BuildCondBr(self.builder, cnd, resume, bridge)

        self.llvm.removePredecessor(self.bailout, current_block)
        block = self.llvm.splitBasicBlockAtPhi(self.bailout)
        terminator = self.llvm.getTerminator(self.bailout)
        self.llvm.EraseInstruction(terminator)
        self.llvm.DeleteBasicBlock(block)

        failargs = [arg for arg in op.getarglist() if arg is not None]
        for arg in failargs:
            index, ref_count = self.failarg_order[self.ssa_vars[arg]]
            if ref_count == 1: #no longer a failarg and doesn't need to be stackmapped
                del self.failarg_order[self.ssa_vars[arg]]
            else:
                self.failarg_order[self.ssa_vars[arg]] = (index, ref_count-1)
        llvm_failargs_no_holes = [arg for arg in llvm_failargs
                                    if arg is not None]
        for c, arg in enumerate(inputargs):
            self.ssa_vars[arg] = llvm_failargs_no_holes[c]

        self.llvm.PositionBuilderAtEnd(self.builder, bridge)

class RuntimeCallbackImpl(GuardHandlerBase):
    """
    Branch all guards to a single bailout block which passes all failargs
    to a runtime callback in order of first seen to last which the runtime
    then figures out which values are the required failargs and writes
    them into the jitframe
    """
    def __init__(self, dispatcher):
        GuardHandlerBase.__init__(self, dispatcher)
        self.failarg_index = 0
        self.failarg_order = {} #map of llvm failarg values to tuple of index and ref count
        self.llvm_failargs = {}
        self.guard_blocks = {}
        self.guard_keys = {}
        self.bailout = self.init_bailout()

    def init_bailout(self):
        cstring = CString("bailout")
        bailout = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                cstring.ptr)
        self.llvm.PositionBuilderAtEnd(self.builder, bailout)

        cstring = CString("descr_phi")
        self.descr_phi = self.llvm.BuildPhi(self.builder,
                                            self.cpu.llvm_int_type,
                                            cstring.ptr)

        self.llvm.PositionBuilderAtEnd(self.builder, self.dispatcher.entry)
        return bailout

    def setup_guard(self, op):
        current_block = self.llvm.GetInsertBlock(self.builder)
        descr = op.getdescr()
        self.guard_blocks[descr] = current_block

        cstring = CString("resume")
        resume = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                            cstring.ptr)

        return (resume, self.bailout)

    def finalise_guard(self, op, resume, cnd, branch):
        descr = op.getdescr()
        current_block = self.guard_blocks[descr]

        for arg in op.getfailargs():
            if arg is not None:
                llvm_arg = self.ssa_vars[arg]
                if llvm_arg._cast_to_adr() not in self.failarg_order:
                    self.failarg_order[llvm_arg] = (self.failarg_index, 0)
                    self.failarg_index += 1
                else:
                    index, ref_count = self.failarg_order[llvm_arg]
                    self.failarg_order[llvm_arg] = (index, ref_count+1)
                    self.llvm_failargs[descr].append(llvm_arg)
            else:
                self.llvm_failargs[descr].append(None)

        llvm_descr = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                        compute_unique_id(descr), 0)
        self.llvm.AddIncoming(self.descr_phi, llvm_descr, current_block)

        self.guard_keys[descr] = (op, resume, cnd, branch)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def runtime_callback(self, descr_int_ptr, jitframe_ptr, *failargs):
        descr = ctypes.cast(descr_int_ptr, ctypes.py_object).value
        jitframe = lltype.cast_opaque_ptr(JITFRAMEPTR, jitframe_ptr)

        llvm_failargs = self.llvm_failargs[descr]
        indices = [self.failarg_order[arg][0] for arg in llvm_failargs]

        for c, index in enumerate(indices): #TODO: not sure if rpython jitframe preserves indx 0
            failarg = failargs[index]
            jitframe.jf_frame[c] = rffi.cast(lltype.Signed, failarg)

        jitframe.jf_descr = cast_instance_to_gcref(descr)

    def finalise_bailout(self):
        self.llvm.PositionBuilderAtEnd(self.bailout)

        arg_types = []
        ret_type = lltype.Void
        callback_int_ptr = self.dispatcher.get_func_ptr(self.runtime_callback,
                                                        arg_types, ret_type)
        callback_int_ptr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                   callback_int_ptr, 0)
        llvm_failargs = list(self.failarg_order.keys())
        arg_types_llvm = [self.cpu.llvm_int_type, self.cpu.llvm_void_ptr]
        arg_types_llvm += [self.llvm.TypeOf(arg) for arg in llvm_failargs]
        args_llvm = [self.descr_phi, self.jitframe.struct] + llvm_failargs
        ret_type_llvm = self.cpu.llvm_void_type
        self.dispatcher.call_function(callback_int_ptr_llvm, ret_type_llvm,
                                      arg_types_llvm, args_llvm, "")

        self.llvm.BuildRet(self.builder, self.jitframe.struct)

    def patch_guard(self, faildescr, inputargs):
        op, resume, cnd, branch = self.guard_keys[faildescr]
        current_block = self.guard_blocks[faildescr]
        llvm_failargs = self.llvm_failargs[faildescr]

        self.llvm.PosoitionBuilderBefore(self.builder, branch)
        self.llvm.EraseInstruction(branch)
        cstring = CString("bridge")
        bridge = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                            cstring.ptr)
        self.llvm.BuildCondBr(self.builder, cnd, resume, bridge)

        self.llvm.removePredecessor(self.bailout, current_block)
        block = self.llvm.splitBasicBlockAtPhi(self.bailout)
        terminator = self.llvm.getTerminator(self.bailout)
        self.llvm.EraseInstruction(terminator)
        self.llvm.DeleteBasicBlock(block)

        failargs = [arg for arg in op.getarglist() if arg is not None]
        for arg in failargs:
            index, ref_count = self.failarg_order[self.ssa_vars[arg]]
            if ref_count == 1: #no longer a failarg and doesn't need to be stackmapped
                del self.failarg_order[self.ssa_vars[arg]]
            else:
                self.failarg_order[self.ssa_vars[arg]] = (index, ref_count-1)
        llvm_failargs_no_holes = [arg for arg in llvm_failargs
                                    if arg is not None]
        for c, arg in enumerate(inputargs):
            self.ssa_vars[arg] = llvm_failargs_no_holes[c]

        self.llvm.PositionBuilderAtEnd(self.builder, bridge)
