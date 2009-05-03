import sys
from pypy.rpython.lltypesystem import lltype, rffi
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
        self.module = llvm_rffi.LLVMModuleCreateWithName("pypyjit")
        if sys.maxint == 2147483647:
            self.ty_int = llvm_rffi.LLVMInt32Type()
        else:
            self.ty_int = llvm_rffi.LLVMInt64Type()
        self.ty_int_ptr = llvm_rffi.LLVMPointerType(self.ty_int, 0)

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

    # ------------------------------
    # Compilation

    def compile_operations(self, loop):
        self._ensure_in_args(len(loop.inputargs))
        ty_func = self.get_ty_func(len(loop.inputargs))
        func = llvm_rffi.LLVMAddFunction(self.module, "", ty_func)
        self.vars = {}
        for i in range(len(loop.inputargs)):
            self.vars[loop.inputargs[i]] = llvm_rffi.LLVMGetParam(func, i)
        self.builder = llvm_rffi.LLVMCreateBuilder()
        self._generate_branch(loop.operations, func)
        llvm_rffi.LLVMDisposeBuilder(self.builder)
        self.builder = None
        self.vars = None
        #...
        llvm_rffi.LLVMDumpModule(self.module)
        loop._llvm_func = func

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

    def _generate_branch(self, operations, func):
        bb = llvm_rffi.LLVMAppendBasicBlock(func, "")
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, bb)
        #
        for op in operations:
            self._generate_op(op)
        #
        return bb

    def _generate_op(self, op):
        opnum = op.opnum
        for i, name in all_operations:
            if opnum == i:
                meth = getattr(self, name)
                meth(op)
                return
        else:
            raise MissingOperation(resoperation.opname[opnum])

    def getarg(self, v):
        try:
            return self.vars[v]
        except KeyError:
            assert isinstance(v, ConstInt)
            return self._make_const_int(v.value)

    def _make_const_int(self, value):
        return llvm_rffi.LLVMConstInt(self.ty_int, value, True)

    def generate_int_add(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildAdd(self.builder,
                                                      self.getarg(op.args[0]),
                                                      self.getarg(op.args[1]),
                                                      "")

    def generate_uint_rshift(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildLShr(self.builder,
                                                       self.getarg(op.args[0]),
                                                       self.getarg(op.args[1]),
                                                       "")

    def generate_int_invert(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildNot(self.builder,
                                                      self.vars[op.args[0]],
                                                      "")

    def generate_fail(self, op):
        self._ensure_out_args(len(op.args))
        for i in range(len(op.args)):
            addr_as_signed = rffi.cast(lltype.Signed, self.out_args[i])
            llvmconstint = self._make_const_int(addr_as_signed)
            llvmconstptr = llvm_rffi.LLVMConstIntToPtr(llvmconstint,
                                                       self.ty_int_ptr)
            llvm_rffi.LLVMBuildStore(self.builder, self.vars[op.args[i]],
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

    def get_latest_value_int(self, index):
        return rffi.cast(lltype.Signed, self.out_args[index][0])

# ____________________________________________________________

class MissingOperation(Exception):
    pass

all_operations = {}
for _key, _value in rop.__dict__.items():
    if 'A' <= _key <= 'Z':
        assert _value not in all_operations
        methname = 'generate_' + _key.lower()
        if hasattr(LLVMCPU, methname):
            all_operations[_value] = methname
all_operations = unrolling_iterable(all_operations.items())
