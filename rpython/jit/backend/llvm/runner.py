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

    def dispatch_ops(self, args, ops):
        ssa_vars = {}
        descrs = {}
        descr_cnt = 0

    def verify(self):
        verified = self.llvm.VerifyModule(self.Module)
        if verified: #returns 0 on success
            raise Exception("Malformed IR")


    def compile_loop(self, inputargs, operations, looptoken, jd_id=0,
                     unique_id=0, log=True, name='', logger=None):

        arg_types = [arg.datatype for arg in inputargs]
        ret_type = lltype.Signed #hard coding for now
        llvm_arg_types, llvm_args = self.convert_args(inputargs) #need all types in eq LLVM form

        signature = self.llvm.FunctionType(self.llvm.IntType(32),
                                      llvm_arg_types,
                                      len(inputargs), 0)
        trace = self.llvm.AddFunction(self.Module,
                                 str2constcharp("trace"),
                                 signature)
        entry = self.llvm.AppendBasicBlock(trace, str2constcharp("entry"))
        self.llvm.PositionBuilderAtEnd(self.Builder, entry)

        #this is where an opcode dispatch loop will go
        i1 = self.llvm.BuildAdd(self.Builder, llvm_args[0],
                           self.llvm.ConstInt(self.llvm.IntType(32), 1, 1),
                           str2constcharp("i1"))
        self.llvm.BuildRet(self.Builder, i1)

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

        args = []
        for c, arg in enumerate(inputargs):
            typ, ref = self.get_input_llvm_type(arg)
            arg_types.setitem(c, typ)
            args.append(ref)
        return (arg_types_ptr, args)

    def get_input_llvm_type(self, val):
        if val.datatype == 'i':
            int_type = self.llvm.IntType(val.bytesize)
            if val.signed == True:
                return (int_type, self.llvm.ConstInt(int_type, val.getvalue(), 1))
            else:
                return (int_type, self.llvm.ConstInt(int_type, val.getvalue(), 0))
