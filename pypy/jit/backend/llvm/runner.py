import py, sys
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import ConstInt, AbstractDescr, INT
from pypy.jit.backend import model
from pypy.jit.backend.llvm import llvm_rffi
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.history import TreeLoop
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.x86 import symbolic     # xxx

TreeLoop._llvm_compiled_index = -1


class LLVMCPU(model.AbstractCPU):
    is_oo = False
    RAW_VALUE = rffi.CFixedArray(rffi.ULONGLONG, 1)
    SIGNED_VALUE = rffi.CFixedArray(lltype.Signed, 1)
    POINTER_VALUE = rffi.CFixedArray(llmemory.GCREF, 1)

    def __init__(self, rtyper, stats=None, translate_support_code=False,
                 annmixlevel=None):
        self.rtyper = rtyper
        self.translate_support_code = translate_support_code
        self.compiled_functions = []
        self.fail_ops = []
        self.in_out_args = []
        self._descr_caches = {}
        self.fielddescr_vtable = self.fielddescrof(rclass.OBJECT, 'typeptr')
        if sys.maxint == 2147483647:
            self.size_of_int = 4
        else:
            self.size_of_int = 8

    def setup_once(self):
        if not we_are_translated():
            llvm_rffi.teardown_now()
        llvm_rffi.LLVM_SetFlags()
        self.module = llvm_rffi.LLVMModuleCreateWithName("pypyjit")
        if self.size_of_int == 4:
            self.ty_int = llvm_rffi.LLVMInt32Type()
        else:
            self.ty_int = llvm_rffi.LLVMInt64Type()
        self.ty_void = llvm_rffi.LLVMVoidType()
        self.ty_bit = llvm_rffi.LLVMInt1Type()
        self.ty_char = llvm_rffi.LLVMInt8Type()
        self.ty_char_ptr = llvm_rffi.LLVMPointerType(self.ty_char, 0)
        self.ty_char_ptr_ptr = llvm_rffi.LLVMPointerType(self.ty_char_ptr, 0)
        self.ty_int_ptr = llvm_rffi.LLVMPointerType(self.ty_int, 0)
        self.ty_int_ptr_ptr = llvm_rffi.LLVMPointerType(self.ty_int_ptr, 0)
        self.const_zero = self._make_const_int(0)
        self.const_one  = self._make_const_int(1)
        self.const_minint = self._make_const_int(-sys.maxint-1)
        self.const_null_charptr = self._make_const(0, self.ty_char_ptr)
        #
        arglist = lltype.malloc(rffi.CArray(llvm_rffi.LLVMTypeRef), 0,
                                flavor='raw')
        self.ty_func = llvm_rffi.LLVMFunctionType(self.ty_int, arglist, 0,
                                                  False)
        lltype.free(arglist, flavor='raw')
        #
        self.f_add_ovf = llvm_rffi.LLVM_Intrinsic_add_ovf(self.module,
                                                          self.ty_int)
        self.f_sub_ovf = llvm_rffi.LLVM_Intrinsic_sub_ovf(self.module,
                                                          self.ty_int)
        self.f_mul_ovf = llvm_rffi.LLVM_Intrinsic_mul_ovf(self.module,
                                                          self.ty_int)
        if we_are_translated():
            XXX - fix-me
        else:
            self.exc_type = lltype.malloc(rffi.CArray(lltype.Signed), 1,
                                          zero=True, flavor='raw')
            self.exc_value = lltype.malloc(rffi.CArray(llmemory.GCREF), 1,
                                           zero=True, flavor='raw')
        self.backup_exc_type = lltype.malloc(rffi.CArray(lltype.Signed), 1,
                                             zero=True, flavor='raw')
        self.backup_exc_value = lltype.malloc(rffi.CArray(llmemory.GCREF), 1,
                                              zero=True, flavor='raw')
        self.const_exc_type = self._make_const(self.exc_type,
                                               self.ty_char_ptr_ptr)
        self.const_exc_value = self._make_const(self.exc_value,
                                                self.ty_char_ptr_ptr)
        self.const_backup_exc_type = self._make_const(self.backup_exc_type,
                                                      self.ty_char_ptr_ptr)
        self.const_backup_exc_value = self._make_const(self.backup_exc_value,
                                                       self.ty_char_ptr_ptr)
        #
        self._setup_prebuilt_error('ovf', OverflowError)
        self._setup_prebuilt_error('zer', ZeroDivisionError)
        #
        self.ee = llvm_rffi.LLVM_EE_Create(self.module)
        if not we_are_translated():
            llvm_rffi.set_teardown_function(self._teardown)

    def _teardown(self):
        llvm_rffi.LLVMDisposeExecutionEngine(self.ee)

    def _setup_prebuilt_error(self, prefix, Class):
        if self.rtyper is not None:   # normal case
            bk = self.rtyper.annotator.bookkeeper
            clsdef = bk.getuniqueclassdef(Class)
            ll_inst = self.rtyper.exceptiondata.get_standard_ll_exc_instance(
                self.rtyper, clsdef)
        else:
            # for tests, a random emulated ll_inst will do
            ll_inst = lltype.malloc(rclass.OBJECT)
            ll_inst.typeptr = lltype.malloc(rclass.OBJECT_VTABLE,
                                            immortal=True)
        setattr(self, '_%s_error_type' % prefix,
                rffi.cast(lltype.Signed, ll_inst.typeptr))
        setattr(self, '_%s_error_value' % prefix,
                lltype.cast_opaque_ptr(llmemory.GCREF, ll_inst))
        setattr(self, 'const_%s_error_type' % prefix,
                self._make_const(ll_inst.typeptr, self.ty_char_ptr))
        setattr(self, 'const_%s_error_value' % prefix,
                self._make_const(ll_inst, self.ty_char_ptr))

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

    def _make_const_int(self, value):
        return llvm_rffi.LLVMConstInt(self.ty_int, value, True)

    def _make_const_bit(self, value):
        assert (value & ~1) == 0, "value is not 0 or 1"
        return llvm_rffi.LLVMConstInt(self.ty_bit, value, True)

    def _make_const(self, value, ty_result):
        value_as_signed = rffi.cast(lltype.Signed, value)
        llvmconstint = self._make_const_int(value_as_signed)
        llvmconstptr = llvm_rffi.LLVMConstIntToPtr(llvmconstint, ty_result)
        return llvmconstptr
    _make_const._annspecialcase_ = 'specialize:argtype(1)'

    def _lltype2llvmtype(self, TYPE):
        if TYPE is lltype.Void:
            return self.ty_void
        elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
            return self.ty_char_ptr
        else:
            return self.ty_int

    def _get_var_type(self, v):
        if v.type == INT:
            return self.ty_int
        else:
            return self.ty_char_ptr

    def _get_pointer_type(self, v):
        if v.type == INT:
            return self.ty_int_ptr
        else:
            return self.ty_char_ptr_ptr

    # ------------------------------
    # Execution

    def set_future_value_int(self, index, intvalue):
        p = rffi.cast(lltype.Ptr(self.SIGNED_VALUE), self.in_out_args[index])
        p[0] = intvalue

    def set_future_value_ptr(self, index, ptrvalue):
        p = rffi.cast(lltype.Ptr(self.POINTER_VALUE), self.in_out_args[index])
        p[0] = ptrvalue

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

    def get_latest_value_ptr(self, index):
        p = rffi.cast(lltype.Ptr(self.POINTER_VALUE), self.in_out_args[index])
        return p[0]

    def get_exception(self):
        return self.backup_exc_type[0]

    def get_exc_value(self):
        return self.backup_exc_value[0]

    def clear_exception(self):
        self.backup_exc_type[0] = 0
        self.backup_exc_value[0] = lltype.nullptr(llmemory.GCREF.TO)

    def set_overflow_error(self):
        self.backup_exc_type[0] = self._ovf_error_type
        self.backup_exc_value[0] = self._ovf_error_value

    def set_zero_division_error(self):
        self.backup_exc_type[0] = self._zer_error_type
        self.backup_exc_value[0] = self._zer_error_value

    @staticmethod
    def cast_adr_to_int(x):
        return rffi.cast(lltype.Signed, x)

    @staticmethod
    def cast_int_to_adr(x):
        if we_are_translated():
            return rffi.cast(llmemory.Address, x)
        else:
            # indirect casting because the above doesn't work with ll2ctypes
            return llmemory.cast_ptr_to_adr(rffi.cast(llmemory.GCREF, x))

    def fielddescrof(self, S, fieldname):
        try:
            return self._descr_caches['field', S, fieldname]
        except KeyError:
            pass
        ofs, size = symbolic.get_field_token(S, fieldname,
                                             self.translate_support_code)
        if (isinstance(getattr(S, fieldname), lltype.Ptr) and
            getattr(S, fieldname).TO._gckind == 'gc'):
            size = -1
        descr = FieldDescr(ofs, size)
        self._descr_caches['field', S, fieldname] = descr
        return descr

    def calldescrof(self, FUNC, ARGS, RESULT):
        try:
            return self._descr_caches['call', ARGS, RESULT]
        except KeyError:
            pass
        #
        param_types = lltype.malloc(rffi.CArray(llvm_rffi.LLVMTypeRef),
                                    len(ARGS), flavor='raw')
        for i in range(len(ARGS)):
            param_types[i] = self._lltype2llvmtype(ARGS[i])
        ty_func = llvm_rffi.LLVMFunctionType(self._lltype2llvmtype(RESULT),
                                             param_types, len(ARGS), 0)
        lltype.free(param_types, flavor='raw')
        ty_funcptr = llvm_rffi.LLVMPointerType(ty_func, 0)
        #
        result_mask = -1
        if RESULT is lltype.Void:
            pass
        elif isinstance(RESULT, lltype.Ptr) and RESULT.TO._gckind == 'gc':
            pass
        else:
            result_size = symbolic.get_size(RESULT,
                                            self.translate_support_code)
            if result_size < self.size_of_int:
                result_mask = (1 << (result_size*8)) - 1
        descr = CallDescr(ty_funcptr, result_mask)
        self._descr_caches['call', ARGS, RESULT] = descr
        return descr


class FieldDescr(AbstractDescr):
    def __init__(self, offset, size):
        self.offset = offset
        self.size = size      # set to -1 to mark a pointer field

class CallDescr(AbstractDescr):
    def __init__(self, ty_function_ptr, result_mask=-1):
        self.ty_function_ptr = ty_function_ptr
        self.result_mask = result_mask

# ____________________________________________________________

class LLVMJITCompiler(object):
    FUNC = lltype.FuncType([], lltype.Signed)

    def __init__(self, cpu, loop):
        self.cpu = cpu
        self.loop = loop

    def start_generating_function(self):
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
            ty = self.cpu._get_pointer_type(loop.inputargs[i])
            llvmconstptr = self.cpu._make_const(self.cpu.in_out_args[i], ty)
            res = llvm_rffi.LLVMBuildLoad(self.builder, llvmconstptr, "")
            self.phi_incoming_values.append([res])
        self.bb_start = llvm_rffi.LLVMAppendBasicBlock(func, "")
        llvm_rffi.LLVMBuildBr(self.builder, self.bb_start)
        #
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, self.bb_start)
        for v in loop.inputargs:
            ty = self.cpu._get_var_type(v)
            phi = llvm_rffi.LLVMBuildPhi(self.builder, ty, "")
            self.vars[v] = phi

    def generate_loop_body(self):
        func = self.compiling_func
        self.pending_blocks = [(self.loop.operations, self.bb_start, False)]
        while self.pending_blocks:
            operations, bb, exc = self.pending_blocks.pop()
            self._generate_branch(operations, bb, exc)
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
        if index < 0:
            self.loop._llvm_compiled_index = len(self.cpu.compiled_functions)
            self.cpu.compiled_functions.append(func_ptr)
        else:
            self.cpu.compiled_functions[index] = func_ptr

    def _generate_branch(self, operations, basicblock, exc):
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, basicblock)
        # The flag 'exc' is set to True if we are a branch handling a
        # GUARD_EXCEPTION or GUARD_NO_EXCEPTION.  In this case, we have to
        # store away the exception into self.backup_exc_xxx, *unless* the
        # branch starts with a further GUARD_EXCEPTION/GUARD_NO_EXCEPTION.
        if exc:
            opnum = operations[0].opnum
            if opnum not in (rop.GUARD_EXCEPTION, rop.GUARD_NO_EXCEPTION):
                self._store_away_exception()
        # Normal handling of the operations follows.
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

    def _store_away_exception(self):
        # etype, evalue: ty_char_ptr
        etype = llvm_rffi.LLVMBuildLoad(self.builder,
                                        self.cpu.const_exc_type, "")
        llvm_rffi.LLVMBuildStore(self.builder,
                                 self.cpu.const_null_charptr,
                                 self.cpu.const_exc_type)
        llvm_rffi.LLVMBuildStore(self.builder,
                                 etype,
                                 self.cpu.const_backup_exc_type)
        evalue = llvm_rffi.LLVMBuildLoad(self.builder,
                                         self.cpu.const_exc_value, "")
        llvm_rffi.LLVMBuildStore(self.builder,
                                 self.cpu.const_null_charptr,
                                 self.cpu.const_exc_value)
        llvm_rffi.LLVMBuildStore(self.builder,
                                 evalue,
                                 self.cpu.const_backup_exc_value)

    def getintarg(self, v):
        try:
            value_ref = self.vars[v]
        except KeyError:
            assert isinstance(v, ConstInt)
            return self.cpu._make_const_int(v.value)
        else:
            return self._cast_to_int(value_ref)

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
            return self.cpu._make_const_bit(v.value)
        else:
            return self._cast_to_bit(value_ref)

    def _cast_to_bit(self, value_ref):
        ty = llvm_rffi.LLVMTypeOf(value_ref)
        if ty == self.cpu.ty_bit:
            return value_ref
        elif ty == self.cpu.ty_int:
            return llvm_rffi.LLVMBuildTrunc(self.builder, value_ref,
                                            self.cpu.ty_bit, "")
        else:
            raise AssertionError("type is not an int nor a bit")

    def getptrarg(self, v):
        try:
            value_ref = self.vars[v]
        except KeyError:
            return self.cpu._make_const(v.getaddr(self.cpu),
                                        self.cpu.ty_char_ptr_ptr)
        else:
            ty = llvm_rffi.LLVMTypeOf(value_ref)
            assert ty != self.cpu.ty_int and ty != self.cpu.ty_bit
            return value_ref

    for _opname, _llvmname in [('INT_ADD', 'Add'),
                               ('INT_SUB', 'Sub'),
                               ('INT_MUL', 'Mul'),
                               ('INT_FLOORDIV', 'SDiv'),
                               ('INT_MOD', 'SRem'),
                               ('INT_LSHIFT', 'Shl'),
                               ('INT_RSHIFT', 'AShr'),
                               ('UINT_RSHIFT', 'LShr'),
                               ('INT_AND', 'And'),
                               ('INT_OR',  'Or'),
                               ('INT_XOR', 'Xor'),
                               ]:
        exec py.code.Source('''
            def generate_%s(self, op):
                self.vars[op.result] = llvm_rffi.LLVMBuild%s(
                    self.builder,
                    self.getintarg(op.args[0]),
                    self.getintarg(op.args[1]),
                    "")
        ''' % (_opname, _llvmname)).compile()

    def generate_INT_NEG(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildNeg(self.builder,
                                                    self.getintarg(op.args[0]),
                                                    "")

    def generate_INT_INVERT(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildNot(self.builder,
                                                    self.getintarg(op.args[0]),
                                                    "")

    def generate_INT_IS_TRUE(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildICmp(self.builder,
                                                    llvm_rffi.Predicate.NE,
                                                    self.getintarg(op.args[0]),
                                                    self.cpu.const_zero,
                                                    "")

    def generate_INT_ADD_OVF(self, op):
        self._generate_ovf_op(op, self.cpu.f_add_ovf)

    def generate_INT_SUB_OVF(self, op):
        self._generate_ovf_op(op, self.cpu.f_sub_ovf)

    def generate_INT_MUL_OVF(self, op):
        self._generate_ovf_op(op, self.cpu.f_mul_ovf)

    def generate_INT_NEG_OVF(self, op):
        arg = self.getintarg(op.args[0])
        self.vars[op.result] = llvm_rffi.LLVMBuildNeg(self.builder, arg, "")
        ovf = llvm_rffi.LLVMBuildICmp(self.builder,
                                      llvm_rffi.Predicate.EQ,
                                      arg,
                                      self.cpu.const_minint,
                                      "")
        self._generate_set_ovf(ovf)

    def generate_INT_LSHIFT_OVF(self, op):
        arg0 = self.getintarg(op.args[0])
        arg1 = llvm_rffi.LLVMBuildShl(self.builder,
                                      self.cpu.const_one,
                                      self.getintarg(op.args[1]),
                                      "")
        self._generate_ovf_test(self.cpu.f_mul_ovf, arg0, arg1, op.result)

    def _generate_ovf_op(self, op, f_intrinsic):
        self._generate_ovf_test(f_intrinsic,
                                self.getintarg(op.args[0]),
                                self.getintarg(op.args[1]),
                                op.result)

    def _generate_ovf_test(self, f_intrinsic, arg0, arg1, result):
        arglist = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), 2,
                                flavor='raw')
        arglist[0] = arg0
        arglist[1] = arg1
        tmp = llvm_rffi.LLVMBuildCall(self.builder, f_intrinsic,
                                      arglist, 2, "")
        lltype.free(arglist, flavor='raw')
        self.vars[result] = llvm_rffi.LLVMBuildExtractValue(self.builder,
                                                            tmp, 0, "")
        ovf = llvm_rffi.LLVMBuildExtractValue(self.builder, tmp, 1, "")
        self._generate_set_ovf(ovf)

    def _generate_set_ovf(self, ovf_flag):
        exc_type = llvm_rffi.LLVMBuildSelect(self.builder, ovf_flag,
                                             self.cpu.const_ovf_error_type,
                                             self.cpu.const_null_charptr,
                                             "")
        llvm_rffi.LLVMBuildStore(self.builder, exc_type,
                                 self.cpu.const_exc_type)
        exc_value = llvm_rffi.LLVMBuildSelect(self.builder, ovf_flag,
                                              self.cpu.const_ovf_error_value,
                                              self.cpu.const_null_charptr,
                                              "")
        llvm_rffi.LLVMBuildStore(self.builder, exc_value,
                                 self.cpu.const_exc_value)

    def generate_GUARD_FALSE(self, op):
        self._generate_guard(op, self.getbitarg(op.args[0]), True)

    def generate_GUARD_TRUE(self, op):
        self._generate_guard(op, self.getbitarg(op.args[0]), False)

    def generate_GUARD_VALUE(self, op):
        if op.args[0].type == INT:
            arg0 = self.getintarg(op.args[0])
            arg1 = self.getintarg(op.args[1])
        else:
            arg0 = self.getptrarg(op.args[0])
            arg1 = self.getptrarg(op.args[1])
        equal = llvm_rffi.LLVMBuildICmp(self.builder,
                                        llvm_rffi.Predicate.EQ,
                                        arg0, arg1, "")
        self._generate_guard(op, equal, False)

    def generate_GUARD_CLASS(self, op):
        loc = self._generate_field_gep(op.args[0], self.cpu.fielddescr_vtable)
        cls = llvm_rffi.LLVMBuildLoad(self.builder, loc, "")
        equal = llvm_rffi.LLVMBuildICmp(self.builder,
                                        llvm_rffi.Predicate.EQ,
                                        cls,
                                        self.getintarg(op.args[1]), "")
        self._generate_guard(op, equal, False)

    def generate_GUARD_NO_EXCEPTION(self, op):
        # etype: ty_char_ptr
        etype = llvm_rffi.LLVMBuildLoad(self.builder,
                                        self.cpu.const_exc_type, "")
        eisnull = llvm_rffi.LLVMBuildICmp(self.builder,
                                          llvm_rffi.Predicate.EQ,
                                          etype,
                                          self.cpu.const_null_charptr, "")
        self._generate_guard(op, eisnull, False, exc=True)

    def generate_GUARD_EXCEPTION(self, op):
        v = op.args[0]
        assert isinstance(v, ConstInt)
        # etype, expectedtype: ty_char_ptr
        expectedtype = self.cpu._make_const(v.value, self.cpu.ty_char_ptr)
        etype = llvm_rffi.LLVMBuildLoad(self.builder,
                                        self.cpu.const_exc_type, "")
        eisequal = llvm_rffi.LLVMBuildICmp(self.builder,
                                           llvm_rffi.Predicate.EQ,
                                           etype,
                                           expectedtype, "")
        self._generate_guard(op, eisequal, False, exc=True)
        self.vars[op.result] = llvm_rffi.LLVMBuildLoad(self.builder,
                                                      self.cpu.const_exc_value,
                                                      "")

    def _generate_guard(self, op, verify_condition, reversed, exc=False):
        func = self.compiling_func
        bb_on_track = llvm_rffi.LLVMAppendBasicBlock(func, "")
        bb_off_track = llvm_rffi.LLVMAppendBasicBlock(func, "")
        llvm_rffi.LLVMBuildCondBr(self.builder, verify_condition,
                                  bb_on_track, bb_off_track)
        if reversed:
            bb_on_track, bb_off_track = bb_off_track, bb_on_track
        # generate the on-track part first, and the off-track part later
        self.pending_blocks.append((op.suboperations, bb_off_track, exc))
        llvm_rffi.LLVMPositionBuilderAtEnd(self.builder, bb_on_track)

    def generate_JUMP(self, op):
        if op.jump_target is self.loop:
            basicblock = llvm_rffi.LLVMGetInsertBlock(self.builder)
            self.phi_incoming_blocks.append(basicblock)
            for i in range(len(op.args)):
                incoming = self.phi_incoming_values[i]
                v = op.args[i]
                if v.type == INT:
                    value_ref = self.getintarg(v)
                else:
                    value_ref = self.getptrarg(v)
                incoming.append(value_ref)
            llvm_rffi.LLVMBuildBr(self.builder, self.bb_start)
        else:
            index = op.jump_target._llvm_compiled_index
            assert index >= 0
            self._generate_fail(op.args, index)

    def generate_FAIL(self, op):
        i = len(self.cpu.fail_ops)
        self.cpu.fail_ops.append(op)
        self._generate_fail(op.args, ~i)

    def _generate_fail(self, args, index):
        self.cpu._ensure_out_args(len(args))
        for i in range(len(args)):
            v = args[i]
            if v.type == INT:
                value_ref = self.getintarg(v)
                ty = self.cpu.ty_int_ptr
            else:
                value_ref = self.getptrarg(v)
                ty = self.cpu.ty_char_ptr_ptr
            llvmconstptr = self.cpu._make_const(self.cpu.in_out_args[i], ty)
            llvm_rffi.LLVMBuildStore(self.builder, value_ref,
                                     llvmconstptr)
        llvm_rffi.LLVMBuildRet(self.builder, self.cpu._make_const_int(index))

    def _generate_field_gep(self, v_structure, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        indices = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), 1,
                                flavor='raw')
        indices[0] = self.cpu._make_const_int(fielddescr.offset)
        location = llvm_rffi.LLVMBuildGEP(self.builder,
                                          self.getptrarg(v_structure),
                                          indices, 1, "")
        lltype.free(indices, flavor='raw')
        if fielddescr.size < 0:   # pointer field
            ty = self.cpu.ty_char_ptr_ptr
        else:
            assert fielddescr.size == symbolic.get_size(lltype.Signed,  # XXX
                                              self.cpu.translate_support_code)
            ty = self.cpu.ty_int_ptr
        return llvm_rffi.LLVMBuildBitCast(self.builder, location, ty, "")

    def generate_GETFIELD_GC(self, op):
        loc = self._generate_field_gep(op.args[0], op.descr)
        # XXX zero-extension for char fields
        self.vars[op.result] = llvm_rffi.LLVMBuildLoad(self.builder,
                                                       loc, "")

    def generate_SETFIELD_GC(self, op):
        loc = self._generate_field_gep(op.args[0], op.descr)
        if llvm_rffi.LLVMTypeOf(loc) == self.cpu.ty_char_ptr_ptr:
            value_ref = self.getptrarg(op.args[1])
        else:
            value_ref = self.getintarg(op.args[1])
            # XXX mask for char fields
        llvm_rffi.LLVMBuildStore(self.builder, value_ref, loc, "")

    def generate_CALL(self, op):
        calldescr = op.descr
        assert isinstance(calldescr, CallDescr)
        v = op.args[0]
        if isinstance(v, ConstInt):
            func = self.cpu._make_const(v.value, calldescr.ty_function_ptr)
        else:
            func = self.getintarg(v)
            func = llvm_rffi.LLVMBuildIntToPtr(self.builder,
                                               func,
                                               calldescr.ty_function_ptr, "")
        nb_args = len(op.args) - 1
        arglist = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), nb_args,
                                flavor='raw')
        for i in range(nb_args):
            v = op.args[1 + i]
            if v.type == INT:
                value_ref = self.getintarg(v)
            else:
                value_ref = self.getptrarg(v)
            arglist[i] = value_ref
        res = llvm_rffi.LLVMBuildCall(self.builder,
                                      func, arglist, nb_args, "")
        lltype.free(arglist, flavor='raw')
        if op.result is not None:
            if calldescr.result_mask != -1:
                mask = self.cpu._make_const_int(calldescr.result_mask)
                res = llvm_rffi.LLVMBuildAnd(self.builder,
                                             res, mask, "")
            self.vars[op.result] = res

    def generate_CAST_PTR_TO_INT(self, op):
        res = llvm_rffi.LLVMBuildPtrToInt(self.builder,
                                          self.getptrarg(op.args[0]),
                                          self.cpu.ty_int, "")
        self.vars[op.result] = res

    def generate_CAST_INT_TO_PTR(self, op):
        res = llvm_rffi.LLVMBuildIntToPtr(self.builder,
                                          self.getintarg(op.args[0]),
                                          self.cpu.ty_char_ptr, "")
        self.vars[op.result] = res

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

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(LLVMCPU)
