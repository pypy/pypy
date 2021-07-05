from rpython.rlib.objectmodel import compute_unique_id
from rpython.rtyper.lltypesystem.lltype import r_uint
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.jit.backend.llvm.llvm_api import CString

class LLVMOpDispatcher:
    def __init__(self, cpu, builder, module, entry, func, jitframe_type, jitframe_subtypes):
        self.cpu = cpu
        self.builder = builder
        self.module = module
        self.func = func
        self.entry = entry
        self.llvm = self.cpu.llvm
        self.jitframe_type = jitframe_type
        self.jitframe_subtypes = jitframe_subtypes
        self.args_size = 0
        self.local_vars_size = 0
        self.ssa_vars = {} #map pypy ssa vars to llvm objects
        self.descr_phis = {} #map label descrs to phi values
        self.descr_blocks = {} #map label and guard descrs to their blocks
        self.descr_guards = {} #map guard descrs to llvm instructions
        self.llvm_failargs = {} #map guards to llvm values their failargs map to at point of parsing
        self.guards = set() #keep track of seen guards for later
        self.max_failargs = 0 #track max number of failargs seen
        self.setCmpEnums()
        self.llvm.PositionBuilderAtEnd(builder, self.entry)
        self.jitframe = self.llvm.GetParam(self.func, r_uint(0))
        cstring = CString("bailout")
        self.bailout = self.llvm.AppendBasicBlock(self.cpu.context,
                                                  self.func, cstring.ptr)

    def setCmpEnums(self):
        enums = lltype.malloc(self.llvm.CmpEnums, flavor='raw')
        self.llvm.SetCmpEnums(enums)
        self.inteq = enums.inteq
        self.intne = enums.intne
        self.intugt = enums.intugt
        self.intuge = enums.intuge
        self.intult = enums.intult
        self.intule = enums.intule
        self.intsgt = enums.intsgt
        self.intsge = enums.intsge
        self.intslt = enums.intslt
        self.intsle = enums.intsle
        self.realeq = enums.realeq
        self.realne = enums.realne
        self.realgt = enums.realgt
        self.realge = enums.realge
        self.reallt = enums.reallt
        self.realle = enums.realle
        self.realord = enums.realord
        lltype.free(enums, flavor='raw')

    def parse_args(self, args):
        llvm_args = []
        for arg in args:
            if arg.is_constant():
                if arg.type == 'i':
                    typ = self.cpu.llvm_int_type
                    val = self.llvm.ConstInt(typ, r_uint(arg.getvalue()), 1)
                    llvm_args.append([val, typ])
                if arg.type == 'f':
                    typ = self.cpu.llvm_float_type
                    val = self.llvm.ConstFloat(typ, float(arg.getvalue()))
                    llvm_args.append([val, typ])
            else:
                val = self.ssa_vars[arg]
                llvm_args.append([val, self.llvm.TypeOf(val)])
        return llvm_args

    def cast_arg(self, arg, llvm_val):
        if arg.type == 'i':
            return llvm_val #already int
        if arg.type == 'f':
            cstring = CString("arg")
            return self.llvm.BuildBitCast(self.builder, llvm_val,
                                          self.cpu.llvm_float_type, cstring.ptr)

    #need to put signed ints back in the jitframe
    def uncast(self, arg, llvm_val):
        if arg.type == 'i':
            return llvm_val
        else:
            cstring = CString("uncast_res")
            return self.llvm.BuildBitCast(self.builder, llvm_val,
                                          self.cpu.llvm_int_type, cstring.ptr)

    def exit_trace(self, args, descr):
        self.jitframe.set_elem(descr, 1)
        for i in range(len(args)):
            self.jitframe.set_elem(args[i], 7, i+1)
        self.llvm.BuildRet(self.builder, self.jitframe.struct)

    def init_bailout(self):
        self.llvm.PositionBuilderAtEnd(self.builder, self.bailout)
        self.bailout_phis = []
        cstring = CString("descr_phi")
        descr_phi = self.llvm.BuildPhi(self.builder, self.cpu.llvm_int_type,
                                     cstring.ptr)
        self.bailout_phis.append(descr_phi)
        self.llvm.PositionBuilderAtEnd(self.builder, self.entry)

    def populate_bailout(self):
        if len(self.guards) == 0: #is linear loop
            self.llvm.DeleteBasicBlock(self.bailout)
            return
        self.llvm.PositionBuilderAtEnd(self.builder, self.bailout)
        for guard in self.guards:
            failargs = guard.getfailargs()
            num_failargs = len(failargs)
            descr = guard.getdescr()
            block = self.descr_blocks[descr]
            for i in range(self.max_failargs-num_failargs):
                #how far we got + extra phi node we're currently at + 1 for descr phi + 1 for 0 indexing
                indx = num_failargs+i+2
                dummy_value = self.llvm.ConstInt(self.cpu.context,
                                                 r_uint(0), 0)
                self.llvm.AddIncoming(self.bailout_phis[indx], dummy_value, block)
        if self.max_failargs > 0:
            descr = self.bailout_phis[0]
            self.exit_trace(self.bailout_phis[1:], descr)
        else:
            descr = self.bailout_phis[0]
            self.jitframe.set_elem(descr, 1)
            self.llvm.BuildRet(self.builder, self.jitframe.struct)

    def patch_guard(self, faildescr, inputargs):
        branch, op, cnd, resume = self.descr_guards[faildescr]
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
        self.llvm.PositionBuilderAtEnd(self.builder, bridge)
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

    def init_inputargs(self, inputargs):
        self.jitframe = LLVMStruct(self, self.jitframe_subtypes, 2,
                                   self.entry, self.jitframe,
                                   self.jitframe_type)
        indecies_array = rffi.CArray(self.llvm.ValueRef)
        indecies = lltype.malloc(indecies_array, n=3, flavor='raw')
        for c, arg in enumerate(inputargs,1):
            arg_uncast = self.jitframe.get_elem(7,c)
            self.ssa_vars[arg] = self.cast_arg(arg, arg_uncast)
            self.args_size += self.cpu.WORD
        lltype.free(indecies, flavor='raw')

    def dispatch_ops(self, inputargs, ops, faildescr=None):
        if faildescr is None:
            self.init_inputargs(inputargs)
            self.init_bailout()
        else: #is bridge
            self.patch_guard(faildescr, inputargs)

        for op in ops:
            if op.opnum == 1:
                self.parse_jump(op)

            elif op.opnum == 2:
                self.parse_finish(op)

            elif op.opnum == 4:
                self.parse_label(op)

            elif op.opnum == 7:
                resume_block = self.setup_guard(op)
                self.parse_guard_true(op, resume_block)

            elif op.opnum == 8:
                resume_block = self.setup_guard(op)
                self.parse_guard_false(op, resume_block)

            elif op.opnum == 13:
                resume_block = self.setup_guard(op)
                self.parse_guard_nonnull(op, resume_block)

            elif op.opnum == 14:
                resume_block = self.setup_guard(op)
                self.parse_guard_isnull(op, resume_block)

            elif op.opnum == 31:
                self.parse_int_add(op)

            elif op.opnum == 32:
                self.parse_int_sub(op)

            elif op.opnum == 33:
                self.parse_int_mul(op)

            #elif op.opnum == 34:
            #    self.parse_uint_mul_high(op)

            elif op.opnum == 35:
                self.parse_int_and(op)

            elif op.opnum == 36:
                self.parse_int_or(op)

            elif op.opnum == 37:
                self.parse_int_xor(op)

            elif op.opnum == 38:
                self.parse_int_rshift(op)

            elif op.opnum == 39:
                self.parse_int_lshift(op)

            elif op.opnum == 40:
                self.parse_uint_rshift(op)

            elif op.opnum == 41:
                self.parse_int_sext(op)

            elif op.opnum == 42:
                self.parse_float_add(op)

            elif op.opnum == 43:
                self.parse_float_sub(op)

            elif op.opnum == 44:
                self.parse_float_mul(op)

            elif op.opnum == 45:
                self.parse_float_div(op)

            #elif op.opnum == 46:
            #    self.parse_float_neg(op)

            #elif op.opnum == 47:
            #    self.parse_float_abs(op)

            elif op.opnum == 48:
                self.parse_float_to_int(op)

            elif op.opnum == 49:
                self.parse_int_to_float(op)

            elif op.opnum == 50:
                self.parse_float_to_single_float(op)

            elif op.opnum == 51:
                self.parse_single_float_to_float(op)

            elif op.opnum == 52: #float_to_longlong - int is already word len
                self.parse_float_to_int(op)

            elif op.opnum == 53:
                self.parse_int_to_float(op)

            elif op.opnum == 91:
                self.parse_int_cmp(op, self.intslt)

            elif op.opnum == 92:
                self.parse_int_cmp(op, self.intsle)

            elif op.opnum == 93:
                self.parse_int_cmp(op, self.inteq)

            elif op.opnum == 94:
                self.parse_int_cmp(op, self.intne)

            elif op.opnum == 95:
                self.parse_int_cmp(op, self.intsgt)

            elif op.opnum == 96:
                self.parse_int_cmp(op, self.intsge)

            elif op.opnum == 97:
                self.parse_int_cmp(op, self.intult)

            elif op.opnum == 98:
                self.parse_int_cmp(op, self.intule)

            elif op.opnum == 99:
                self.parse_int_cmp(op, self.intugt)

            elif op.opnum == 100:
                self.parse_int_cmp(op, self.intuge)

            elif op.opnum == 101:
                self.parse_float_cmp(op, self.reallt)

            elif op.opnum == 102:
                self.parse_float_cmp(op, self.realle)

            elif op.opnum == 103:
                self.parse_float_cmp(op, self.realeq)

            elif op.opnum == 104:
                self.parse_float_cmp(op, self.realne)

            elif op.opnum == 105:
                self.parse_float_cmp(op, self.realgt)

            elif op.opnum == 106:
                self.parse_float_cmp(op, self.realge)

            elif op.opnum == 107:
                self.parse_int_is_zero(op)

            elif op.opnum == 108:
                self.parse_int_is_true(op)

            elif op.opnum == 113:
                self.parse_ptr_to_int(op)

            elif op.opnum == 114:
                self.parse_int_to_ptr(op)

            #elif op.opnum == 115:
            #    self.parse_ptr_eq(op)

            #elif op.opnum == 116:
            #    self.parse_ptr_ne(op)

            else: #TODO: take out as this may prevent jump table optimisation
                raise Exception("Unimplemented opcode: "+str(op.opnum))

        self.populate_bailout()

    def parse_jump(self, op):
        current_block = self.llvm.GetInsertBlock(self.builder)
        descr = op.getdescr()
        target_block = self.descr_blocks[descr]
        phis = self.descr_phis[descr]

        c = 0
        for arg, _, in self.parse_args(op.getarglist()):
            phi = phis[c]
            self.llvm.AddIncoming(phi, arg, current_block)
            c += 1

        self.llvm.BuildBr(self.builder, target_block)

    def parse_finish(self, op):
        uncast_args = []
        for arg in op.getarglist():
            uncast = self.uncast(arg, self.ssa_vars[arg])
            uncast_args.append(uncast)
        descr = compute_unique_id(op.getdescr())
        descr = self.llvm.ConstInt(self.cpu.llvm_int_type, r_uint(descr), 0)
        self.exit_trace(uncast_args, descr)

    def parse_label(self, op):
        descr = op.getdescr()
        current_block = self.llvm.GetInsertBlock(self.builder)
        cstring = CString("loop_header")
        loop_header = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                 cstring.ptr)
        self.llvm.BuildBr(self.builder, loop_header) #llvm requires explicit branching even for fall through
        self.llvm.PositionBuilderAtEnd(self.builder, loop_header)
        phis = []
        arg_list = op.getarglist()
        c = 0
        for arg, typ in self.parse_args(arg_list):
            cstring = CString("phi_"+str(c))
            phi = self.llvm.BuildPhi(self.builder, typ, cstring.ptr)
            self.llvm.AddIncoming(phi, arg, current_block)
            rpy_val = arg_list[c] #want to replace referances to this value with the phi instead of whatever was there beofre
            self.ssa_vars[rpy_val] = phi
            phis.append(phi)
            c += 1
        self.descr_phis[descr] = phis
        self.descr_blocks[descr] = loop_header

    def setup_guard(self, op):
        self.guards.add(op)
        current_block = self.llvm.GetInsertBlock(self.builder)
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
        descr = op.getdescr()
        descr_addr = compute_unique_id(descr) #TODO: look into making more efficient
        descr_addr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                             r_uint(descr_addr), 1)
        self.llvm.AddIncoming(self.bailout_phis[0], descr_addr_llvm, current_block)
        for i in range(1,num_failargs+1):
            arg = failargs[i-1]
            uncast_arg = self.uncast(arg, self.ssa_vars[arg])
            self.llvm.AddIncoming(self.bailout_phis[i], uncast_arg, current_block)
        self.llvm.PositionBuilderAtEnd(self.builder, current_block)
        cstring = CString("resume")
        resume = self.llvm.AppendBasicBlock(self.cpu.context,
                                            self.func, cstring.ptr)
        self.descr_blocks[descr] = current_block
        return resume

    def parse_guard_true(self, op, resume):
        cnd = self.ssa_vars[op.getarglist()[0]]
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, self.bailout)
        self.descr_guards[op.getdescr()] = (branch, op, cnd, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_guard_false(self, op, resume):
        cnd = self.ssa_vars[op.getarglist()[0]]
        branch = self.llvm.BuildCondBr(self.builder, cnd, self.bailout, resume)
        self.descr_guards[op.getdescr()] = (branch, op, cnd, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_guard_nonnull(self, op, resume):
        arg = self.parse_args(op.getarglist())[0][0]
        zero = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                  r_uint(0), 1)
        cstring = CString("guard_nonnull_res")
        cnd = self.llvm.BuildICmp(self.builder, self.intne, arg, zero,
                                  cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, self.bailout)
        self.descr_guards[op.getdescr()] = (branch, op, cnd, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_guard_isnull(self, op, resume):
        arg = self.parse_args(op.getarglist())[0][0]
        zero = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                  r_uint(0), 1)
        cstring = CString("guard_isnull_res")
        cnd = self.llvm.BuildICmp(self.builder, self.inteq, arg, zero,
                                  cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, self.bailout)
        self.descr_guards[op.getdescr()] = (branch, op, cnd, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_int_add(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_add_res")
        self.ssa_vars[op] = self.llvm.BuildAdd(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_sub(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_sub_res")
        self.ssa_vars[op] = self.llvm.BuildSub(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_mul(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_mul_res")
        self.ssa_vars[op] = self.llvm.BuildMul(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_and(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_and_res")
        self.ssa_vars[op] = self.llvm.BuildAnd(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_or(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_or_res")
        self.ssa_vars[op] = self.llvm.BuildOr(self.builder, lhs, rhs,
                                              cstring.ptr)

    def parse_int_xor(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_xor_res")
        self.ssa_vars[op] = self.llvm.BuildXor(self.builder, lhs, rhs,
                                               cstring.ptr)

    def parse_int_rshift(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_rshift_res")
        self.ssa_vars[op] = self.llvm.BuildRShl(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_int_lshift(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_lshift_res")
        self.ssa_vars[op] = self.llvm.BuildLShl(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_uint_rshift(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("uint_rshift_res")
        self.ssa_vars[op] = self.llvm.BuildURShl(self.builder, lhs, rhs,
                                                 cstring.ptr)

    def parse_int_sext(self, op): #TODO: look into what pypy is passing, likely not a type
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_sext_res")
        self.ssa_vars[op] = self.llvm.BuildSExt(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_add(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_add_res")
        self.ssa_vars[op] = self.llvm.BuildFAdd(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_sub(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_sub_res")
        self.ssa_vars[op] = self.llvm.BuildFSub(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_mul(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_mul_res")
        self.ssa_vars[op] = self.llvm.BuildFMul(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_div(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_div_res")
        self.ssa_vars[op] = self.llvm.BuildFDiv(self.builder, lhs, rhs,
                                                cstring.ptr)

    def parse_float_neg(self, op): #FIXME
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("float_neg_res")
        self.ssa_vars[op] = self.llvm.BuildFDiv(self.builder, arg, cstring.ptr)

    def parse_float_to_int(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("float_to_int_res")
        self.ssa_vars[op] = self.llvm.BuildBitCast(self.builder, arg,
                                                   self.cpu.llvm_int_type,
                                                   cstring.ptr)

    def parse_int_to_float(self, op):
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("int_to_float_res")
        self.ssa_vars[op] = self.llvm.BuildBitCast(self.builder, arg,
                                                   self.cpu.llvm_float_type,
                                                   cstring.ptr)

    def parse_float_to_single_float(self, op):
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("float_to_single_float_res")
        self.ssa_vars[op] = self.llvm.BuildBitCast(self.builder, arg,
                                                   self.cpu.llvm_single_float_type,
                                                   cstring.ptr)

    def parse_single_float_to_float(self, op):
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("single_float_to_res")
        self.ssa_vars[op] = self.llvm.BuildBitCast(self.builder, arg,
                                                   self.cpu.llvm_float_type,
                                                   cstring.ptr)

    def parse_int_cmp(self, op, pred):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("int_cmp_res")
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, pred, lhs, rhs,
                                                cstring.ptr)


    def parse_float_cmp(self, op, pred):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("float_cmp_res")
        self.ssa_vars[op] = self.llvm.BuildFCmp(self.builder, pred, lhs, rhs,
                                                cstring.ptr)

    def parse_int_is_zero(self, op):
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("int_is_zero_res")
        pred = self.inteq
        zero = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                  r_uint(0), 1)
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, pred, arg, zero,
                                                cstring.ptr)

    def parse_int_is_true(self, op):
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("int_is_true_res")
        pred = self.intne
        zero = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                  r_uint(0), 1)
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, pred, arg, zero,
                                                cstring.ptr)

    def parse_ptr_to_int(self, op): #FIXME: parse refs
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("pre_to_int_res")
        self.ssa_vars[op] = self.llvm.BuildPtrToInt(self.builder, arg,
                                                    self.cpu.llvm_int_type,
                                                    cstring.ptr)

    def parse_int_to_ptr(self, op): #TODO: check that casting this to i8* is ok
        arg = self.parse_args(op.getarglist())[0]
        cstring = CString("int_to_ptr_res")
        self.ssa_vars[op] = self.llvm.BuildIntToPtr(self.builder, arg,
                                                    self.cpu.llvm_void_ptr,
                                                    cstring.ptr)

    #def parse_ptr_eq(self, op):

class LLVMArray:
    def __init__(self, dispatcher, elem_type, elem_counts, depth, caller_block,
                 array=None, array_type=None):
        self.dispatcher = dispatcher
        self.builder = self.dispatcher.builder
        self.cpu = self.dispatcher.cpu
        self.llvm = self.dispatcher.llvm
        self.elem_type = elem_type
        self.elem_counts = elem_counts
        self.depth = depth
        indecies = rffi.CArray(self.llvm.ValueRef)
        self.indecies_array = lltype.malloc(indecies, n=self.depth+1,
                                            flavor='raw')
        if array_type is None:
            self.array_type = self.get_array_type()
        else:
            self.array_type = array_type
        if array is None:
            self.array = self.allocate_array(dispatcher.entry, caller_block)
        else:
            self.array = array

    def get_array_type(self):
        base_type_count = self.elem_counts[-1]
        array_type = self.llvm.ArrayType(self.elem_type,
                                         r_uint(base_type_count))
        for count in self.elem_counts[:-1]:
            array_type = self.llvm.ArrayType(array_type,
                                             r_uint(count))
        return array_type

    def allocate_array(self, entry, caller_block):
        """
        Allocas should be placed at the entry block of a function to aid
        LLVM's optimiser
        """
        instr = self.llvm.GetFirstInstruction(entry)
        self.llvm.PositionBuilderBefore(self.builder, instr)
        index = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                   r_uint(0), 1)
        self.indecies_array.__setitem__(0, index) #held array is actually a pointer to the array, will always needs to be deref'ed at indx 0 first
        cstring = CString("array")
        array = self.llvm.BuildAlloca(self.builder, self.array_type,
                                      cstring.ptr) #TODO: check for stack overflow
        self.llvm.PositionBuilderAtEnd(self.builder, caller_block)
        self.dispatcher.local_vars_size += self.llvm.SizeOf(self.array_type)
        return array

    def get_elem(self, *indecies):
        """
        Note that LLVM will regalloc a whole aggregate type you ask it to.
        Use get_ptr if you only want the address, and not the load.
        """
        ptr = self.get_ptr(*indecies)
        elem_type = self.llvm.getResultElementType(ptr)
        cstring = CString("array_elem")
        elem = self.llvm.BuildLoad(self.builder, elem_type,
                                   ptr, cstring.ptr)
        return elem

    def set_elem(self, elem, *indecies):
        ptr = self.get_ptr(*indecies)
        self.llvm.BuildStore(self.builder, elem, ptr)

    def get_ptr(self, *indecies):
        for i in range(len(indecies)):
            index = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                       r_uint(indecies[i]), 1)
            self.indecies_array.__setitem__(i+1, index)
        cstring = CString("array_elem_ptr")
        ptr = self.llvm.BuildGEP(self.builder, self.array_type,
                                 self.array, self.indecies_array,
                                 r_uint(len(indecies)+1), cstring.ptr)
        return ptr

    def __del__(self):
        lltype.free(self.indecies_array, flavor='raw')

class LLVMStruct:
    def __init__(self, dispatcher, subtypes, depth, caller_block,
                 struct=None, struct_type=None):
        self.dispatcher = dispatcher
        self.builder = self.dispatcher.builder
        self.cpu = self.dispatcher.cpu
        self.llvm = self.dispatcher.llvm
        self.subtypes = subtypes #only defined up to depth=1
        self.elem_count = len(subtypes)
        self.depth = depth
        indecies = rffi.CArray(self.llvm.ValueRef)
        self.indecies_array = lltype.malloc(indecies, n=self.depth+1,
                                            flavor='raw')
        index = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                   r_uint(0), 1)
        self.indecies_array.__setitem__(0, index) #held struct is actually a pointer to the array, will always needs to be deref'ed at indx 0 first
        if struct_type is None:
            self.struct_type = self.get_struct_type()
        else:
            self.struct_type = struct_type
        if struct is None:
            self.struct = self.allocate_struct(dispatcher.entry, caller_block)
        else:
            self.struct = struct

    def get_struct_type(self):
        types_array_type = rffi.CArray(self.llvm.TypeRef)
        packed = r_uint(0)
        types_array = lltype.malloc(types_array_type,
                                    n=self.elem_count, flavor='raw')
        for c, elem in enumerate(self.subtypes):
            types_array.__setitem__(c, elem)
        struct_type = self.llvm.StructType(self.cpu.context, types_array,
                                           r_uint(self.elem_count),
                                           packed)
        lltype.free(types_array, flavor='raw')
        return struct_type

    def allocate_struct(self, entry, caller_block):
        """
        Allocas should be placed at the entry block of a function to aid
        LLVM's optimiser
        """
        instr = self.llvm.GetFirstInstruction(entry)
        self.llvm.PositionBuilderBefore(self.builder, instr)
        cstring = CString("struct")
        struct = self.llvm.BuildAlloca(self.builder, self.struct_type,
                                      cstring.ptr) #TODO: check for stack overflow
        self.llvm.PositionBuilderAtEnd(self.builder, caller_block)
        self.dispatcher.local_vars_size += self.llvm.SizeOf(self.struct_type)
        return struct

    def get_elem(self, *indecies):
        """
        Note that LLVM will regalloc a whole aggregate type you ask it to.
        Use get_ptr if you only want the address, and not the load.
        """
        ptr = self.get_ptr(*indecies)
        elem_type = self.llvm.getResultElementType(ptr)
        cstring = CString("struct_elem")
        elem = self.llvm.BuildLoad(self.builder, elem_type, ptr,
                                   cstring.ptr)
        return elem

    def set_elem(self, elem, *indecies):
        ptr = self.get_ptr(*indecies)
        self.llvm.BuildStore(self.builder, elem, ptr)

    def get_ptr(self, *indecies):
        for i in range(len(indecies)):
            index = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                       r_uint(indecies[i]), 1)
            self.indecies_array.__setitem__(i+1, index)
        cstring = CString("struct_elem_ptr")
        ptr = self.llvm.BuildGEP(self.builder, self.struct_type,
                                 self.struct, self.indecies_array,
                                 r_uint(len(indecies)+1), cstring.ptr)
        return ptr

    def __del__(self):
        lltype.free(self.indecies_array, flavor='raw')
