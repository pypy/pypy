from rpython.jit.backend.llsupport.llmodel import AbstractLLCPU, jitframe
from rpython.jit.backend.model import CPUTotalTracker
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.jit.backend.llvm.llvm_api import LLVMAPI, CString
from rpython.jit.backend.llvm.llvm_parse_ops import LLVMOpDispatcher
from rpython.jit.backend.llvm.assembler import LLVMAssembler
from rpython.jit.metainterp import history
import os

class LLVM_CPU(AbstractLLCPU):
    def __init__(self, rtyper, stats, opts=None,
                 translate_support_code=False, gcdescr=None, debug=True):
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)
        self.is_llvm = True
        self.supports_floats = True
        self.supports_singlefloats = True
        self.tracker = CPUTotalTracker()
        self.debug = debug
        self.llvm = LLVMAPI()
        self.assembler = LLVMAssembler(self)
        self.thread_safe_context = self.llvm.CreateThreadSafeContext(None)
        self.context = self.llvm.GetContext(self.thread_safe_context)
        self.dispatchers = {} #map loop tokens to their dispatcher instance
        self.descr_tokens = {} #map descrs to token values that llvm uses
        self.force_tokens = {}
        self.descr_token_cnt = 1 #start at 1 because memory is initailised to 0
        self.WORD = 8
        self.define_types()

    def define_types(self):
        self.llvm_bool_type = self.llvm.IntType(self.context, 1)
        self.llvm_char_type = self.llvm.IntType(self.context, self.WORD)
        self.llvm_short_type = self.llvm.IntType(self.context, self.WORD*2)
        self.llvm_int_type = self.llvm.IntType(self.context, self.WORD*8)
        self.llvm_wide_int = self.llvm.IntType(self.context, self.WORD*16) #for overflow checks
        self.llvm_float_type = self.llvm.FloatType(self.context) #DoubleTypeInContext
        self.llvm_single_float_type = self.llvm.SingleFloatType(self.context)
        self.llvm_indx_type = self.llvm.IntType(self.context, self.WORD*4) #llvm only allows signed 32bit ints for indecies (for some reason, and only sometimes)
        self.llvm_int_ptr = self.llvm.PointerType(self.llvm_int_type, 0)
        self.llvm_void_type = self.llvm.VoidType(self.context)
        self.llvm_void_ptr = self.llvm.PointerType(self.llvm.IntType(self.context, 8), 0) #llvm doesn't have void*, represents as i8*

    def decl_jitframe(self, num_args):
        arg_array = self.llvm.ArrayType(self.llvm_int_type, num_args+1) #+1 for python metadata in element 0
        jitframe_subtypes = [self.llvm_void_ptr, self.llvm_int_type,
                               self.llvm_int_type, self.llvm_void_ptr,
                               self.llvm_void_ptr, self.llvm_void_ptr,
                               self.llvm_void_ptr, arg_array]
        elem_array = rffi.CArray(self.llvm.TypeRef)
        elem_count = 8
        packed = 0
        elem_types = lltype.malloc(elem_array, n=elem_count, flavor='raw')
        for c, typ in enumerate(jitframe_subtypes):
            elem_types[c] = typ
        jitframe_type = self.llvm.StructType(self.context, elem_types,
                                               elem_count, packed)
        lltype.free(elem_types, flavor='raw')

        return (jitframe_type, jitframe_subtypes)

    def verify(self, module):
        verified = self.llvm.VerifyModule(module)
        if verified: #returns 0 on success
            raise Exception("Malformed IR")

    def write_ir(self, module, name):
        cstring = CString("./ir-"+name+".bc")
        self.llvm.WriteBitcodeToFile(module, cstring.ptr)
        os.system("llvm-dis ir-"+name+".bc")
        os.system("rm ir-"+name+".bc")

    def dump_looptoken(self, looptoken): #only dumps unoptimised IR
        dispatcher = self.dispatchers[looptoken]
        module = dispatcher.module
        self.write_ir(module, "dmp")
        os.system("cat ir-dmp.ll")
        os.system("rm ir-dmp.ll")

    def set_debug(self, value):
        previous_value = self.debug
        self.debug = value
        return previous_value

    def force(self, force_token):
        deadframe_addr = self.read_int_at_mem(force_token, 0, self.WORD, 0)
        deadframe = rffi.cast(jitframe.JITFRAMEPTR, deadframe_addr)
        deadframe = deadframe.resolve()
        force_descr_token = rffi.cast(lltype.Signed, deadframe.jf_force_descr)
        num_failargs = self.force_tokens[force_descr_token]
        deadframe.jf_descr = rffi.cast(llmemory.GCREF, force_descr_token)
        descr = self.gc_ll_descr.getframedescrs(self).arraydescr
        ofs = self.unpack_arraydescr(descr)
        for i in range(num_failargs):
            failarg = self.read_int_at_mem(force_token, self.WORD*(i+1),
                                           self.WORD, 0)
            self.write_int_at_mem(deadframe, ofs+(self.WORD*i), self.WORD,
                                  failarg)

        return deadframe

    def malloc_wrapper(self, size):
        # llexternal functions don't play nice with LLVM
        return self.gc_ll_descr.malloc_fn_ptr(size)

    def compile_loop(self, inputargs, operations, looptoken, jd_id=0,
                     unique_id=0, log=True, name='trace', logger=None):
        cstring = CString('hot_code')
        module = self.llvm.CreateModule(cstring.ptr, self.context)
        self.llvm.SetModuleDataLayout(module, self.assembler.data_layout)
        self.llvm.SetTarget(module, self.assembler.triple)
        builder = self.llvm.CreateBuilder(self.context)
        jitframe_type, jitframe_subtypes = self.decl_jitframe(len(inputargs))
        jitframe_ptr = self.llvm.PointerType(jitframe_type, 0)
        arg_array = rffi.CArray(self.llvm.TypeRef)
        arg_types = lltype.malloc(arg_array, n=2, flavor='raw')
        arg_types[0] = jitframe_ptr
        arg_types[1] = self.llvm_void_ptr
        signature = self.llvm.FunctionType(jitframe_ptr, arg_types, 2, 0)
        lltype.free(arg_types, flavor='raw')
        cstring = CString(name)
        trace = self.llvm.AddFunction(module, cstring.ptr, signature)
        cstring = CString("entry")
        entry = self.llvm.AppendBasicBlock(self.context, trace,
                                           cstring.ptr)
        dispatcher = LLVMOpDispatcher(self, builder, module,
                                      entry, trace, jitframe_type,
                                      jitframe_subtypes)
        dispatcher.jitframe_depth = len(inputargs)
        self.dispatchers[looptoken] = dispatcher
        dispatcher.dispatch_ops(inputargs, operations)
        if self.debug:
            self.verify(module)
            self.write_ir(module, "org")
        fail_descr_rd_locs = [rffi.cast(rffi.USHORT, i)
                              for i in range(dispatcher.jitframe_depth)]
        history.BasicFailDescr.rd_locs = fail_descr_rd_locs
        self.assembler.jit_compile(module, looptoken, inputargs, dispatcher,
                                   dispatcher.jitframe_depth)

    def compile_bridge(self, faildescr, inputargs, operations, looptoken):
        dispatcher = self.dispatchers[looptoken]
        dispatcher.dispatch_ops(inputargs, operations, faildescr=faildescr)
        if self.debug:
            self.verify(dispatcher.module)
            self.write_ir(dispatcher.module, "org")
        fail_descr_rd_locs = [rffi.cast(rffi.USHORT, i)
                              for i in range(dispatcher.jitframe_depth)]
        history.BasicFailDescr.rd_locs = fail_descr_rd_locs
        self.assembler.jit_compile(dispatcher.module, looptoken,
                                   inputargs, dispatcher,
                                   dispatcher.jitframe_depth, is_bridge=True)

    def parse_arg_types(self, *ARGS):
        types = []
        for arg in ARGS:
            if type(arg) == int:
                types.append(lltype.Signed)
            elif type(arg) == float:
                types.append(lltype.Float)
            elif type(arg) == lltype._ptr:
                types.append(arg._TYPE)
            elif type(arg) == llmemory.AddressAsInt:
                types.append(arg.lltype())
            else:
                raise Exception("Unknown type: ", type(arg))
        return types

    def execute_token(self, looptoken, *ARGS):
        arg_types = self.parse_arg_types(*ARGS)
        func = self.make_execute_token(*arg_types)
        deadframe = func(looptoken, *ARGS)
        return deadframe

    def get_latest_descr(self, deadframe):
        deadframe = lltype.cast_opaque_ptr(jitframe.JITFRAMEPTR, deadframe)
        descr_token = rffi.cast(lltype.Signed, deadframe.jf_descr)
        return self.descr_tokens[descr_token]
