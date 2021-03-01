from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str

class LLVM_Op_Dispatcher:
    #FIXME: opnames, enums, desc counts, parse args
    #TODO: guards
    def __init__(self, cpu):
        self.cpu = cpu
        self.llvm = self.cpu.llvm
        self.ssa_vars = {} #map ssa names to LLVM objects
        self.const_cnt = 0 #counter to help keep llvm's ssa names unique
        self.descrs = [] #save descr objects from branches in order as they're seen
        self.descr_phis = {} #map label descrs to phi values
        self.descr_blocks = {} #map label descrs to their blocks
        self.desc_cnt = 0

    def parse_args(self, args): #convert opcode args into LLVM objects and types
        llvm_args = []
        for arg in args:
            if arg.is_constant():
                if arg.datatype == 'i':
                    if arg.
                    self.llvm.ConstInt(LLVMIntType(arg.bitsize), arg.getvalue(), )
        return llvm_args

    def dispatch_ops(self, func, entry, inputargs, ops):
        for c, arg in enumerate(inputargs):
            name = repr(arg)
            ssa_vars[name] = self.llvm.GetParam(func, c)

        for op in ops: #hoping if we use the opcode numbers and elif's this'll optimise to a jump table
            if op.opnum == 1:
                self.parse_jump(op)

            elif op.opnum == 2:
                self.parse_finish(op)

            elif op.opnum == 4:
                self.parse_label(op, func)

            elif op.opnum == 31:
                self.parse_int_add(op)

            elif op.opnum == 99:
                self.parse_int_le(op)

    def parse_jump(self, op):
        block = self.descr_blocks[op.getdescr()]
        phis = self.descr_phis[op.getdescr()]
        c = 0

        for arg, typ, name in self.parse_args(op.getargslist()):
            phi = phis[c]
            self.llvm.AddIncoming(phi, arg, block)
            c += 1

        self.llvm.BuildBr(self.Builder, block)

    def parse_finish(self, op):
        self.descrs.append(op.getdescr())
        self.llvm.BuildRet(self.Builder, self.ssa_vars[op._args[0]]) #TODO: return both arg as well as desc count

    def parse_label(self, op, func):
        last_block = self.llvm.GetInsertBlock(self.Builder)
        loop_header = self.llvm.LLVMAppendBasicBlock(func,
                                                     str2constcharp("loop_header"))
        br = self.llvm.BuildBr(self.Builder, loop_header) #llvm requires explicit branching even for fall through
        self.llvm.PositionBuilderAtEnd(self.Builder, loop_header)

        phis = []

        for arg, typ, name in self.parse_args(op.getargslist()):
            phi = self.llvm.BuildPhi(self.Builder, typ,
                                     str2constcharp(name+"_phi"))
            self.llvm.AddIncoming(phi, arg, last_block)
            self.ssa_vars[name] = phi #this introduces divergence between our ssa values and llvm's, hope that's not too hacky
            phis.append(phi)

        descr_phis[op.getdescr()] = phis

    def parse_int_add(self, op):
        args = []
        for arg, typ, name in self.parse_args(op.getargslist()):
            args.append(arg)
        lhs = args[0]
        rhs = args[1]
        self.ssa_vars[op.name] = self.llvm.BuildAdd(self.Builder, lhs, rhs,
                                                    str2constcharp(op.name))

    def parse_int_le(self, op):
        args = []
        for arg, typ, name in self.parseargs(args):
            args.append(arg)
        lhs = args[0]
        rhs = args[1]
        ssa_vars[op.name] = self.llvm.BuildICmp(self.Builder, enumop,
                                                lhs, rhs, str2constcharp(op.name))
