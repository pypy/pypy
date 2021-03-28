from rpython.rlib.objectmodel import compute_unique_id
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str
from rpython.rtyper.lltypesystem.lltype import r_uint
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory


class LLVMOpDispatcher:
    def __init__(self, cpu, builder, module, func, jitframe_type):
        self.cpu = cpu
        self.builder = builder
        self.module = module
        self.func = func
        self.llvm = self.cpu.llvm
        self.jitframe_type = jitframe_type
        self.jitframe = self.llvm.GetParam(self.func, r_uint(0))
        self.args_size = 0
        self.local_vars_size = 0
        self.ssa_vars = {} #map pypy ssa vars to llvm objects
        self.var_cnt = 0 #keep ssa names in llvm unique
        self.const_cnt = 0 #counter to help keep llvm's ssa names unique
        self.descr_phis = {} #map label descrs to phi values
        self.descr_blocks = {} #map label descrs to their blocks
        self.bailout_blocks = {} #map guard descrs to their bailout blocks

    def parse_args(self, args):
        llvm_args = []
        for arg in args:
            if arg.is_constant():
                if arg.type == 'i':
                    typ = self.cpu.llvm_int_type
                    val = self.llvm.ConstInt(typ, r_uint(arg.getvalue()), 1)
                    llvm_args.append([val, typ])
            else:
                val = self.ssa_vars[arg]
                llvm_args.append([val, self.llvm.TypeOf(val)])
        return llvm_args

    def cast_arg(self, arg, llvm_val, c):
        if arg.type == 'i':
            return llvm_val #already int

    def set_indecies(self, array, indecies):
        for i in range(len(indecies)):
            index = self.llvm.ConstInt(self.cpu.llvm_indx_type,
                                       r_uint(indecies[i]), 1)
            array.__setitem__(i, index)

    def dispatch_ops(self, inputargs, ops, is_bridge=False):
        if not is_bridge: #input args for a bridge can only be args parsed in a previous trace
            indecies_array = rffi.CArray(self.llvm.ValueRef)
            indecies = lltype.malloc(indecies_array, n=3, flavor='raw')
            for c, arg in enumerate(inputargs,1):
                self.set_indecies(indecies, [0,7,c])
                arg_ptr = self.llvm.BuildGEP(self.builder,
                                             self.jitframe_type,
                                             self.jitframe,
                                             indecies, r_uint(3),
                                             str2constcharp("arg_ptr_"+str(c)))
                arg_uncast = self.llvm.BuildLoad(self.builder,
                                                 self.cpu.llvm_int_type,
                                                 arg_ptr,
                                                 str2constcharp("arg_"+str(c)))
                self.ssa_vars[arg] = self.cast_arg(arg, arg_uncast, c)
                self.args_size += self.cpu.WORD
            lltype.free(indecies, flavor='raw')

        for op in ops: #hoping if we use the opcode numbers and elif's this'll optimise to a jump table
            if op.opnum == 1:
                self.parse_jump(op)

            elif op.opnum == 2:
                self.parse_finish(op)

            elif op.opnum == 4:
                self.parse_label(op)

            elif op.opnum == 7:
                self.parse_guard_true(op)

            elif op.opnum == 31:
                self.parse_int_add(op)

            elif op.opnum == 92:
                self.parse_int_le(op)

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
        indecies_array = rffi.CArray(self.llvm.ValueRef)
        indecies = lltype.malloc(indecies_array, n=3, flavor='raw')
        self.set_indecies(indecies, [0,1])
        final_descr = self.llvm.BuildGEP(self.builder, self.jitframe_type,
                                         self.jitframe,
                                         indecies, r_uint(2),
                                         str2constcharp("final_descr"))
        descr = compute_unique_id(op.getdescr()) #TODO: consider making this more efficient
        descr_int = self.llvm.ConstInt(self.cpu.llvm_int_type, r_uint(descr), 0)
        descr_ptr = self.llvm.BuildIntToPtr(self.builder, descr_int,
                                           self.cpu.llvm_void_ptr,
                                           str2constcharp("descr_ptr_"+
                                                          str(self.var_cnt)))
        self.var_cnt += 1
        self.llvm.BuildStore(self.builder, descr_ptr, final_descr)

        for c, arg in enumerate(op.getarglist(),1):
            cast_arg = self.llvm.BuildBitCast(self.builder, self.ssa_vars[arg],
                                         self.cpu.llvm_int_type,
                                         str2constcharp("res_"+str(c)))
            self.set_indecies(indecies, [0,7,c])
            ret_ptr = self.llvm.BuildGEP(self.builder,
                                         self.jitframe_type,
                                         self.jitframe,
                                         indecies, r_uint(3),
                                         str2constcharp("arg_"+str(c)))
            self.llvm.BuildStore(self.builder, cast_arg, ret_ptr)

        self.llvm.BuildRet(self.builder, self.jitframe)
        lltype.free(indecies, flavor='raw')

    def parse_label(self, op):
        descr = op.getdescr()
        last_block = self.llvm.GetInsertBlock(self.builder)
        loop_header = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                                 str2constcharp("loop_header_"
                                                                +str(self.var_cnt)))
        self.var_cnt += 1
        self.llvm.BuildBr(self.builder, loop_header) #llvm requires explicit branching even for fall through
        self.llvm.PositionBuilderAtEnd(self.builder, loop_header)

        phis = []

        c = 0
        arg_list = op.getarglist()
        for arg, typ in self.parse_args(arg_list):
            phi = self.llvm.BuildPhi(self.builder, typ,
                                     str2constcharp("phi_"+str(c)+"_"+str(self.var_cnt)))
            self.llvm.AddIncoming(phi, arg, last_block)
            rpy_val = arg_list[c] #want to replace referances to this value with the phi instead of whatever was there beofre
            self.ssa_vars[rpy_val] = phi
            phis.append(phi)
            self.var_cnt += 1
            c += 1

        self.descr_phis[descr] = phis
        self.descr_blocks[descr] = loop_header

    def parse_guard_true(self, op):
        descr = op.getdescr()

        resume = self.llvm.AppendBasicBlock(self.cpu.context,
                                            self.func,
                                            str2constcharp("resume_"
                                                           +str(self.var_cnt)))
        self.var_cnt += 1
        bailout = self.llvm.AppendBasicBlock(self.cpu.context, self.func,
                                             str2constcharp("bailout_"
                                                            +str(self.var_cnt)))
        self.var_cnt += 1

        cnd = self.ssa_vars[op.getarglist()[0]]
        self.llvm.BuildCondBr(self.builder, cnd, resume, bailout)

        self.llvm.PositionBuilderAtEnd(self.builder, bailout)
        llvm_descr_cnt = self.llvm.ConstInt(self.cpu.llvm_int_type,
                                            r_uint(self.var_cnt), 1)
        self.var_cnt += 1
        self.llvm.BuildRet(self.builder, llvm_descr_cnt)

        self.llvm.PositionBuilderAtEnd(self.builder, resume)

        self.bailout_blocks[descr] = bailout

    def parse_int_add(self, op): #TODO: look into signed/unsigned wrapping
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        self.ssa_vars[op] = self.llvm.BuildAdd(self.builder, lhs, rhs,
                                               str2constcharp(str(self.var_cnt)))
        self.var_cnt += 1

    def parse_int_le(self, op):
        args = [arg for arg, _ in self.parse_args(op.getarglist())]
        lhs = args[0]
        rhs = args[1]
        self.ssa_vars[op] = self.llvm.BuildICmp(self.builder, 9, lhs, rhs,
                                                str2constcharp(str(self.var_cnt)))
        self.var_cnt += 1
