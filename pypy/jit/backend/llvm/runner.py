import py, sys
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.backend import model
from pypy.jit.backend.llvm import llvm_rffi
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop


class LLVMException(Exception):
    pass


class LLVMCPU(model.AbstractCPU):
    ARRAY_OF_VALUE_REFS = rffi.CArray(llvm_rffi.LLVMGenericValueRef)
    RAW_VALUE = rffi.CFixedArray(rffi.ULONGLONG, 1)

    def __init__(self, rtyper, stats=None, translate_support_code=False,
                 annmixlevel=None):
        self.rtyper = rtyper
        self.translate_support_code = translate_support_code
        self.ty_funcs = {}
        self.fail_ops = []
        self.in_args_count = 0
        self.in_args = lltype.malloc(self.ARRAY_OF_VALUE_REFS, 0,
                                     flavor='raw')
        self.out_args = []

    def setup_once(self):
        if not we_are_translated():
            teardown_now()
        self.module = llvm_rffi.LLVMModuleCreateWithName("pypyjit")
        if sys.maxint == 2147483647:
            self.ty_int = llvm_rffi.LLVMInt32Type()
        else:
            self.ty_int = llvm_rffi.LLVMInt64Type()
        self.ty_bit = llvm_rffi.LLVMInt1Type()

        mp = llvm_rffi.LLVMCreateModuleProviderForExistingModule(self.module)
        ee_out = lltype.malloc(rffi.CArray(llvm_rffi.LLVMExecutionEngineRef),
                               1, flavor='raw')
        error_out = lltype.malloc(rffi.CArray(rffi.CCHARP), 1, flavor='raw')
        error_out[0] = lltype.nullptr(rffi.CCHARP.TO)
        try:
            error = llvm_rffi.LLVMCreateJITCompiler(ee_out, mp, True,
                                                    error_out)
            if rffi.cast(lltype.Signed, error) != 0:
                raise LLVMException(rffi.charp2str(error_out[0]))
            self.ee = ee_out[0]
        finally:
            if error_out[0]:
                llvm_rffi.LLVMDisposeMessage(error_out[0])
            lltype.free(error_out, flavor='raw')
            lltype.free(ee_out, flavor='raw')
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
        #...
        llvm_rffi.LLVMDumpModule(self.module)
        self.compiling_loop = None

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
        if self.in_args_count <= count:
            count = (count + 8) & ~7       # increment by at least one
            new = lltype.malloc(self.ARRAY_OF_VALUE_REFS, count, flavor='raw')
            lltype.free(self.in_args, flavor='raw')
            for i in range(count):
                new[i] = lltype.nullptr(llvm_rffi.LLVMGenericValueRef.TO)
            self.in_args = new
            self.in_args_count = count

    def _ensure_out_args(self, count):
        while len(self.out_args) < count:
            self.out_args.append(lltype.malloc(self.RAW_VALUE, flavor='raw'))

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
        llvm_rffi.LLVMBuildRet(self.builder, res)
        llvm_rffi.LLVMSetTailCall(res, True)
        lltype.free(args, flavor='raw')

    def generate_FAIL(self, op):
        self._ensure_out_args(len(op.args))
        for i in range(len(op.args)):
            value_ref = self.vars[op.args[i]]
            ty = llvm_rffi.LLVMTypeOf(value_ref)
            typtr = llvm_rffi.LLVMPointerType(ty, 0)
            addr_as_signed = rffi.cast(lltype.Signed, self.out_args[i])
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
        assert index < self.in_args_count - 1
        self.in_args[index] = llvm_rffi.LLVMCreateGenericValueOfInt(
            self.ty_int, intvalue, True)

    def execute_operations(self, loop):
        retval = llvm_rffi.LLVMRunFunction(self.ee, loop._llvm_func,
                                           len(loop.inputargs),
                                           self.in_args)
        ulonglong = llvm_rffi.LLVMGenericValueToInt(retval, True)
        res = rffi.cast(lltype.Signed, ulonglong)
        llvm_rffi.LLVMDisposeGenericValue(retval)
        i = 0
        while self.in_args[i]:
            llvm_rffi.LLVMDisposeGenericValue(self.in_args[i])
            self.in_args[i] = lltype.nullptr(llvm_rffi.LLVMGenericValueRef.TO)
            i += 1
        return self.fail_ops[res]

    def get_latest_value_int(self, index):
        return rffi.cast(lltype.Signed, self.out_args[index][0])

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
