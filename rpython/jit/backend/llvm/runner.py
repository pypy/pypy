from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.backend.model import CompiledLoopToken, CPUTotalTracker
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str
from rpython.rtyper.tool.rffi_platform import DefinedConstantInteger
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.jit.backend.llvm.llvm_api import LLVM_API
from rpython.jit.backend.llvm.assembler import LLVM_Assembler

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None,
                 translate_support_code=False, gcdescr=None, debug=False):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        self.tracker = CPUTotalTracker()
        self.debug = debug
        self.llvm = LLVM_API()
        self.ThreadSafeContext = self.llvm.CreateThreadSafeContext(None)
        self.Context = self.llvm.GetContext(self.ThreadSafeContext)
        self.Module = self.llvm.CreateModule(str2constcharp("hot_code"))
        self.Builder = self.llvm.CreateBuilder(None)
        self.assembler = LLVM_Assembler(self)

    def setup_once(self):
        pass

    def dispatch_ops(self, func, entry, inputargs, ops):
        #FIXME: opnames, enums, desc counts, parse args
        #TODO: guards
        self.ssa_vars = {} #map ssa names to LLVM objects
        self.const_cnt = 0 #counter to help keep llvm's ssa names unique
        self.descrs = [] #save descr objects from branches in order as they're seen
        descr_phis = {} #map label descrs to phi values
        descr_blocks = {} #map label descrs to their blocks
        desc_cnt = 0

        for c, arg in enumerate(inputargs):
            name = repr(arg)
            ssa_vars[name] = self.llvm.GetParam(func, c)

        for op in ops: #hoping if we use the opcode numbers and else if's this'll optimise to a jump table
            if op.opnum == 1: #JUMP
                block = descr_blocks[op.getdescr()]
                phis = descr_phis[op.getdescr()]
                c = 0

                for arg, typ, name in self.parse_args(op.getargslist(), ssa_vars):
                    phi = phis[c]
                    self.llvm.AddIncoming(phi, arg, block)
                    c += 1

                self.llvm.BuildBr(self.Builder, block)

            elif op.opnum == 2: #FINISH
                self.descrs.append(op.getdescr())
                self.llvm.BuildRet(self.Builder, ssa_vars[op._args[0]]) #TODO: return both arg as well as desc count

            elif op.opnum == 4: #LABEL
                last_block = self.llvm.GetInsertBlock(self.Builder)
                loop_header = self.llvm.LLVMAppendBasicBlock(func,
                                                             str2constcharp("loop_header"))
                br = self.llvm.BuildBr(self.Builder, loop_header) #llvm requires explicit branching even for fall through
                self.llvm.PositionBuilderAtEnd(self.Builder, loop_header)

                phis = []

                for arg, typ, name in self.parse_args(op.getargslist(), ssa_vars):
                    phi = self.llvm.BuildPhi(self.Builder, typ,
                                             str2constcharp(name+"_phi"))
                    self.llvm.AddIncoming(phi, arg, last_block)
                    self.ssa_vars[name] = phi #this introduces divergence between our ssa values and llvm's, hope that's not too hacky
                    phis.append(phi)

                descr_phis[op.getdescr()] = phis

            elif op.opnum == 31: #INT_ADD
                args = []
                for arg in op.getargslist():
                    args.append(arg.getvalue() if arg.is_constant() else ssa_vars[arg.name])
                res_name = 'pass'
                self.ssa_vars[res_name] = self.llvm.BuildAdd(self.Builder, args[0],
                                                        args[1], 1, 1,
                                                        str2constcharp(res_name))

            elif op.opnum == 99: #INT_LE
                args = []
                for arg, typ, name in self.parseargs(args, ssa_vars):
                    args.append(arg)
                lhs = args[0]
                rhs = args[1]
                ssa_vars[op.name] = self.llvm.BuildICmp(self.Builder, enumop,
                                                        lhs, rhs, str2constcharp(op.name))

    def parse_args(self, args, ssa_vars): #convert opcode args into LLVM objects and types
        llvm_args = []
        for arg in args:
            if arg.is_constant():
                if arg.datatype == 'i':
                    if arg.
                    self.llvm.ConstInt(LLVMIntType(arg.bitsize), arg.getvalue(), )
        return llvm_args

    def verify(self):
        verified = self.llvm.VerifyModule(self.Module)
        if verified: #returns 0 on success
            raise Exception("Malformed IR")


    def compile_loop(self, inputargs, operations, looptoken, jd_id=0,
                     unique_id=0, log=True, name='', logger=None):

        arg_types = [arg.datatype for arg in inputargs]
        ret_type = lltype.Signed #hard coding for now
        llvm_arg_types = self.convert_args(inputargs)
        print(dir(operations[1]))
        print(operations[1]._args)

        signature = self.llvm.FunctionType(self.llvm.IntType(32),
                                      llvm_arg_types,
                                      len(inputargs), 0)
        trace = self.llvm.AddFunction(self.Module,
                                 str2constcharp("trace"),
                                 signature)
        self.entry = self.llvm.AppendBasicBlock(trace, str2constcharp("entry"))
        self.llvm.PositionBuilderAtEnd(self.Builder, self.entry)

        self.dispatch_ops(trace, entry, inputargs, operations)

        if self.debug:
            self.verify()

        self.assembler.JIT_compile(self.Module, looptoken, inputargs) #set compiled loop token and func addr

        #FUNC_PTR = lltype.Ptr(lltype.FuncType(arg_types, ret_type))
        #func = rffi.cast(FUNC_PTR, addr)
        #self.execute_token = self.make_executable_token(arg_types)
        lltype.free(llvm_arg_types, flavor='raw')

    def convert_args(self, inputargs):
        arg_array = rffi.CArray(self.llvm.TypeRef) #TODO: look into if missing out on optimisations by not using fixed array
        arg_types_ptr = lltype.malloc(arg_array, n=len(inputargs), flavor='raw')
        arg_types = arg_types_ptr._getobj()

        for c, arg in enumerate(inputargs):
            typ = self.get_llvm_type(arg)
            arg_types.setitem(c, typ)
        return arg_types_ptr

    def get_llvm_type(self, val):
        if val.datatype == 'i':
            return self.llvm.IntType(val.bytesize)
