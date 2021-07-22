import ctypes
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.support import ptr2int
from rpython.rlib.objectmodel import compute_unique_id
from rpython.rlib.jit_libffi import types
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.backend.llsupport import gc
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
        self.llvm.PositionBuilderAtEnd(builder, self.entry)
        self.jitframe = self.llvm.GetParam(self.func, 0)
        cstring = CString("bailout")
        self.bailout = self.llvm.AppendBasicBlock(self.cpu.context,
                                                  self.func, cstring.ptr)
        self.define_constants()

    def define_constants(self):
        self.zero = self.llvm.ConstInt(self.cpu.llvm_int_type, 0, 1)
        self.true = self.llvm.ConstInt(self.cpu.llvm_bool_type, 1, 0)
        self.false = self.llvm.ConstInt(self.cpu.llvm_bool_type, 0, 0)
        self.max_int = self.llvm.ConstInt(self.cpu.llvm_wide_int,
                                          2**(self.cpu.WORD*8-1)-1, 1)
        self.min_int = self.llvm.ConstInt(self.cpu.llvm_wide_int,
                                          -2**(self.cpu.WORD*8-1), 1)
        self.fabs_intrinsic = self.define_function([self.cpu.llvm_float_type],
                                                   self.cpu.llvm_float_type,
                                                   "llvm.fabs.f64")
        self.stackmap_intrinsic = self.define_function(
            [self.cpu.llvm_int_type, self.cpu.llvm_indx_type],
            self.cpu.llvm_void_type, "llvm.experimental.stackmap", variadic=True
            )
        self.set_pred_enums()

    def set_pred_enums(self):
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

    def get_func_ptr(self, func, arg_types, ret_type):
        #takes rpython types
        FPTR = lltype.Ptr(lltype.FuncType(arg_types, ret_type))
        func_ptr = llhelper(FPTR, func)
        return ptr2int(func_ptr)

    def func_ptr_to_int(self, func, FPTR):
        func_ptr = llhelper(FPTR, func)
        return ConstInt(ptr2int(func_ptr))

    def define_function(self, param_types, ret_type, name, variadic=False):
        #takes llvm types
        parameters = self.rpython_array(param_types, self.llvm.TypeRef)
        signature = self.llvm.FunctionType(ret_type, parameters,
                                           len(param_types),
                                           1 if variadic else 0)
        lltype.free(parameters, flavor='raw')
        cstring = CString(name)
        return self.llvm.AddFunction(self.module, cstring.ptr, signature)

    def call_function(self, func_int_ptr, ret_type, arg_types, args, res_name):
        # takes llvm types
        # pass res_name = "" when returning void
        arg_num = len(args)
        arg_types = self.rpython_array(arg_types, self.llvm.TypeRef)
        func_type = self.llvm.FunctionType(ret_type, arg_types,
                                           arg_num, 0)

        func_ptr_type = self.llvm.PointerType(func_type, 0)
        cstring = CString("func_ptr")
        func = self.llvm.BuildIntToPtr(self.builder, func_int_ptr,
                                       func_ptr_type, cstring.ptr)
        arg_array = self.rpython_array(args, self.llvm.ValueRef)

        cstring = CString(res_name)
        res =  self.llvm.BuildCall(self.builder, func, arg_array, arg_num,
                                   cstring.ptr)

        lltype.free(arg_array, flavor='raw')
        lltype.free(arg_types, flavor='raw')
        return res


    def create_metadata(self, string):
        cstring = CString(string)
        mdstr = self.llvm.MDString(self.cpu.context, cstring.ptr, len(string))
        return self.llvm.MetadataAsValue(self.cpu.context, mdstr)

    def rpython_array(self, args, elem_type):
        arg_array_type = rffi.CArray(elem_type)
        arg_array = lltype.malloc(arg_array_type, n=len(args), flavor='raw')
        for c, arg in enumerate(args):
            arg_array.__setitem__(c, arg)
        return arg_array

    def parse_args(self, args):
        llvm_args = []
        for arg in args:
            if arg.is_constant():
                if arg.type == 'i':
                    typ = self.cpu.llvm_int_type
                    val = self.llvm.ConstInt(typ, arg.getvalue(), 1)
                    llvm_args.append([val, typ])
                elif arg.type == 'f':
                    typ = self.cpu.llvm_float_type
                    val = self.llvm.ConstFloat(typ, float(arg.getvalue()))
                    llvm_args.append([val, typ])
                elif arg.type == 'r':
                    int_typ = self.cpu.llvm_int_type
                    int_val = self.llvm.ConstInt(int_typ, arg.getvalue(), 1)
                    typ = self.cpu.llvm_void_ptr
                    cstring = CString("ptr_arg")
                    val = self.llvm.BuildIntToPtr(self.builder, int_val,
                                                  typ, cstring.ptr)
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
        if arg.type == 'r':
            cstring = CString("arg")
            return self.llvm.BuildIntToPtr(self.builder, llvm_val,
                                           self.cpu.llvm_void_ptr, cstring.ptr)

    def uncast(self, arg, llvm_val):
    #need to put signed ints back in the jitframe
        if arg.type == 'i':
            cstring = CString("uncast_res")
            return self.llvm.BuildSExt(self.builder, llvm_val, #TODO: look into what happens when val is i1
                                       self.cpu.llvm_int_type, cstring.ptr)
        elif arg.type == 'f':
            cstring = CString("uncast_res")
            return self.llvm.BuildBitCast(self.builder, llvm_val,
                                          self.cpu.llvm_int_type, cstring.ptr)
        else: #arg.type == 'r'
            cstring = CString("uncast_res")
            return self.llvm.BuildPtrToInt(self.builder, llvm_val,
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
                                                 0, 0)
                self.llvm.AddIncoming(self.bailout_phis[indx], dummy_value, block)
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
        cstring = CString("overflow_flag")
        self.overflow = self.llvm.BuildAlloca(self.builder,
                                              self.cpu.llvm_bool_type,
                                              cstring.ptr)
        self.local_vars_size += 1
        self.llvm.BuildStore(self.builder, self.false, self.overflow)
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

            elif op.opnum == 11: #9 and 10 are vect ops
                resume_block = self.setup_guard(op)
                self.parse_guard_value(op, resume_block)

            elif op.opnum == 13:
                resume_block = self.setup_guard(op)
                self.parse_guard_nonnull(op, resume_block)

            elif op.opnum == 14:
                resume_block = self.setup_guard(op)
                self.parse_guard_isnull(op, resume_block)

            elif op.opnum == 22:
                resume_block = self.setup_guard(op)
                self.parse_guard_no_overflow(op, resume_block)

            elif op.opnum == 23:
                resume_block = self.setup_guard(op)
                self.parse_guard_overflow(op, resume_block)

            elif op.opnum == 31:
                self.parse_int_add(op)

            elif op.opnum == 32:
                self.parse_int_sub(op)

            elif op.opnum == 33:
                self.parse_int_mul(op)

            elif op.opnum == 34:
                self.parse_uint_mul_high(op)

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

            elif op.opnum == 46:
                self.parse_float_neg(op)

            elif op.opnum == 47:
                self.parse_float_abs(op)

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

            elif op.opnum == 109:
                self.parse_int_neg(op)

            elif op.opnum == 110:
                self.parse_int_invert(op)

            elif op.opnum == 111:
                self.parse_int_force_ge_zero(op)

            elif op.opnum == 113:
                self.parse_ptr_to_int(op)

            elif op.opnum == 114:
                self.parse_int_to_ptr(op)

            elif op.opnum == 117:
                self.parse_ptr_eq(op)

            elif op.opnum == 116:
                self.parse_ptr_ne(op)

            elif op.opnum == 160:
                self.parse_new(op)

            elif op.opnum == 161:
                self.parse_new_with_vtable(op)

            elif op.opnum == 162:
                self.parse_new_array(op)

            elif op.opnum == 163:
                self.parse_new_array(op) #TODO: boehm zero inits by default, other gc might not

            elif op.opnum == 164:
                self.parse_newstr(op)

            elif op.opnum == 165:
                self.parse_newunicode(op)

            elif op.opnum == 166:
                self.parse_force_token(op)

            elif op.opnum == 168: #167 doesn't reach backend
                self.parse_strhash(op)

            elif op.opnum == 169:
                self.parse_unicodehash(op)

            elif op.opnum == 213:
                self.parse_call(op, 'r')

            elif op.opnum == 214:
                self.parse_call(op, 'f')

            elif op.opnum == 215:
                self.parse_call(op, 'i')

            elif op.opnum == 216:
                self.parse_call(op, 'n')

            elif op.opnum == 217:
                self.parse_cond_call(op)

            elif op.opnum == 218:
                self.parse_cond_call_value(op, "r")

            elif op.opnum == 219:
                self.parse_cond_call_value(op, "i")

            elif op.opnum == 246:
                self.parse_int_ovf(op, '+')

            elif op.opnum == 247:
                self.parse_int_ovf(op, '-')

            elif op.opnum == 248:
                self.parse_int_ovf(op, '*')


            else: #TODO: take out as this may prevent jump table optimisation
                raise Exception("Unimplemented opcode: "+str(op)+"\n Opnum: "+str(op.opnum))

        self.populate_bailout()
        if self.cpu.debug:
            self.llvm.DumpModule(self.module)

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
        descr = self.llvm.ConstInt(self.cpu.llvm_int_type, descr, 0)
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
                                             descr_addr, 1)
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
        cstring = CString("cnd_flipped")
        cnd_flipped = self.llvm.BuildXor(self.builder, cnd, self.true,
                                         cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd_flipped, resume, self.bailout)
        self.descr_guards[op.getdescr()] = (branch, op, cnd_flipped, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_guard_value(self, op, resume):
        args = op.getarglist()
        val = self.ssa_vars[args[0]]
        typ = args[1].type
        const_val = args[1].getvalue()
        cstring = CString("guard_value_cmp")
        if typ == 'i':
            const = self.llvm.ConstInt(self.cpu.llvm_int_type, const_val, 1)
            cnd = self.llvm.BuildICmp(self.builder, self.inteq, val, const,
                                      cstring.ptr)
        elif typ == 'f':
            const = self.llvm.ConstFloat(self.cpu.llvm_float_type,
                                         float(const_val))
            cnd = self.llvm.BuildFCmp(self.builder, self.realeq, val, const,
                                      cstring.ptr)
        elif typ == 'r':
            const = self.llvm.ConstInt(self.cpu.llvm_int_type, const_val, 0)
            int_ptr = self.llvm.BuildPtrToInt(self.builder, val,
                                              self.cpu.llvm_int_type,
                                              cstring.ptr)
            cnd = self.llvm.BuildICmp(self.builder, self.inteq, int_ptr, const,
                                      cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, self.bailout)
        self.descr_guards[op.getdescr()] = (branch, op, cnd, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_guard_nonnull(self, op, resume):
        arg, typ = self.parse_args(op.getarglist())[0]
        cstring = CString("guard_nonnull_res")
        if typ != 'f': #IsNotNull is generic on int and ptr but not float
            cnd = self.llvm.BuildIsNotNull(self.builder, arg, cstring.ptr)
        else:
            zero = self.llvm.ConstFloat(self.cpu.llvm_float_type, float(0))
            cnd = self.llvm.BuildFCmp(self.builder, self.realne, arg, zero,
                                      cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, self.bailout)
        self.descr_guards[op.getdescr()] = (branch, op, cnd, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_guard_isnull(self, op, resume):
        arg, typ = self.parse_args(op.getarglist())[0]
        cstring = CString("guard_isnull_res")
        if typ != 'f':
            cnd = self.llvm.BuildIsNull(self.builder, arg, cstring.ptr)
        else:
            zero = self.llvm.ConstFloat(self.cpu.llvm_float_type, float(0))
            cnd = self.llvm.BuildFCmp(self.builder, self.realeq, arg, zero,
                                      cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd, resume, self.bailout)
        self.descr_guards[op.getdescr()] = (branch, op, cnd, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_guard_no_overflow(self, op, resume):
        cstring = CString("overflow_flag")
        cnd = self.llvm.BuildLoad(self.builder, self.cpu.llvm_bool_type,
                                  self.overflow, cstring.ptr)
        cstring = CString("overflow_flag_flipped")
        cnd_flipped = self.llvm.BuildXor(self.builder, cnd, self.true,
                                         cstring.ptr)
        branch = self.llvm.BuildCondBr(self.builder, cnd_flipped, resume,
                                       self.bailout)
        self.descr_guards[op.getdescr()] = (branch, op, cnd_flipped, resume)
        self.llvm.PositionBuilderAtEnd(self.builder, resume)

    def parse_guard_overflow(self, op, resume):
        cstring = CString("overflow_flag")
        cnd = self.llvm.BuildLoad(self.builder, self.cpu.llvm_bool_type,
                                  self.overflow, cstring.ptr)
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

    def parse_uint_mul_high(self, op):
        """
        see jit/metainterp/optimizeopt/intdiv.py for a more readable version
        of this, but note that it differs slightly as this version was changed
        to match the output of clang at O3
        """
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        shift = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                   self.cpu.WORD/2, 0)
        mask_tmp = (1 << self.cpu.WORD/2) - 1
        mask = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                  mask_tmp, 0)

        cstring = CString("a_high")
        a_high = self.llvm.BuildURShl(self.builder, lhs, shift, cstring.ptr)
        cstring = CString("a_low")
        a_low = self.llvm.BuildAnd(self.builder, lhs, mask, cstring.ptr)
        cstring = CString("b_high")
        b_high = self.llvm.BuildURShl(self.builder, rhs, shift, cstring.ptr)
        cstring = CString("b_low")
        b_low = self.llvm.BuildAnd(self.builder, rhs, mask, cstring.ptr)

        cstring = CString("res_low_low")
        res_low_low = self.llvm.BuildNUWMul(self.builder, a_low, b_low,
                                            cstring.ptr)
        cstring = CString("res_low_high")
        res_low_high = self.llvm.BuildNUWMul(self.builder, a_low, b_high,
                                             cstring.ptr)
        cstring = CString("res_high_low")
        res_high_low = self.llvm.BuildNUWMul(self.builder, a_high, b_low,
                                          cstring.ptr)
        cstring = CString("res_high_high")
        res_high_high = self.llvm.BuildMul(self.builder, a_high, b_high,
                                           cstring.ptr)

        cstring = CString("res")
        res_1 = self.llvm.BuildURShl(self.builder, res_low_low, shift,
                                     cstring.ptr)
        res_2 = self.llvm.BuildAdd(self.builder, res_low_high, res_high_low,
                                   cstring.ptr)
        res_3 = self.llvm.BuildAdd(self.builder, res_2, res_1, cstring.ptr)

        cstring = CString("cmp")
        cnd = self.llvm.BuildICmp(self.builder, self.intugt, res_3, res_1,
                                  cstring.ptr)
        sixteen = self.llvm.ConstInt(self.cpu.llvm_int_type, 16, 0)
        cstring = CString("borrow")
        borrow = self.llvm.BuildSelect(self.builder, cnd, self.zero, sixteen,
                                         cstring.ptr)
        cstring = CString("res")
        res_4 = self.llvm.BuildURShl(self.builder, res_3, shift, cstring.ptr)
        res_5 = self.llvm.BuildAdd(self.builder, res_4, res_high_high, cstring.ptr)
        cstring = CString("uint_mul_high_res")
        self.ssa_vars[op] = self.llvm.BuildAdd(self.builder, res_5,
                                                borrow, cstring.ptr)

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

    def parse_float_neg(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("float_neg_res")
        self.ssa_vars[op] = self.llvm.BuildFNeg(self.builder, arg, cstring.ptr)

    def parse_float_abs(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        arg_array_type = rffi.CArray(self.llvm.ValueRef)
        arg_array = lltype.malloc(arg_array_type, n=1, flavor='raw')
        arg_array.__setitem__(0, arg)
        cstring = CString("float_abs_res")
        self.ssa_vars[op] = self.llvm.BuildCall(self.builder,
                                                self.fabs_intrinsic,
                                                arg_array, 1, cstring.ptr)
        lltype.free(arg_array, flavor='raw')

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
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_is_zero_res")
        pred = self.inteq
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, pred, arg,
                                                self.zero, cstring.ptr)

    def parse_int_is_true(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_is_true_res")
        pred = self.intne
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, pred, arg,
                                                self.zero, cstring.ptr)

    def parse_int_neg(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_neg_res")
        self.ssa_vars[op] = self.llvm.BuildNeg(self.builder, arg, cstring.ptr)

    def parse_int_invert(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        negative_one = self.llvm.ConstInt(self.cpu.llvm_int_type, -1, 1)
        cstring = CString("int_invert_res")
        self.ssa_vars[op] = self.llvm.BuildXor(self.builder, arg, negative_one,
                                               cstring.ptr)

    def parse_int_force_ge_zero(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_force_ge_zero_cmp")
        cmp = self.llvm.BuildICmp(self.builder, self.intsle, arg, self.zero,
                                  cstring.ptr)
        cstring = CString("int_force_ge_zero_res")
        self.ssa_vars[op] = self.llvm.BuildSelect(self.builder, cmp,
                                                  self.zero, arg, cstring.ptr)

    def parse_ptr_to_int(self, op):
        arg = op.getarglist()[0]
        if arg.is_constant():
            self.ssa_vars[op] = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                                   arg.getvalue(), 0)
        else:
            cstring = CString("pre_to_int_res")
            self.ssa_vars[op] = self.llvm.BuildPtrToInt(self.builder,
                                                        self.ssa_vars[arg],
                                                        self.cpu.llvm_int_type,
                                                        cstring.ptr)

    def parse_int_to_ptr(self, op):
        arg = self.parse_args(op.getarglist())[0][0]
        cstring = CString("int_to_ptr_res")
        self.ssa_vars[op] = self.llvm.BuildIntToPtr(self.builder, arg,
                                                    self.cpu.llvm_void_ptr,
                                                    cstring.ptr)

    def parse_ptr_eq(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("ptr_eq_res_diff")
        res = self.llvm.BuildPtrDiff(self.builder, lhs, rhs, cstring.ptr)
        cstring = CString("ptr_eq_res")
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, self.inteq,
                                                res, self.zero, cstring.ptr)

    def parse_ptr_ne(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        cstring = CString("ptr_ne_res_diff")
        res = self.llvm.BuildPtrDiff(self.builder, lhs, rhs, cstring.ptr)
        cstring = CString("ptr_ne_res")
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, self.intne,
                                                res, self.zero, cstring.ptr)

    def parse_new(self, op):
        descr = op.getdescr()
        ptr = self.cpu.bh_new(descr)._cast_to_int()
        llvm_ptr = self.llvm.ConstInt(self.cpu.llvm_int_type, ptr, 0)
        cstring = CString("new_res")
        self.ssa_vars[op] = self.llvm.BuildIntToPtr(self.builder, llvm_ptr,
                                                    self.cpu.llvm_void_ptr,
                                                    cstring.ptr)

    def parse_new_with_vtable(self, op):
        descr = op.getdescr()
        ptr = self.cpu.bh_new_with_vtable(descr)._cast_to_int()
        llvm_ptr = self.llvm.ConstInt(self.cpu.llvm_int_type, ptr, 0)
        cstring = CString("new_res")
        self.ssa_vars[op] = self.llvm.BuildIntToPtr(self.builder, llvm_ptr,
                                                    self.cpu.llvm_void_ptr,
                                                    cstring.ptr)

    def parse_new_array(self, op): #FIXME
        num_elem = self.parse_args(op.getarglist())[0][0]
        func = self.cpu.gc_ll_descr.malloc_array
        FPTR = self.cpu.gc_ll_descr.malloc_array_FUNCPTR
        func_int = self.func_ptr_to_int(func, FPTR)
        func_int_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, func_int, 0)
        array_descr = op.getdescr()

        basesize = array_descr.basesize
        itemsize = array_descr.itemsize
        ofs_length = 0 # assuming this is fine
        basesize_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, basesize, 0)
        itemsize_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, itemsize, 0)
        ofs_length_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type, ofs_length, 0)

        # presumberly if we give more type information to llvm the optimiser
        # works better
        if array_descr.is_array_of_structs():
            # can't represent structs specifically
            ret_type = self.cpu.llvm_void_ptr
        else:
            if array_descr.is_array_of_primitives():
                if array_descr.is_array_of_floats():
                    if itemsize == 8: elem_type = self.cpu.llvm_float_type
                    elif itemsize == 4: elem_type = self.cpu.llvm_single_float_type
                else:
                    elem_type = self.llvm.IntType(self.cpu.context, itemsize*8)
            else:
                elem_type = self.cpu.llvm_void_ptr
            ret_type = self.llvm.ArrayType(elem_type, num_elem)
        arg_types = [self.cpu.llvm_int_type] * 4
        args = [basesize_llvm, itemsize_llvm, num_elem, ofs_length_llvm]

        self.ssa_vars[op] = self.call_function(func_int_llvm, ret_type,
                                               arg_types, args, "new_array_res")


    def parse_newstr(self, op):
        length = self.parse_args(op.getarglist())[0][0]
        arg_types = [lltype.Signed]
        ret_type = llmemory.GCREF

        func_int_ptr = self.get_func_ptr(self.cpu.bh_newstr, arg_types,
                                         ret_type)
        func_int_ptr_llvm = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                               func_int_ptr, 0)

        str_type = self.llvm.ArrayType(self.cpu.llvm_char_type, length)
        arg_types_llvm = [str_type]
        ret_type_llvm = self.cpu.llvm_void_ptr
        args = [length]
        self.ssa_vars[op] = self.call_function(func_int_ptr_llvm, ret_type_llvm,
                                               arg_types_llvm, args,
                                               "newstr_res")

    def parse_newunicode(self, op):
        pass

    def parse_force_token(self, op):
        self.ssa_vars[op] = self.jitframe.struct

    def parse_strhash(self, op):
        func_ptr = compute_unique_id(self.cpu.bh_strhash)

    def parse_unicodehash(self, op):
        pass


    # Won't work when call descr is dynamic and args are any int type
    def get_arg_types(self, call_descr, params):
        arg_types = []
        for c, typ in enumerate(call_descr.arg_classes):
            if typ == 'i':
                arg_type = call_descr.arg_types[c]
                if arg_type is lltype.Signed:
                    arg_types.append(self.cpu.llvm_int_type)
                elif arg_type is rffi.INT:
                    llvm_type = self.cpu.llvm_indx_type #indx_type = 32bits
                    arg_types.append(llvm_type)
                    cstring = CString("trunced_arg")
                    params[c] = self.llvm.BuildTrunc(self.builder, params[c],
                                                     llvm_type, cstring.ptr)
                elif arg_type is rffi.SHORT:
                    llvm_type = self.cpu.llvm_short_type
                    arg_types.append(llvm_type)
                    cstring = CString("trunced_arg")
                    params[c] = self.llvm.BuildTrunc(self.builder, params[c],
                                                     llvm_type, cstring.ptr)
                elif arg_type is rffi.CHAR:
                    llvm_type = self.cpu.llvm_char_type
                    arg_types.append(llvm_type)
                    cstring = CString("trunced_arg")
                    params[c] = self.llvm.BuildTrunc(self.builder, params[c],
                                                     llvm_type, cstring.ptr)
            elif typ == 'f': arg_types.append(self.cpu.llvm_float_type)
            elif typ == 'r': arg_types.append(self.cpu.llvm_void_ptr)
            elif typ == 'L': arg_types.append(self.cpu.llvm_float_type)
            elif typ == 'S': arg_types.append(self.cpu.llvm_single_float_type)
        return arg_types


    def parse_call(self, op, ret):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        func_int_ptr = args[0]
        params = args[1:]
        call_descr = op.getdescr()
        if ret == 'r': ret_type = self.cpu.llvm_void_ptr
        elif ret == 'f': ret_type = self.cpu.llvm_float_type
        elif ret == 'n': ret_type = self.cpu.llvm_void_type
        elif ret == 'i': ret_type = self.llvm.IntType(self.cpu.context,
                                                      self.cpu.WORD*call_descr.
                                                      result_size)
        arg_types = self.get_arg_types(call_descr, params)

        if ret != 'n':
            self.ssa_vars[op] = self.call_function(func_int_ptr, ret_type,
                                                   arg_types, params,
                                                   "call_res")
        else:
            self.call_function(func_int_ptr, ret_type,
                                arg_types, params, "")

    def parse_cond_call(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        cnd = args[0]
        func_int_ptr = args[1]
        params = args[2:]
        call_descr = op.getdescr()
        arg_types = self.get_arg_types(call_descr, params)
        ret_type = self.cpu.llvm_void_type

        cstring = CString("cond_call_cmp")
        cmp = self.llvm.BuildICmp(self.builder, self.intne, cnd, self.zero,
                                  cstring.ptr)
        cstring = CString("call_block")
        call_block = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                cstring.ptr)
        cstring = CString("resume_block")
        resume_block = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                  cstring.ptr)
        self.llvm.BuildCondBr(self.builder, cmp, call_block, resume_block)

        self.llvm.PositionBuilderAtEnd(self.builder, call_block)
        self.call_function(func_int_ptr, ret_type, arg_types, params, "")
        self.llvm.BuildBr(self.builder, resume_block)

        self.llvm.PositionBuilderAtEnd(self.builder, resume_block)

    def parse_cond_call_value(self, op, ret):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        cnd = args[0]
        func_int_ptr = args[1]
        params = args[2:]
        call_descr = op.getdescr()
        arg_types = self.get_arg_types(call_descr, params)
        if ret == 'i': ret_type = self.cpu.llvm_int_type
        if ret == 'r': ret_type = self.cpu.llvm_void_ptr

        cstring = CString("cmp")
        cmp = self.llvm.BuildIsNull(self.builder, cnd, cstring.ptr)

        cstring = CString("call_block")
        call_block = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                cstring.ptr)
        cstring = CString("resume_block")
        resume_block = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                  cstring.ptr)
        self.llvm.BuildCondBr(self.builder, cmp, call_block, resume_block)

        self.llvm.PositionBuilderAtEnd(self.builder, call_block)
        call_res = self.call_function(func_int_ptr, ret_type, arg_types, params,
                                      "call_res")
        self.llvm.BuildBr(self.builder, resume_block)

        self.llvm.PositionBuilderAtEnd(self.builder, resume_block)
        phi_type = ret_type
        cstring = CString("cond_phi")
        phi = self.llvm.BuildPhi(self.builder, phi_type, cstring.ptr)
        self.llvm.AddIncoming(phi, call_res, call_block)
        self.llvm.AddIncoming(phi, cnd, self.entry)
        self.ssa_vars[op] = phi

    def parse_int_ovf(self, op, binop):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]

        cstring = CString("lhs_wide")
        lhs_wide = self.llvm.BuildSExt(self.builder, lhs,
                                       self.cpu.llvm_wide_int, cstring.ptr)
        cstring = CString("rhs_wide")
        rhs_wide = self.llvm.BuildSExt(self.builder, rhs,
                                       self.cpu.llvm_wide_int, cstring.ptr)

        if binop == "+":
            cstring = CString("overflow_add")
            res = self.llvm.BuildAdd(self.builder, lhs_wide, rhs_wide,
                                     cstring.ptr)
        elif binop == "-":
            cstring = CString("overflow_sub")
            res = self.llvm.BuildSub(self.builder, lhs_wide, rhs_wide,
                                     cstring.ptr)
        elif binop == "*":
            cstring = CString("overflow_mul")
            res = self.llvm.BuildMul(self.builder, lhs_wide, rhs_wide,
                                     cstring.ptr)

        cstring = CString("max_flag")
        max_flag = self.llvm.BuildICmp(self.builder, self.intsgt, res,
                                       self.max_int, cstring.ptr)
        cstring = CString("min_flag")
        min_flag = self.llvm.BuildICmp(self.builder, self.intslt, res,
                                       self.min_int, cstring.ptr)

        cstring = CString("overflow_check")
        check = self.llvm.BuildOr(self.builder, max_flag, min_flag, cstring.ptr)
        self.llvm.BuildStore(self.builder, check, self.overflow)

        cstring = CString("int_add_ovf_res")
        self.ssa_vars[op] = self.llvm.BuildTrunc(self.builder, res,
                                                 self.cpu.llvm_int_type,
                                                 cstring.ptr)

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
                                         base_type_count)
        for count in self.elem_counts[:-1]:
            array_type = self.llvm.ArrayType(array_type, count)
        return array_type

    def allocate_array(self, entry, caller_block):
        """
        Allocas should be placed at the entry block of a function to aid
        LLVM's optimiser
        """
        instr = self.llvm.GetFirstInstruction(entry)
        self.llvm.PositionBuilderBefore(self.builder, instr)
        index = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                   0, 1)
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
                                       indecies[i], 1)
            self.indecies_array.__setitem__(i+1, index)
        cstring = CString("array_elem_ptr")
        ptr = self.llvm.BuildGEP(self.builder, self.array_type,
                                 self.array, self.indecies_array,
                                 len(indecies)+1, cstring.ptr)
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
        index = self.llvm.ConstInt(self.cpu.llvm_indx_type, 0, 1)
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
        packed = 0
        types_array = lltype.malloc(types_array_type,
                                    n=self.elem_count, flavor='raw')
        for c, elem in enumerate(self.subtypes):
            types_array.__setitem__(c, elem)
        struct_type = self.llvm.StructType(self.cpu.context, types_array,
                                           self.elem_count,
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
                                       indecies[i], 1)
            self.indecies_array.__setitem__(i+1, index)
        cstring = CString("struct_elem_ptr")
        ptr = self.llvm.BuildGEP(self.builder, self.struct_type,
                                 self.struct, self.indecies_array,
                                 len(indecies)+1, cstring.ptr)
        return ptr

    def __del__(self):
        lltype.free(self.indecies_array, flavor='raw')
