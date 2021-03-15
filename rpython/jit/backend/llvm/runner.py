from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU, jitframe
from rpython.jit.backend.model import CompiledLoopToken, CPUTotalTracker
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rtyper.lltypesystem.rffi import str2constcharp, constcharp2str
from rpython.rtyper.tool.rffi_platform import DefinedConstantInteger
from rpython.jit.backend.llvm.llvm_api import LLVMAPI
from rpython.jit.backend.llvm.llvm_parse_ops import LLVMOpDispatcher
from rpython.jit.backend.llvm.assembler import LLVMAssembler
from rpython.jit.metainterp import history
import ctypes

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None,
                 translate_support_code=False, gcdescr=None, debug=True):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        self.tracker = CPUTotalTracker()
        self.debug = debug
        self.llvm = LLVMAPI()
        self.assembler = LLVMAssembler(self)
        self.thread_safe_context = self.llvm.CreateThreadSafeContext(None)
        self.context = self.llvm.GetContext(self.thread_safe_context)
        self.dispatchers = {} #map loop tokens to their dispatcher instance
        self.WORD = 8
        self.llvm_int_type = self.llvm.IntType(self.context, self.WORD*8) #would like to define these in LLVMAPI but need the context arg
        self.llvm_int_ptr = self.llvm.PointerType(self.llvm_int_type, 0)
        self.llvm_void_ptr = self.llvm.PointerType(self.llvm.IntType(self.context, 8), 0) #llvm doesn't have void*, represents as i8*

    def decl_jitframe(self, num_args):
        elem_array = rffi.CArray(self.llvm.TypeRef)
        elem_count = 8
        packed = 0
        elem_types = lltype.malloc(elem_array, n=elem_count, flavor='raw')
        elem_types.__setitem__(0, self.llvm_void_ptr)
        elem_types.__setitem__(1, self.llvm_void_ptr)
        elem_types.__setitem__(2, self.llvm_void_ptr)
        elem_types.__setitem__(3, self.llvm_void_ptr)
        elem_types.__setitem__(4, self.llvm_void_ptr)
        elem_types.__setitem__(5, self.llvm_void_ptr)
        elem_types.__setitem__(6, self.llvm_void_ptr)
        arg_array = self.llvm.ArrayType(self.llvm_int_type, num_args)
        elem_types.__setitem__(7, arg_array)
        jitframe_type = self.llvm.StructType(self.context, elem_types,
                                               elem_count, packed)
        lltype.free(elem_types, flavor='raw')

        return jitframe_type

    def setup_once(self):
        pass

    def verify(self, module):
        verified = self.llvm.VerifyModule(module)
        if verified: #returns 0 on success
            raise Exception("Malformed IR")

    def compile_loop(self, inputargs, operations, looptoken, jd_id=0,
                     unique_id=0, log=True, name='', logger=None):
        module = self.llvm.CreateModule(str2constcharp(name), self.context)
        builder = self.llvm.CreateBuilder(self.context)
        jitframe_type = self.decl_jitframe(len(inputargs))
        jitframe_ptr = self.llvm.PointerType(jitframe_type, 0)
        arg_array = rffi.CArray(self.llvm.TypeRef)
        arg_types = lltype.malloc(arg_array, n=2, flavor='raw')
        arg_types.__setitem__(0, jitframe_ptr)
        arg_types.__setitem__(1, self.llvm_void_ptr)
        signature = self.llvm.FunctionType(jitframe_ptr,
                                           arg_types,
                                           2, 0)
        lltype.free(arg_types, flavor='raw')
        trace = self.llvm.AddFunction(module,
                                      str2constcharp("trace"),
                                      signature)
        entry = self.llvm.AppendBasicBlock(self.context, trace,
                                           str2constcharp("entry"))
        self.llvm.PositionBuilderAtEnd(builder, entry)
        dispatcher = LLVMOpDispatcher(self, builder, module,
                                      trace, jitframe_type)
        self.dispatchers[looptoken] = dispatcher #this class holds data about llvm's state, so helpful to keep around on a per-loop basis for bridges
        dispatcher.dispatch_ops(inputargs, operations)

        if self.debug:
            self.verify(module)

        self.assembler.jit_compile(module, looptoken, inputargs, dispatcher) #set compiled loop token and func addr

    def execute_token(self, looptoken, *ARGS):
        func = self.make_execute_token(lltype.Signed) #FIXME: parse input args into types or ask if something already does that
        deadframe =  func(looptoken, *ARGS)
        return deadframe

    def get_latest_descr(self, deadframe):
        deadframe = lltype.cast_opaque_ptr(jitframe.JITFRAMEPTR, deadframe)
        descr = deadframe.jf_descr
        descr_addr = rffi.cast(lltype.Signed, descr)
        return ctypes.cast(descr_addr, ctypes.py_object).value #TODO: ask about how much of a massive hack this might be

    def compile_bridge(self, faildescr, inputargs, operations, looptoken):
        dispatcher = self.dispatchers[looptoken]
        patch_block = dispatcher.bailout_blocks[faildescr]
        instr = self.llvm.GetFirstInstruction(patch_block)
        self.llvm.EraseInstruction(instr)
        self.llvm.PositionBuilderAtEnd(dispatcher.builder, patch_block)
        dispatcher.dispatch_ops(inputargs, operations, is_bridge=True)

        if self.debug:
            self.verify(dispatcher.module)

        self.assembler.jit_compile(dispatcher.module, looptoken,
                                   inputargs, dispatcher)

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
            return self.llvm.IntType(self.context, val.bytesize)
