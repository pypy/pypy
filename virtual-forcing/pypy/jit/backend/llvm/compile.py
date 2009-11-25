import py
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp.history import Const, INT
from pypy.jit.backend.llvm import llvm_rffi
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llvm.runner import SizeDescr, CallDescr
from pypy.jit.backend.llvm.runner import FieldDescr, ArrayDescr

# ____________________________________________________________

class LLVMJITCompiler(object):
    FUNC = lltype.FuncType([], lltype.Signed)
    lastovf = lltype.nullptr(llvm_rffi.LLVMValueRef.TO)

    def __init__(self, cpu, loop):
        self.cpu = cpu
        self.loop = loop

    def compile(self):
        self.start_generating_function()
        self.generate_initial_arguments_load()
        self.generate_loop_body()
        self.close_phi_nodes()
        self.done_generating_function()

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
        llvm_rffi.LLVMDumpValue(self.compiling_func)   # xxx for debugging
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
            assert isinstance(v, Const)
            return self.cpu._make_const_int(v.getint())
        else:
            return self._cast_to_int(value_ref)

    def _cast_to_int(self, value_ref):
        ty = llvm_rffi.LLVMTypeOf(value_ref)
        if ty == self.cpu.ty_int:
            return value_ref
        else:
            return llvm_rffi.LLVMBuildZExt(self.builder, value_ref,
                                           self.cpu.ty_int, "")

    def getbitarg(self, v):
        try:
            value_ref = self.vars[v]
        except KeyError:
            assert isinstance(v, Const)
            return self.cpu._make_const_bit(v.getint())
        else:
            return self._cast_to_bit(value_ref)

    def _cast_to_bit(self, value_ref):
        ty = llvm_rffi.LLVMTypeOf(value_ref)
        if ty == self.cpu.ty_bit:
            return value_ref
        else:
            return llvm_rffi.LLVMBuildTrunc(self.builder, value_ref,
                                            self.cpu.ty_bit, "")

    def getchararg(self, v):
        try:
            value_ref = self.vars[v]
        except KeyError:
            assert isinstance(v, Const)
            return self.cpu._make_const_char(v.getint())
        else:
            return self._cast_to_char(value_ref)

    def _cast_to_char(self, value_ref):
        ty = llvm_rffi.LLVMTypeOf(value_ref)
        if ty == self.cpu.ty_char:
            return value_ref
        elif ty == self.cpu.ty_int or ty == self.cpu.ty_unichar:
            return llvm_rffi.LLVMBuildTrunc(self.builder, value_ref,
                                            self.cpu.ty_char, "")
        elif ty == self.cpu.ty_bit:
            return llvm_rffi.LLVMBuildZExt(self.builder, value_ref,
                                           self.cpu.ty_char, "")
        else:
            raise AssertionError("type is not an int nor a bit")

    def getunichararg(self, v):
        try:
            value_ref = self.vars[v]
        except KeyError:
            assert isinstance(v, Const)
            return self.cpu._make_const_unichar(v.getint())
        else:
            return self._cast_to_unichar(value_ref)

    def _cast_to_unichar(self, value_ref):
        ty = llvm_rffi.LLVMTypeOf(value_ref)
        if ty == self.cpu.ty_unichar:
            return value_ref
        elif ty == self.cpu.ty_int:
            return llvm_rffi.LLVMBuildTrunc(self.builder, value_ref,
                                            self.cpu.ty_char, "")
        elif ty == self.cpu.ty_bit or ty == self.cpu.ty_char:
            return llvm_rffi.LLVMBuildZExt(self.builder, value_ref,
                                           self.cpu.ty_char, "")
        else:
            raise AssertionError("type is not an int nor a bit")

    def getptrarg(self, v):
        try:
            value_ref = self.vars[v]
        except KeyError:
            return self.cpu._make_const(v.getaddr(self.cpu),
                                        self.cpu.ty_char_ptr)
        else:
            ty = llvm_rffi.LLVMTypeOf(value_ref)
            if ty == self.cpu.ty_int:
                value_ref = llvm_rffi.LLVMBuildIntToPtr(self.builder,
                                                        value_ref,
                                                        self.cpu.ty_char_ptr,
                                                        "")
            else:
                assert (ty != self.cpu.ty_bit and
                        ty != self.cpu.ty_char and
                        ty != self.cpu.ty_unichar)
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

    for _opname, _predicate in [('INT_LT', llvm_rffi.Predicate.SLT),
                                ('INT_LE', llvm_rffi.Predicate.SLE),
                                ('INT_EQ', llvm_rffi.Predicate.EQ),
                                ('INT_NE', llvm_rffi.Predicate.NE),
                                ('INT_GT', llvm_rffi.Predicate.SGT),
                                ('INT_GE', llvm_rffi.Predicate.SGE),
                                ('UINT_LT', llvm_rffi.Predicate.ULT),
                                ('UINT_LE', llvm_rffi.Predicate.ULE),
                                ('UINT_GT', llvm_rffi.Predicate.UGT),
                                ('UINT_GE', llvm_rffi.Predicate.UGE)]:
        exec py.code.Source('''
            def generate_%s(self, op):
                self.vars[op.result] = llvm_rffi.LLVMBuildICmp(
                    self.builder,
                    %d,
                    self.getintarg(op.args[0]),
                    self.getintarg(op.args[1]),
                    "")
        ''' % (_opname, _predicate)).compile()

    def generate_INT_NEG(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildNeg(self.builder,
                                                    self.getintarg(op.args[0]),
                                                    "")

    def generate_INT_INVERT(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildNot(self.builder,
                                                    self.getintarg(op.args[0]),
                                                    "")

    def generate_INT_IS_TRUE(self, op):
        v = op.args[0]
        try:
            value_ref = self.vars[v]
            if llvm_rffi.LLVMTypeOf(value_ref) != self.cpu.ty_bit:
                raise KeyError
        except KeyError:
            res = llvm_rffi.LLVMBuildICmp(self.builder,
                                          llvm_rffi.Predicate.NE,
                                          self.getintarg(op.args[0]),
                                          self.cpu.const_zero,
                                          "")
        else:
            res = value_ref     # value_ref: ty_bit.  this is a no-op
        self.vars[op.result] = res

    def generate_BOOL_NOT(self, op):
        v = op.args[0]
        try:
            value_ref = self.vars[v]
            if llvm_rffi.LLVMTypeOf(value_ref) != self.cpu.ty_bit:
                raise KeyError
        except KeyError:
            res = llvm_rffi.LLVMBuildICmp(self.builder,
                                          llvm_rffi.Predicate.EQ,
                                          self.getintarg(op.args[0]),
                                          self.cpu.const_zero,
                                          "")
        else:
            # value_ref: ty_bit
            res = llvm_rffi.LLVMBuildNot(self.builder, value_ref, "")
        self.vars[op.result] = res

    def generate_INT_ADD_OVF(self, op):
        self._generate_ovf_op(op, self.cpu.f_add_ovf)

    def generate_INT_SUB_OVF(self, op):
        self._generate_ovf_op(op, self.cpu.f_sub_ovf)

    def generate_INT_MUL_OVF(self, op):
        self._generate_ovf_op(op, self.cpu.f_mul_ovf)

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
        self.lastovf = llvm_rffi.LLVMBuildExtractValue(self.builder, tmp, 1,
                                                       "")

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
        assert isinstance(v, Const)
        # etype, expectedtype: ty_char_ptr
        expectedtype = self.cpu._make_const(v.getint(), self.cpu.ty_char_ptr)
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

    def generate_GUARD_NO_OVERFLOW(self, op):
        self._generate_guard(op, self.lastovf, True)

    def generate_GUARD_OVERFLOW(self, op):
        self._generate_guard(op, self.lastovf, False)

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
        ty = self.cpu.types_ptr_by_index[fielddescr.size_index]
        location = llvm_rffi.LLVMBuildBitCast(self.builder, location, ty, "")
        return location

    def generate_GETFIELD_GC(self, op):
        loc = self._generate_field_gep(op.args[0], op.descr)
        self.vars[op.result] = llvm_rffi.LLVMBuildLoad(self.builder, loc, "")

    generate_GETFIELD_GC_PURE  = generate_GETFIELD_GC
    generate_GETFIELD_RAW      = generate_GETFIELD_GC
    generate_GETFIELD_RAW_PURE = generate_GETFIELD_GC

    def generate_SETFIELD_GC(self, op):
        fielddescr = op.descr
        loc = self._generate_field_gep(op.args[0], fielddescr)
        assert isinstance(fielddescr, FieldDescr)
        getarg = self.cpu.getarg_by_index[fielddescr.size_index]
        value_ref = getarg(self, op.args[1])
        llvm_rffi.LLVMBuildStore(self.builder, value_ref, loc, "")

    def generate_CALL(self, op):
        calldescr = op.descr
        assert isinstance(calldescr, CallDescr)
        ty_function_ptr = self.cpu.get_calldescr_ty_function_ptr(calldescr)
        v = op.args[0]
        if isinstance(v, Const):
            func = self.cpu._make_const(v.getint(), ty_function_ptr)
        else:
            func = self.getintarg(v)
            func = llvm_rffi.LLVMBuildIntToPtr(self.builder,
                                               func,
                                               ty_function_ptr, "")
        nb_args = len(op.args) - 1
        arglist = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), nb_args,
                                flavor='raw')
        for i in range(nb_args):
            v = op.args[1 + i]
            index = calldescr.args_indices[i]
            getarg = self.cpu.getarg_by_index[index]
            value_ref = getarg(self, v)
            arglist[i] = value_ref
        res = llvm_rffi.LLVMBuildCall(self.builder,
                                      func, arglist, nb_args, "")
        lltype.free(arglist, flavor='raw')
        if op.result is not None:
            assert calldescr.res_index >= 0
            self.vars[op.result] = res

    generate_CALL_PURE = generate_CALL

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

    def generate_OOIS(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildICmp(
            self.builder, llvm_rffi.Predicate.EQ,
            self.getptrarg(op.args[0]),
            self.getptrarg(op.args[1]), "")

    def generate_OOISNOT(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildICmp(
            self.builder, llvm_rffi.Predicate.NE,
            self.getptrarg(op.args[0]),
            self.getptrarg(op.args[1]), "")

    def generate_OOISNULL(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildICmp(
            self.builder, llvm_rffi.Predicate.EQ,
            self.getptrarg(op.args[0]),
            self.cpu.const_null_charptr, "")

    def generate_OONONNULL(self, op):
        self.vars[op.result] = llvm_rffi.LLVMBuildICmp(
            self.builder, llvm_rffi.Predicate.NE,
            self.getptrarg(op.args[0]),
            self.cpu.const_null_charptr, "")

    def generate_SAME_AS(self, op):
        if op.args[0].type == INT:
            self.vars[op.result] = self.getintarg(op.args[0])
        else:
            self.vars[op.result] = self.getptrarg(op.args[0])

    def _generate_len_gep(self, array_ref, ty, const_index_length):
        array = llvm_rffi.LLVMBuildBitCast(self.builder,
                                           array_ref, ty, "")
        indices = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), 2,
                                flavor='raw')
        indices[0] = self.cpu.const_zero
        indices[1] = const_index_length
        loc = llvm_rffi.LLVMBuildGEP(self.builder, array, indices, 2, "")
        lltype.free(indices, flavor='raw')
        return loc

    def _generate_len(self, op, ty, const_index_length):
        loc = self._generate_len_gep(self.getptrarg(op.args[0]),
                                     ty, const_index_length)
        self.vars[op.result] = llvm_rffi.LLVMBuildLoad(self.builder, loc, "")

    def generate_ARRAYLEN_GC(self, op):
        arraydescr = op.descr
        assert isinstance(arraydescr, ArrayDescr)
        self._generate_len(op, arraydescr.ty_array_ptr,
                           self.cpu.const_array_index_length)

    def _generate_gep(self, op, ty, const_index_array):
        array = llvm_rffi.LLVMBuildBitCast(self.builder,
                                           self.getptrarg(op.args[0]),
                                           ty, "")
        indices = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), 3,
                                flavor='raw')
        indices[0] = self.cpu.const_zero
        indices[1] = const_index_array
        indices[2] = self.getintarg(op.args[1])
        location = llvm_rffi.LLVMBuildGEP(self.builder, array, indices, 3, "")
        lltype.free(indices, flavor='raw')
        return location

    def _generate_array_gep(self, op):
        arraydescr = op.descr
        assert isinstance(arraydescr, ArrayDescr)
        location = self._generate_gep(op, arraydescr.ty_array_ptr,
                                      self.cpu.const_array_index_array)
        return location

    def generate_GETARRAYITEM_GC(self, op):
        loc = self._generate_array_gep(op)
        self.vars[op.result] = llvm_rffi.LLVMBuildLoad(self.builder, loc, "")

    generate_GETARRAYITEM_GC_PURE = generate_GETARRAYITEM_GC

    def generate_SETARRAYITEM_GC(self, op):
        loc = self._generate_array_gep(op)
        arraydescr = op.descr
        assert isinstance(arraydescr, ArrayDescr)
        getarg = self.cpu.getarg_by_index[arraydescr.itemsize_index]
        value_ref = getarg(self, op.args[2])
        llvm_rffi.LLVMBuildStore(self.builder, value_ref, loc, "")

    def generate_STRLEN(self, op):
        self._generate_len(op, self.cpu.ty_string_ptr,
                           self.cpu.const_string_index_length)

    def generate_UNICODELEN(self, op):
        self._generate_len(op, self.cpu.ty_unicode_ptr,
                           self.cpu.const_unicode_index_length)

    def generate_STRGETITEM(self, op):
        loc = self._generate_gep(op, self.cpu.ty_string_ptr,
                                 self.cpu.const_string_index_array)
        self.vars[op.result] = llvm_rffi.LLVMBuildLoad(self.builder, loc, "")

    def generate_UNICODEGETITEM(self, op):
        loc = self._generate_gep(op, self.cpu.ty_unicode_ptr,
                                 self.cpu.const_unicode_index_array)
        self.vars[op.result] = llvm_rffi.LLVMBuildLoad(self.builder, loc, "")

    def generate_STRSETITEM(self, op):
        loc = self._generate_gep(op, self.cpu.ty_string_ptr,
                                 self.cpu.const_string_index_array)
        value_ref = self.getchararg(op.args[2])
        llvm_rffi.LLVMBuildStore(self.builder, value_ref, loc, "")

    def generate_UNICODESETITEM(self, op):
        loc = self._generate_gep(op, self.cpu.ty_unicode_ptr,
                                 self.cpu.const_unicode_index_array)
        value_ref = self.getunichararg(op.args[2])
        llvm_rffi.LLVMBuildStore(self.builder, value_ref, loc, "")

    def _generate_new(self, size_ref):
        malloc_func = self.cpu._make_const(self.cpu.malloc_fn_ptr,
                                           self.cpu.ty_malloc_fn)
        arglist = lltype.malloc(rffi.CArray(llvm_rffi.LLVMValueRef), 1,
                                flavor='raw')
        arglist[0] = size_ref
        res = llvm_rffi.LLVMBuildCall(self.builder, malloc_func,
                                      arglist, 1, "")
        lltype.free(arglist, flavor='raw')
        return res

    def generate_NEW(self, op):
        sizedescr = op.descr
        assert isinstance(sizedescr, SizeDescr)
        res = self._generate_new(self.cpu._make_const_int(sizedescr.size))
        self.vars[op.result] = res

    def generate_NEW_WITH_VTABLE(self, op):
        sizedescr = self.cpu.class_sizes[op.args[0].getint()]
        res = self._generate_new(self.cpu._make_const_int(sizedescr.size))
        self.vars[op.result] = res
        loc = self._generate_field_gep(op.result, self.cpu.vtable_descr)
        value_ref = self.getintarg(op.args[0])
        llvm_rffi.LLVMBuildStore(self.builder, value_ref, loc, "")

    def _generate_new_array(self, op, ty_array, const_item_size,
                            const_index_array, const_index_length):
        length_ref = self.getintarg(op.args[0])
        if const_item_size == self.cpu.const_one:
            arraysize_ref = length_ref
        else:
            arraysize_ref = llvm_rffi.LLVMBuildMul(self.builder,
                                                   length_ref,
                                                   const_item_size,
                                                   "")
        size_ref = llvm_rffi.LLVMBuildAdd(self.builder,
                                          const_index_array,
                                          arraysize_ref,
                                          "")
        res = self._generate_new(size_ref)
        loc = self._generate_len_gep(res, ty_array, const_index_length)
        llvm_rffi.LLVMBuildStore(self.builder,
                                 length_ref,
                                 loc, "")
        self.vars[op.result] = res

    def generate_NEW_ARRAY(self, op):
        arraydescr = op.descr
        assert isinstance(arraydescr, ArrayDescr)
        self._generate_new_array(op, arraydescr.ty_array_ptr,
                                 self.cpu._make_const_int(arraydescr.itemsize),
                                 self.cpu.const_array_index_array,
                                 self.cpu.const_array_index_length)

    def generate_NEWSTR(self, op):
        self._generate_new_array(op, self.cpu.ty_string_ptr,
                                 self.cpu.const_one,
                                 self.cpu.const_string_index_array,
                                 self.cpu.const_string_index_length)

    def generate_NEWUNICODE(self, op):
        self._generate_new_array(op, self.cpu.ty_unicode_ptr,
                            self.cpu._make_const_int(self.cpu.size_of_unicode),
                                 self.cpu.const_unicode_index_array,
                                 self.cpu.const_unicode_index_length)

    def generate_DEBUG_MERGE_POINT(self, op):
        pass

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
