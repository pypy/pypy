from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.backend.model import CompiledLoopToken, CPUTotalTracker
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str
from rpython.rtyper.tool.rffi_platform import DefinedConstantInteger
from rpython.jit.backend.llvm.llvm_api import LLVMAPI
from rpython.jit.backend.llvm.llvm_parse_ops import LLVMOpDispatcher
from rpython.jit.backend.llvm.assembler import LLVMAssembler

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None,
                 translate_support_code=False, gcdescr=None, debug=False):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        self.tracker = CPUTotalTracker()
        self.debug = debug
        self.llvm = LLVMAPI()
        self.assembler = LLVMAssembler(self)
        self.context = self.llvm.CreateThreadSafeContext(None)
        self.dispatchers = {} #map loop tokens to their dispatcher instances
        self.WORD = 8

    def setup_once(self):
        pass

    def verify(self, module):
        verified = self.llvm.VerifyModule(module)
        if verified: #returns 0 on success
            raise Exception("Malformed IR")

    def compile_loop(self, inputargs, operations, looptoken, jd_id=0,
                     unique_id=0, log=True, name='', logger=None):
        module = self.llvm.CreateModule(str2constcharp(name))
        builder = self.llvm.CreateBuilder(None)
        llvm_arg_types = self.convert_args(inputargs)
        arg_array = rffi.CArray(self.llvm.TypeRef)
        arg_types_ptr = lltype.malloc(arg_array, n=len(inputargs), flavor='raw')
        arg_types = arg_types_ptr._getobj()
        arg_types.setitem(0, self.llvm.VoidPtr)

        signature = self.llvm.FunctionType(self.llvm.VoidPtr,
                                      llvm_arg_types,
                                      len(inputargs), 0)
        trace = self.llvm.AddFunction(module,
                                 str2constcharp("trace"),
                                 signature)
        entry = self.llvm.AppendBasicBlock(trace, str2constcharp("entry"))
        self.llvm.PositionBuilderAtEnd(builder, entry)

        dispatcher = LLVMOpDispatcher(self, builder, module, trace)
        self.dispatchers[looptoken] = dispatcher #this class holds data about llvm's state, so helpful to keep around on a per-loop basis for bridges
        dispatcher.dispatch_ops(inputargs, operations)

        if self.debug:
            self.verify(module)

        self.assembler.jit_compile(module, looptoken, inputargs, dispatcher) #set compiled loop token and func addr

        lltype.free(llvm_arg_types, flavor='raw')

    def compile_bridge(self, faildescr, inputargs, operations, looptoken):
        dispatcher = self.dispatchers[looptoken]
        patch_block = dispatcher.bailout_blocks[faildescr]
        instr = self.llvm.GetFirstInstruction(patch_block)
        self.llvm.EraseInstruction(instr)
        self.llvm.PositionBuilderAtEnd(dispatcher.builder, patch_block)
        dispatcher.dispatch_ops(inputargs, operations, is_bridge=True)

        if self.debug:
            self.verify(dispatcher.module)

        self.assembler.jit_compile(dispatcher.module, looptoken, inputargs, dispatcher)

    def make_executable_args(self, *ARGS):
        FUNCPTR = lltype.Ptr(lltype.FuncType([llmemory.GCREF, llmemory.Address],
                                             llmemory.GCREF))

        #func = rffi.cast(FUNCPTR, addr)

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
