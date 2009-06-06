import py, sys
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.backend import model
from pypy.jit.backend.llvm import llvm_rffi
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.history import TreeLoop
from pypy.jit.metainterp.resoperation import rop

TreeLoop._llvm_compiled_index = -1


class LLVMCPU(model.AbstractCPU):
    RAW_VALUE = rffi.CFixedArray(rffi.ULONGLONG, 1)
    SIGNED_VALUE = rffi.CFixedArray(lltype.Signed, 1)

    def __init__(self, rtyper, stats=None, translate_support_code=False,
                 annmixlevel=None):
        self.rtyper = rtyper
        self.translate_support_code = translate_support_code
        self.compiled_functions = []
        self.fail_ops = []
        self.in_out_args = []

    def setup_once(self):
        if not we_are_translated():
            teardown_now()
        llvm_rffi.LLVM_SetFlags()
        self.module = llvm_rffi.LLVMModuleCreateWithName("pypyjit")
        if sys.maxint == 2147483647:
            self.ty_int = llvm_rffi.LLVMInt32Type()
        else:
            self.ty_int = llvm_rffi.LLVMInt64Type()
        self.ty_bit = llvm_rffi.LLVMInt1Type()
        self.ty_char = llvm_rffi.LLVMInt8Type()
        self.ty_int_ptr = llvm_rffi.LLVMPointerType(self.ty_int, 0)
        #
        arglist = lltype.malloc(rffi.CArray(llvm_rffi.LLVMTypeRef), 0,
                                flavor='raw')
        self.ty_func = llvm_rffi.LLVMFunctionType(self.ty_int, arglist, 0,
                                                  False)
        lltype.free(arglist, flavor='raw')
        #
        self.ee = llvm_rffi.LLVM_EE_Create(self.module)
        if not we_are_translated():
            set_teardown_function(self._teardown)

    def _teardown(self):
        llvm_rffi.LLVMDisposeExecutionEngine(self.ee)

    # ------------------------------
    # Compilation

    def compile_operations(self, loop):
        compiler = LLVMJITCompiler(self, loop)
        compiler.start_generating_function()
        compiler.generate_initial_arguments_load()
        compiler.generate_loop_body()
        compiler.close_phi_nodes()
        compiler.done_generating_function()
        llvm_rffi.LLVMDumpModule(self.module)   # xxx for debugging

    def _ensure_in_args(self, count):
        while len(self.in_out_args) < count:
            self.in_out_args.append(lltype.malloc(self.RAW_VALUE, flavor='raw'))

    _ensure_out_args = _ensure_in_args

    # ------------------------------
    # Execution

    def set_future_value_int(self, index, intvalue):
        p = rffi.cast(lltype.Ptr(self.SIGNED_VALUE), self.in_out_args[index])
        p[0] = intvalue

    def execute_operations(self, loop):
        index = loop._llvm_compiled_index
        assert index >= 0
        while True:
            func_ptr = self.compiled_functions[index]
            print 'execute_operations: %d (at 0x%x)' % (
                index,  rffi.cast(lltype.Signed, func_ptr))
            index = func_ptr()
            print '\t--->', index
            if index < 0:
                break
        return self.fail_ops[~index]

    def get_latest_value_int(self, index):
        p = rffi.cast(lltype.Ptr(self.SIGNED_VALUE), self.in_out_args[index])
        return p[0]

# ____________________________________________________________

class LLVMJITCompiler(object):
    FUNC = lltype.FuncType([], lltype.Signed)

    def __init__(self, cpu, loop):
        self.cpu = cpu
        self.loop = loop

    def start_generating_function(self):
        if self.loop._llvm_compiled_index < 0:
            self.loop._llvm_compiled_index = len(self.cpu.compiled_functions)
            self.cpu.compiled_functions.append(lltype.nullptr(self.FUNC))
        func = llvm_rffi.LLVMAddFunction(self.cpu.module, "", self.cpu.ty_func)
        self.compiling_func = func
        self.builder = llvm_rffi.LLVMCreateBuilder()
        self.vars = {}

    def generate_initial_arguments_load(self):
        loop = self.loop
        func = self.compiling_func
        bb_entry = llvm_rffi.LLVMAppendBasicBlock(func, "entry")
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, bb_entry)
        self.cpu._ensure_in_args(len(loop.inputargs))
        self.phi_incoming_blocks = [bb_entry]
        self.phi_incoming_values = []
        for i in range(len(loop.inputargs)):
            addr_as_signed = rffi.cast(lltype.Signed, self.cpu.in_out_args[i])
            llvmconstint = self._make_const_int(addr_as_signed)
            llvmconstptr = llvm_rffi.LLVMConstIntToPtr(llvmconstint,
                                                       self.cpu.ty_int_ptr)
            res = llvm_rffi.LLVMBuildLoad(self.builder, llvmconstptr, "")
            self.phi_incoming_values.append([res])
        self.bb_start = llvm_rffi.LLVMAppendBasicBlock(func, "")
        llvm_rffi.LLVMBuildBr(self.builder, self.bb_start)
        #
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, self.bb_start)
        for i in range(len(loop.inputargs)):
            phi = llvm_rffi.LLVMBuildPhi(self.builder, self.cpu.ty_int, "")
            self.vars[loop.inputargs[i]] = phi

    def generate_loop_body(self):
        func = self.compiling_func
        self.pending_blocks = [(self.loop.operations, self.bb_start)]
        while self.pending_blocks:
            operations, bb = self.pending_blocks.pop()
            self._generate_branch(operations, bb)
        self.bb_start = lltype.nullptr(llvm_rffi.LLVMBasicBlockRef.TO)

    def close_phi_nodes(self):
        incoming_blocks = lltype.malloc(
            rffi.CArray(llvm_rffi.LLVMBasicBlockRef),
            len(self.phi_incoming_blocks), flavor='raw')
        incoming_values = lltype.malloc(
            rffi.CArray(llvm_rffi.LLVMValueRef),
            len(self.phi_incoming_blocks), flavor='raw')
        for j in range(len(self.phi_incoming_blocks)):
            incoming_blocks[j] = self.phi_incoming_blocks[j]
        loop = self.loop
        for i in range(len(loop.inputargs)):
            phi = self.vars[loop.inputargs[i]]
            incoming = self.phi_incoming_values[i]
            for j in range(len(self.phi_incoming_blocks)):
                incoming_values[j] = incoming[j]
            llvm_rffi.LLVMAddIncoming(phi, incoming_values, incoming_blocks,
                                      len(self.phi_incoming_blocks))
        lltype.free(incoming_values, flavor='raw')
        lltype.free(incoming_blocks, flavor='raw')

    def done_generating_function(self):
        llvm_rffi.LLVMDisposeBuilder(self.builder)
        #
        func_addr = llvm_rffi.LLVM_EE_getPointerToFunction(self.cpu.ee,
                                                           self.compiling_func)
        if not we_are_translated():
            print '--- function is at %r ---' % (func_addr,)
        #
        func_ptr = rffi.cast(lltype.Ptr(self.FUNC), func_addr)
        index = self.loop._llvm_compiled_index
        self.cpu.compiled_functions[index] = func_ptr

    def _generate_branch(self, operations, basicblock):
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, basicblock)
        for op in operations:
            self._generate_op(op)

    def _generate_op(self, op):
        opnum = op.opnum
        for i, name in all_operations:
            if opnum == i:
                meth = getattr(self, name)
                meth(op)
                return
        else:
            raise MissingOperation(resoperation.opname[opnum])

    def getintarg(self, v):
        try:
            value_ref = self.vars[v]
        except KeyError:
            assert isinstance(v, ConstInt)
            return self._make_const_int(v.value)
        else:
            return self._cast_to_int(value_ref)

    def _make_const_int(self, value):
        return llvm_rffi.LLVMConstInt(self.cpu.ty_int, value, True)

    def _cast_to_int(self, value_ref):
        ty = llvm_rffi.LLVMTypeOf(value_ref)
        if ty == self.cpu.ty_int:
            return value_ref
        elif ty == self.cpu.ty_bit:
            return llvm_rffi.LLVMBuildZExt(self.builder, value_ref,
                                           self.cpu.ty_int, "")
        else:
            raise AssertionError("type is not an int nor a bit")

    def getbitarg(self, v):
        try:
            value_ref = self.vars[v]
        except KeyError:
            assert isinstance(v, ConstInt)
            return self._make_const_bit(v.value)
        else:
            return self._cast_to_bit(value_ref)

    def _make_const_bit(self, value):
        assert (value & ~1) == 0, "value is not 0 or 1"
        return llvm_rffi.LLVMConstInt(self.ty_bit, value, True)

    def _cast_to_bit(self, value_ref):
        ty = llvm_rffi.LLVMTypeOf(value_ref)
        if ty == self.cpu.ty_bit:
            return value_ref
        elif ty == self.cpu.ty_int:
            return llvm_rffi.LLVMBuildTrunc(self.builder, value_ref,
                                            self.cpu.ty_bit, "")
        else:
            raise AssertionError("type is not an int nor a bit")

    for _opname, _llvmname in [('INT_ADD', 'Add'),
                               ('INT_SUB', 'Sub'),
                               ('UINT_RSHIFT', 'LShr'),
                               ]:
        exec py.code.Source('''
            def generate_%s(self, op):
                self.vars[op.result] = llvm_rffi.LLVMBuild%s(
                    self.builder,
                    self.getintarg(op.args[0]),
                    self.getintarg(op.args[1]),
                    "")
        ''' % (_opname, _llvmname)).compile()

    def generate_INT_INVERT(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildNot(self.builder,
                                                    self.getintarg(op.args[0]),
                                                    "")

    def generate_INT_IS_TRUE(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildICmp(self.builder,
                                                    llvm_rffi.Predicate.NE,
                                                    self.getintarg(op.args[0]),
                                                    self._make_const_int(0),
                                                    "")

    def generate_GUARD_TRUE(self, op):
        func = self.compiling_func
        bb_on_track = llvm_rffi.LLVMAppendBasicBlock(func, "")
        bb_off_track = llvm_rffi.LLVMAppendBasicBlock(func, "")
        llvm_rffi.LLVMBuildCondBr(self.builder, self.getbitarg(op.args[0]),
                                  bb_on_track, bb_off_track)
        # generate the on-track part first, and the off-track part later
        self.pending_blocks.append((op.suboperations, bb_off_track))
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, bb_on_track)

    def generate_JUMP(self, op):
        if op.jump_target is self.loop:
            basicblock = llvm_rffi.LLVMGetInsertBlock(self.builder)
            self.phi_incoming_blocks.append(basicblock)
            for i in range(len(op.args)):
                incoming = self.phi_incoming_values[i]
                incoming.append(self.getintarg(op.args[i]))
            llvm_rffi.LLVMBuildBr(self.builder, self.bb_start)
        else:
            xxx

    def generate_FAIL(self, op):
        self.cpu._ensure_out_args(len(op.args))
        for i in range(len(op.args)):
            value_ref = self.vars[op.args[i]]
            ty = llvm_rffi.LLVMTypeOf(value_ref)
            typtr = llvm_rffi.LLVMPointerType(ty, 0)
            addr_as_signed = rffi.cast(lltype.Signed, self.cpu.in_out_args[i])
            llvmconstint = self._make_const_int(addr_as_signed)
            llvmconstptr = llvm_rffi.LLVMConstIntToPtr(llvmconstint, typtr)
            llvm_rffi.LLVMBuildStore(self.builder, value_ref,
                                     llvmconstptr)
        i = len(self.cpu.fail_ops)
        self.cpu.fail_ops.append(op)
        llvm_rffi.LLVMBuildRet(self.builder, self._make_const_int(~i))

# ____________________________________________________________

class MissingOperation(Exception):
    pass

all_operations = {}
for _key, _value in rop.__dict__.items():
    if 'A' <= _key <= 'Z':
        assert _value not in all_operations
        methname = 'generate_' + _key
        if hasattr(LLVMJITCompiler, methname):
            all_operations[_value] = methname
all_operations = unrolling_iterable(all_operations.items())

_teardown = None

def set_teardown_function(fn):
    global _teardown
    _teardown = fn

def teardown_now():
    global _teardown
    fn = _teardown
    _teardown = None
    if fn is not None:
        fn()
