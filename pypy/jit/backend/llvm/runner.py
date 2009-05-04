import py, sys
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.backend import model
from pypy.jit.backend.llvm import llvm_rffi
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop


class LLVMCPU(model.AbstractCPU):
    RAW_VALUE = rffi.CFixedArray(rffi.ULONGLONG, 1)
    SIGNED_VALUE = rffi.CFixedArray(lltype.Signed, 1)
    STUB_FUNC = lltype.FuncType([rffi.VOIDP], lltype.Signed)

    def __init__(self, rtyper, stats=None, translate_support_code=False,
                 annmixlevel=None):
        self.rtyper = rtyper
        self.translate_support_code = translate_support_code
        self.ty_funcs = {}
        self.fail_ops = []
        self.in_out_args = []
        self.entry_stubs = {}

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
        self.ty_charp = llvm_rffi.LLVMPointerType(self.ty_char, 0)
        #
        arglist = lltype.malloc(rffi.CArray(llvm_rffi.LLVMTypeRef), 1,
                                flavor='raw')
        arglist[0] = self.ty_charp
        self.ty_stub_func = llvm_rffi.LLVMFunctionType(self.ty_int, arglist,
                                                       1, False)
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
        self.compiling_loop = loop
        self._ensure_in_args(len(loop.inputargs))
        ty_func = self.get_ty_func(len(loop.inputargs))
        func = llvm_rffi.LLVMAddFunction(self.module, "", ty_func)
        llvm_rffi.LLVMSetFunctionCallConv(func, llvm_rffi.CallConv.Fast)
        loop._llvm_func = func
        self.vars = {}
        for i in range(len(loop.inputargs)):
            self.vars[loop.inputargs[i]] = llvm_rffi.LLVMGetParam(func, i)
        self.builder = llvm_rffi.LLVMCreateBuilder()
        bb_start = llvm_rffi.LLVMAppendBasicBlock(func, "entry")
        self.pending_blocks = [(loop.operations, bb_start)]
        while self.pending_blocks:
            operations, bb = self.pending_blocks.pop()
            self._generate_branch(operations, bb)
        llvm_rffi.LLVMDisposeBuilder(self.builder)
        self.vars = None
        #
        loop._llvm_func_addr = llvm_rffi.LLVM_EE_getPointerToFunction(
            self.ee, loop._llvm_func)
        if not we_are_translated():
            print '--- function is at %r ---' % (loop._llvm_func_addr,)
        #
        loop._llvm_entry_stub = self._get_entry_stub(loop)
        llvm_rffi.LLVMDumpModule(self.module)
        self.compiling_loop = None

    def _get_entry_stub(self, loop):
        key = len(loop.inputargs)
        try:
            stub = self.entry_stubs[key]
        except KeyError:
            stub = self.entry_stubs[key] = self._build_entry_stub(key)
        return stub

    def _build_entry_stub(self, nb_args):
        stubfunc = llvm_rffi.LLVMAddFunction(self.module, "stub",
                                             self.ty_stub_func)
        basicblock = llvm_rffi.LLVMAppendBasicBlock(stubfunc, "entry")
        builder = llvm_rffi.LLVMCreateBuilder()
        llvm_rffi.LLVMPositionBuilderAtEnd(builder, basicblock)
        args = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), nb_args,
                             flavor='raw')
        for i in range(nb_args):
            ty_int_ptr = llvm_rffi.LLVMPointerType(self.ty_int, 0)
            addr_as_signed = rffi.cast(lltype.Signed, self.in_out_args[i])
            llvmconstint = self._make_const_int(addr_as_signed)
            llvmconstptr = llvm_rffi.LLVMConstIntToPtr(llvmconstint, ty_int_ptr)
            args[i] = llvm_rffi.LLVMBuildLoad(builder, llvmconstptr, "")
        #
        realtype = llvm_rffi.LLVMPointerType(self.get_ty_func(nb_args), 0)
        realfunc = llvm_rffi.LLVMGetParam(stubfunc, 0)
        realfunc = llvm_rffi.LLVMBuildBitCast(builder, realfunc, realtype, "")
        res = llvm_rffi.LLVMBuildCall(builder, realfunc, args, nb_args, "")
        llvm_rffi.LLVMSetInstructionCallConv(res, llvm_rffi.CallConv.Fast)
        lltype.free(args, flavor='raw')
        llvm_rffi.LLVMBuildRet(builder, res)
        llvm_rffi.LLVMDisposeBuilder(builder)
        #
        stub = llvm_rffi.LLVM_EE_getPointerToFunction(self.ee, stubfunc)
        if not we_are_translated():
            print '--- stub is at %r ---' % (stub,)
        return rffi.cast(lltype.Ptr(self.STUB_FUNC), stub)

    def get_ty_func(self, nb_args):
        try:
            return self.ty_funcs[nb_args]
        except KeyError:
            arglist = lltype.malloc(rffi.CArray(llvm_rffi.LLVMTypeRef),
                                    nb_args, flavor='raw')
            for i in range(nb_args):
                arglist[i] = self.ty_int
            ty_func = llvm_rffi.LLVMFunctionType(self.ty_int, arglist,
                                                 nb_args, False)
            lltype.free(arglist, flavor='raw')
            self.ty_funcs[nb_args] = ty_func
            return ty_func

    def _ensure_in_args(self, count):
        while len(self.in_out_args) < count:
            self.in_out_args.append(lltype.malloc(self.RAW_VALUE, flavor='raw'))

    _ensure_out_args = _ensure_in_args

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
        return llvm_rffi.LLVMConstInt(self.ty_int, value, True)

    def _cast_to_int(self, value_ref):
        ty = llvm_rffi.LLVMTypeOf(value_ref)
        if ty == self.ty_int:
            return value_ref
        elif ty == self.ty_bit:
            return llvm_rffi.LLVMBuildZExt(self.builder, value_ref,
                                           self.ty_int, "")
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
        if ty == self.ty_bit:
            return value_ref
        elif ty == self.ty_int:
            return llvm_rffi.LLVMBuildTrunc(self.builder, value_ref,
                                            self.ty_bit, "")
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
        func = self.compiling_loop._llvm_func
        bb_on_track = llvm_rffi.LLVMAppendBasicBlock(func, "")
        bb_off_track = llvm_rffi.LLVMAppendBasicBlock(func, "")
        llvm_rffi.LLVMBuildCondBr(self.builder, self.getbitarg(op.args[0]),
                                  bb_on_track, bb_off_track)
        # generate the on-track part first, and the off-track part later
        self.pending_blocks.append((op.suboperations, bb_off_track))
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, bb_on_track)

    def generate_JUMP(self, op):
        args = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), len(op.args),
                             flavor='raw')
        for i in range(len(op.args)):
            args[i] = self.getintarg(op.args[i])
        res = llvm_rffi.LLVMBuildCall(self.builder, op.jump_target._llvm_func,
                                      args, len(op.args), "")
        llvm_rffi.LLVMSetInstructionCallConv(res, llvm_rffi.CallConv.Fast)
        llvm_rffi.LLVMSetTailCall(res, True)
        llvm_rffi.LLVMBuildRet(self.builder, res)
        lltype.free(args, flavor='raw')

    def generate_FAIL(self, op):
        self._ensure_out_args(len(op.args))
        for i in range(len(op.args)):
            value_ref = self.vars[op.args[i]]
            ty = llvm_rffi.LLVMTypeOf(value_ref)
            typtr = llvm_rffi.LLVMPointerType(ty, 0)
            addr_as_signed = rffi.cast(lltype.Signed, self.in_out_args[i])
            llvmconstint = self._make_const_int(addr_as_signed)
            llvmconstptr = llvm_rffi.LLVMConstIntToPtr(llvmconstint, typtr)
            llvm_rffi.LLVMBuildStore(self.builder, value_ref,
                                     llvmconstptr)
        i = len(self.fail_ops)
        self.fail_ops.append(op)
        llvm_rffi.LLVMBuildRet(self.builder, self._make_const_int(i))

    # ------------------------------
    # Execution

    def set_future_value_int(self, index, intvalue):
        p = rffi.cast(lltype.Ptr(self.SIGNED_VALUE), self.in_out_args[index])
        p[0] = intvalue

    def execute_operations(self, loop):
        print 'execute_operations: %s' % (loop._llvm_func_addr,)
        import time; time.sleep(2)
        res = loop._llvm_entry_stub(loop._llvm_func_addr)
        print '\t--->', res
        return self.fail_ops[res]

    def get_latest_value_int(self, index):
        p = rffi.cast(lltype.Ptr(self.SIGNED_VALUE), self.in_out_args[index])
        return p[0]

# ____________________________________________________________

class MissingOperation(Exception):
    pass

all_operations = {}
for _key, _value in rop.__dict__.items():
    if 'A' <= _key <= 'Z':
        assert _value not in all_operations
        methname = 'generate_' + _key
        if hasattr(LLVMCPU, methname):
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
