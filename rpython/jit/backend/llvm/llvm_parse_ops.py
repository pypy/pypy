from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str

class LLVMOpDispatcher:
    #FIXME: opnames, enums, desc counts, parse args
    def __init__(self, cpu):
        self.cpu = cpu
        self.llvm = self.cpu.llvm
        self.ssa_vars = {} #map ssa names to LLVM objects
        self.const_cnt = 0 #counter to help keep llvm's ssa names unique
        self.descrs = [] #save descr objects from branches in order they're seen #TODO: this may not make sense in a trace tree
        self.desc_cnt = 0
        self.descr_phis = {} #map label descrs to phi values
        self.descr_blocks = {} #map label descrs to their blocks
        self.bailout_blocks = {} #map guard descrs to their bailout blocks

    def parse_args(self, args): #convert opcode args into LLVM objects and types
        llvm_args = []
        #for arg in args:
        #    if arg.is_constant():
        #        if arg.datatype == 'i':
        #            if arg.
        #            self.llvm.ConstInt(LLVMIntType(arg.bytesize), arg.getvalue(), )
        return llvm_args

    def dispatch_ops(self, func, inputargs, ops, is_bridge=False):
        if not is_bridge: #input args for a bridge can only be args parsed in a previous trace
            for c, arg in enumerate(inputargs):
                name = repr(arg)
                self.ssa_vars[name] = self.llvm.GetParam(func, c)

        for op in ops: #hoping if we use the opcode numbers and elif's this'll optimise to a jump table
            if op.opnum == 1:
                self.parse_jump(op)

            elif op.opnum == 2:
                self.parse_finish(op)

            elif op.opnum == 4:
                self.parse_label(op, func)

            elif op.opnum == 7:
                self.parse_guard_true(op, func)

            elif op.opnum == 31:
                self.parse_int_add(op)

            elif op.opnum == 99:
                self.parse_int_le(op)

    def parse_jump(self, op):
        current_block = self.llvm.GetInsertBlock(self.cpu.Builder)
        descr = op.getdescr()
        target_block = self.descr_blocks[descr]
        phis = self.descr_phis[descr]

        c = 0
        for arg, _, _, in self.parse_args(op.getargslist()):
            phi = phis[c]
            self.llvm.AddIncoming(phi, arg, current_block)
            c += 1

        self.llvm.BuildBr(self.cpu.Builder, target_block)

    def parse_finish(self, op):
        self.descrs.append(op.getdescr())
        self.descr_cnt += 1
        self.llvm.BuildRet(self.cpu.Builder, self.ssa_vars[op._args[0]]) #TODO: return both arg as well as desc count

    def parse_label(self, op, func):
        descr = op.getdescr()
        self.descrs[descr]
        self.descr_cnt += 1
        last_block = self.llvm.GetInsertBlock(self.cpu.Builder)
        loop_header = self.llvm.LLVMAppendBasicBlock(func,
                                                     str2constcharp("loop_header_"
                                                                    +str(self.descr_cnt)))
        self.llvm.BuildBr(self.cpu.Builder, loop_header) #llvm requires explicit branching even for fall through
        self.llvm.PositionBuilderAtEnd(self.cpu.Builder, loop_header)

        phis = []

        for arg, typ, name in self.parse_args(op.getargslist()):
            phi = self.llvm.BuildPhi(self.cpu.Builder, typ,
                                     str2constcharp(name+"_phi"))
            self.llvm.AddIncoming(phi, arg, last_block)
            self.ssa_vars[name] = phi #this introduces divergence between our ssa values and llvm's, hope that's not too hacky
            phis.append(phi)

        self.descr_phis[descr] = phis
        self.descr_blocks[descr] = loop_header

    def parse_guard_true(self, op, func):
        descr = op.getdescr()
        self.descrs.append(descr)
        self.descr_cnt += 1

        resume = self.llvm.AppendBasicblock(func, str2constcharp("resume_"
                                                                 +str(self.descr_cnt)))
        bailout = self.llvm.AppendBasicblock(func,
                                             str2constcharp("bailout_"
                                                            +str(self.descr_cnt)))

        cnd = self.ssa_vars[op.getargslist()[0]]
        self.llvm.BuildCondBr(self.cpu.Builder, cnd, resume, bailout)

        self.llvm.PositionBuilderAtEnd(self.cpu.Builder, bailout)
        self.llvm.BuildRet(self.cpu.Builder, self.descr_cnt) #FIXME: convert to LLVM const

        self.llvm.PositionBuilderAtEnd(self.cpu.Builder, resume)

        self.bailout_blocks[descr] = bailout

    def parse_int_add(self, op):
        args = []
        for arg, typ, name in self.parse_args(op.getargslist()):
            args.append(arg)
        lhs = args[0]
        rhs = args[1]
        self.ssa_vars[op.name] = self.llvm.BuildAdd(self.cpu.Builder, lhs, rhs,
                                                    str2constcharp(op.name))

    def parse_int_le(self, op):
        args = []
        for arg, typ, name in self.parse_args(args):
            args.append(arg)
        lhs = args[0]
        rhs = args[1]
        self.ssa_vars[op.name] = self.llvm.BuildICmp(self.cpu.Builder, enumop,
                                                lhs, rhs, str2constcharp(op.name))
