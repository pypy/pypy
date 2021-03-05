from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU
from rpython.jit.backend.model import CompiledLoopToken, CPUTotalTracker
from rpython.rtyper.lltypesystem import rffi, lltype
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

        self.thread_safe_context = self.llvm.CreateThreadSafeContext(None)

    def setup_once(self):
        pass

    def verify(self):
        verified = self.llvm.VerifyModule(self.Module)
        if verified: #returns 0 on success
            raise Exception("Malformed IR")

    def compile_loop(self, inputargs, operations, looptoken, jd_id=0,
                     unique_id=0, log=True, name='', logger=None):

        module = self.llvm.CreateModule(str2constcharp(name))
        builder = self.llvm.CreateBuilder(None)
        arg_types = [arg.datatype for arg in inputargs]
        ret_type = lltype.Signed #hard coding for now
        llvm_arg_types = self.convert_args(inputargs)

        signature = self.llvm.FunctionType(self.llvm.IntType(32),
                                      llvm_arg_types,
                                      len(inputargs), 0)
        trace = self.llvm.AddFunction(module,
                                 str2constcharp("trace"),
                                 signature)
        entry = self.llvm.AppendBasicBlock(trace, str2constcharp("entry"))
        self.llvm.PositionBuilderAtEnd(builder, entry)

        dispatcher = LLVMOpDispatcher(self, builder)
        looptoken.dispathcer = dispatcher #this class holds data about llvm's state, so helpful to keep around on a per-loop basis for use by bridges

        dispatcher.func = trace
        dispatcher.dispatch_ops(inputargs, operations)

        if self.debug:
            self.verify()

        self.assembler.jit_compile(module, looptoken, inputargs) #set compiled loop token and func addr

        #FUNC_PTR = lltype.Ptr(lltype.FuncType(arg_types, ret_type))
        #func = rffi.cast(FUNC_PTR, addr)
        #self.execute_token = self.make_executable_token(arg_types)
        lltype.free(llvm_arg_types, flavor='raw')

    def compile_bridge(self, faildescr, inputargs, operations, looptoken):
        #patch_block = self.dispatcher.bailout_blocks[faildescr]
        #instr = self.llvm.GetFirstInstruction(patch_block)
        #self.llvm.EraseInstruction(instr)
        #self.llvm.PositionBuilderAtEnd(self.Builder, patch_block)

        #self.dispatcher.dispatch_ops()
        pass
    """
    look up faildescr's bailout block, set builder to top of block, erase ret instruction, parse as normal - bridge is now patched :)
    """

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
