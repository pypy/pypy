from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.backend.model import CompiledLoopToken, CPUTotalTracker
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str
from rpython.rtyper.tool.rffi_platform import DefinedConstantInteger
from rpython.jit.backend.llvm.llvm_api import LLVM_API
from rpython.jit.backend.llvm.llvm_parse_ops import LLVM_Op_Dispatcher
from rpython.jit.backend.llvm.assembler import LLVM_Assembler

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None,
                 translate_support_code=False, gcdescr=None, debug=False):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        self.tracker = CPUTotalTracker()
        self.debug = debug
        self.llvm = LLVM_API()
        self.dispatcher = LLVM_Op_Dispatcher(self)
        self.assembler = LLVM_Assembler(self)

        self.ThreadSafeContext = self.llvm.CreateThreadSafeContext(None)
        self.Context = self.llvm.GetContext(self.ThreadSafeContext)
        self.Module = self.llvm.CreateModule(str2constcharp("hot_code"))
        self.Builder = self.llvm.CreateBuilder(None)

    def setup_once(self):
        pass

    def verify(self):
        verified = self.llvm.VerifyModule(self.Module)
        if verified: #returns 0 on success
            raise Exception("Malformed IR")

    def compile_loop(self, inputargs, operations, looptoken, jd_id=0,
                     unique_id=0, log=True, name='', logger=None):

        arg_types = [arg.datatype for arg in inputargs]
        ret_type = lltype.Signed #hard coding for now
        llvm_arg_types = self.convert_args(inputargs)

        signature = self.llvm.FunctionType(self.llvm.IntType(32),
                                      llvm_arg_types,
                                      len(inputargs), 0)
        trace = self.llvm.AddFunction(self.Module,
                                 str2constcharp("trace"),
                                 signature)
        self.entry = self.llvm.AppendBasicBlock(trace, str2constcharp("entry"))
        self.llvm.PositionBuilderAtEnd(self.Builder, self.entry)

        self.dispatcher.dispatch_ops(trace, entry, inputargs, operations)

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
