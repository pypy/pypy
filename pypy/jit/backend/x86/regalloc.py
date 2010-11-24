
""" Register allocation scheme.
"""

import os
from pypy.jit.metainterp.history import (Box, Const, ConstInt, ConstPtr,
                                         ResOperation, BoxPtr,
                                         LoopToken, INT, REF, FLOAT)
from pypy.jit.backend.x86.regloc import *
from pypy.rpython.lltypesystem import lltype, ll2ctypes, rffi, rstr
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import rgc
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.x86.jump import remap_frame_layout
from pypy.jit.codewriter import heaptracker
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llsupport.descr import BaseFieldDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.descr import BaseCallDescr, BaseSizeDescr
from pypy.jit.backend.llsupport.regalloc import FrameManager, RegisterManager,\
     TempBox
from pypy.jit.backend.x86.arch import WORD, FRAME_FIXED_SIZE, IS_X86_32, IS_X86_64

class X86RegisterManager(RegisterManager):

    box_types = [INT, REF]
    all_regs = [eax, ecx, edx, ebx, esi, edi]
    no_lower_byte_regs = [esi, edi]
    save_around_call_regs = [eax, edx, ecx]

    REGLOC_TO_GCROOTMAP_REG_INDEX = {
        ebx: 1,
        esi: 2,
        edi: 3,
    }

    def call_result_location(self, v):
        return eax

    def convert_to_imm(self, c):
        if isinstance(c, ConstInt):
            return imm(c.value)
        elif isinstance(c, ConstPtr):
            if we_are_translated() and c.value and rgc.can_move(c.value):
                not_implemented("convert_to_imm: ConstPtr needs special care")
            return imm(rffi.cast(lltype.Signed, c.value))
        else:
            not_implemented("convert_to_imm: got a %s" % c)

class X86_64_RegisterManager(X86RegisterManager):
    # r11 omitted because it's used as scratch
    all_regs = [eax, ecx, edx, ebx, esi, edi, r8, r9, r10, r12, r13, r14, r15]
    no_lower_byte_regs = []
    save_around_call_regs = [eax, ecx, edx, esi, edi, r8, r9, r10]

    REGLOC_TO_GCROOTMAP_REG_INDEX = {
        ebx: 1,
        r12: 2,
        r13: 3,
        r14: 4,
        r15: 5,
    }

class FloatConstants(object):
    BASE_CONSTANT_SIZE = 1000

    def __init__(self):
        self.cur_array_free = 0
        self.const_id = 0

    def _get_new_array(self):
        n = self.BASE_CONSTANT_SIZE
        # known to leak
        self.cur_array = lltype.malloc(rffi.CArray(lltype.Float), n, # YYY leak
                                       flavor='raw', track_allocation=False)
        self.cur_array_free = n
    _get_new_array._dont_inline_ = True

    def record_float(self, floatval):
        if self.cur_array_free == 0:
            self._get_new_array()
        arr = self.cur_array
        n = self.cur_array_free - 1
        arr[n] = floatval
        self.cur_array_free = n
        self.const_id += 1
        return (self.const_id, rffi.cast(lltype.Signed, arr) + n * 8)


class X86XMMRegisterManager(RegisterManager):

    box_types = [FLOAT]
    all_regs = [xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7]
    # we never need lower byte I hope
    save_around_call_regs = all_regs

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager=frame_manager,
                                 assembler=assembler)
        if assembler is None:
            self.float_constants = FloatConstants()
        else:
            if assembler._float_constants is None:
                assembler._float_constants = FloatConstants()
            self.float_constants = assembler._float_constants

    def convert_to_imm(self, c):
        const_id, adr = self.float_constants.record_float(c.getfloat())
        return ConstFloatLoc(adr, const_id)
        
    def after_call(self, v):
        # the result is stored in st0, but we don't have this around,
        # so genop_call will move it to some frame location immediately
        # after the call
        return self.frame_manager.loc(v)

class X86_64_XMMRegisterManager(X86XMMRegisterManager):
    # xmm15 reserved for scratch use
    all_regs = [xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7, xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14]
    save_around_call_regs = all_regs

    def call_result_location(self, v):
        return xmm0

    def after_call(self, v):
        # We use RegisterManager's implementation, since X86XMMRegisterManager
        # places the result on the stack, which we don't need to do when the
        # calling convention places the result in xmm0
        return RegisterManager.after_call(self, v)

class X86FrameManager(FrameManager):
    @staticmethod
    def frame_pos(i, box_type):
        if IS_X86_32 and box_type == FLOAT:
            return StackLoc(i, get_ebp_ofs(i+1), 2, box_type)
        else:
            return StackLoc(i, get_ebp_ofs(i), 1, box_type)

class RegAlloc(object):
    exc = False

    def __init__(self, assembler, translate_support_code=False):
        assert isinstance(translate_support_code, bool)
        # variables that have place in register
        self.assembler = assembler
        self.translate_support_code = translate_support_code
        # to be read/used by the assembler too
        self.jump_target_descr = None

    def _prepare(self, inputargs, operations):
        self.fm = X86FrameManager()
        self.param_depth = 0
        cpu = self.assembler.cpu
        cpu.gc_ll_descr.rewrite_assembler(cpu, operations)
        # compute longevity of variables
        longevity = self._compute_vars_longevity(inputargs, operations)
        self.longevity = longevity
        # XXX
        if cpu.WORD == 4:
            gpr_reg_mgr_cls = X86RegisterManager
            xmm_reg_mgr_cls = X86XMMRegisterManager
        elif cpu.WORD == 8:
            gpr_reg_mgr_cls = X86_64_RegisterManager
            xmm_reg_mgr_cls = X86_64_XMMRegisterManager
        else:
            raise AssertionError("Word size should be 4 or 8")
            
        self.rm = gpr_reg_mgr_cls(longevity,
                                  frame_manager = self.fm,
                                  assembler = self.assembler)
        self.xrm = xmm_reg_mgr_cls(longevity, frame_manager = self.fm,
                                   assembler = self.assembler)

    def prepare_loop(self, inputargs, operations, looptoken):
        self._prepare(inputargs, operations)
        jump = operations[-1]
        loop_consts = self._compute_loop_consts(inputargs, jump, looptoken)
        self.loop_consts = loop_consts
        return self._process_inputargs(inputargs)

    def prepare_bridge(self, prev_depths, inputargs, arglocs, operations):
        self._prepare(inputargs, operations)
        self.loop_consts = {}
        self._update_bindings(arglocs, inputargs)
        self.fm.frame_depth = prev_depths[0]
        self.param_depth = prev_depths[1]

    def reserve_param(self, n):
        self.param_depth = max(self.param_depth, n)

    def _process_inputargs(self, inputargs):
        # XXX we can sort out here by longevity if we need something
        # more optimal
        floatlocs = [None] * len(inputargs)
        nonfloatlocs = [None] * len(inputargs)
        # Don't use all_regs[0] for passing arguments around a loop.
        # Must be kept in sync with consider_jump().
        # XXX this should probably go to llsupport/regalloc.py
        xmmtmp = self.xrm.free_regs.pop(0)
        tmpreg = self.rm.free_regs.pop(0)
        assert tmpreg == X86RegisterManager.all_regs[0]
        assert xmmtmp == X86XMMRegisterManager.all_regs[0]
        for i in range(len(inputargs)):
            arg = inputargs[i]
            assert not isinstance(arg, Const)
            reg = None
            if arg not in self.loop_consts and self.longevity[arg][1] > -1:
                if arg.type == FLOAT:
                    # xxx is it really a good idea?  at the first CALL they
                    # will all be flushed anyway
                    reg = self.xrm.try_allocate_reg(arg)
                else:
                    reg = self.rm.try_allocate_reg(arg)
            if reg:
                loc = reg
            else:
                loc = self.fm.loc(arg)
            if arg.type == FLOAT:
                floatlocs[i] = loc
            else:
                nonfloatlocs[i] = loc
            # otherwise we have it saved on stack, so no worry
        self.rm.free_regs.insert(0, tmpreg)
        self.xrm.free_regs.insert(0, xmmtmp)
        assert tmpreg not in nonfloatlocs
        assert xmmtmp not in floatlocs
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))
        return nonfloatlocs, floatlocs

    def possibly_free_var(self, var):
        if var.type == FLOAT:
            self.xrm.possibly_free_var(var)
        else:
            self.rm.possibly_free_var(var)

    def possibly_free_vars_for_op(self, op):
        for i in range(op.numargs()):
            var = op.getarg(i)
            if var is not None: # xxx kludgy
                self.possibly_free_var(var)

    def possibly_free_vars(self, vars):
        for var in vars:
            if var is not None: # xxx kludgy
                self.possibly_free_var(var)

    def make_sure_var_in_reg(self, var, forbidden_vars=[],
                             selected_reg=None, imm_fine=True,
                             need_lower_byte=False):
        if var.type == FLOAT:
            # always pass imm_fine=False for now in this case
            return self.xrm.make_sure_var_in_reg(var, forbidden_vars,
                                                 selected_reg, False,
                                                 need_lower_byte)
        else:
            return self.rm.make_sure_var_in_reg(var, forbidden_vars,
                                                selected_reg, imm_fine,
                                                need_lower_byte)

    def force_allocate_reg(self, var, forbidden_vars=[], selected_reg=None,
                           need_lower_byte=False):
        if var.type == FLOAT:
            return self.xrm.force_allocate_reg(var, forbidden_vars,
                                               selected_reg, need_lower_byte)
        else:
            return self.rm.force_allocate_reg(var, forbidden_vars,
                                              selected_reg, need_lower_byte)

    def _compute_loop_consts(self, inputargs, jump, looptoken):
        if jump.getopnum() != rop.JUMP or jump.getdescr() is not looptoken:
            loop_consts = {}
        else:
            loop_consts = {}
            for i in range(len(inputargs)):
                if inputargs[i] is jump.getarg(i):
                    loop_consts[inputargs[i]] = i
        return loop_consts

    def _update_bindings(self, locs, inputargs):
        # XXX this should probably go to llsupport/regalloc.py
        used = {}
        i = 0
        for loc in locs:
            if loc is None: # xxx bit kludgy
                continue
            arg = inputargs[i]
            i += 1
            if arg.type == FLOAT:
                if isinstance(loc, RegLoc):
                    self.xrm.reg_bindings[arg] = loc
                    used[loc] = None
                else:
                    self.fm.frame_bindings[arg] = loc
            else:
                if isinstance(loc, RegLoc):
                    self.rm.reg_bindings[arg] = loc
                    used[loc] = None
                else:
                    self.fm.frame_bindings[arg] = loc
        self.rm.free_regs = []
        for reg in self.rm.all_regs:
            if reg not in used:
                self.rm.free_regs.append(reg)
        self.xrm.free_regs = []
        for reg in self.xrm.all_regs:
            if reg not in used:
                self.xrm.free_regs.append(reg)
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))
        self.rm._check_invariants()
        self.xrm._check_invariants()

    def Perform(self, op, arglocs, result_loc):
        if not we_are_translated():
            self.assembler.dump('%s <- %s(%s)' % (result_loc, op, arglocs))
        self.assembler.regalloc_perform(op, arglocs, result_loc)

    def locs_for_fail(self, guard_op):
        return [self.loc(v) for v in guard_op.getfailargs()]

    def perform_with_guard(self, op, guard_op, arglocs, result_loc):
        faillocs = self.locs_for_fail(guard_op)
        self.rm.position += 1
        self.xrm.position += 1
        current_depths = (self.fm.frame_depth, self.param_depth)
        self.assembler.regalloc_perform_with_guard(op, guard_op, faillocs,
                                                   arglocs, result_loc,
                                                   current_depths)
        if op.result is not None:
            self.possibly_free_var(op.result)
        self.possibly_free_vars(guard_op.getfailargs())

    def perform_guard(self, guard_op, arglocs, result_loc):
        faillocs = self.locs_for_fail(guard_op)
        if not we_are_translated():
            if result_loc is not None:
                self.assembler.dump('%s <- %s(%s)' % (result_loc, guard_op,
                                                      arglocs))
            else:
                self.assembler.dump('%s(%s)' % (guard_op, arglocs))
        current_depths = (self.fm.frame_depth, self.param_depth)                
        self.assembler.regalloc_perform_guard(guard_op, faillocs, arglocs,
                                              result_loc,
                                              current_depths)
        self.possibly_free_vars(guard_op.getfailargs())        

    def PerformDiscard(self, op, arglocs):
        if not we_are_translated():
            self.assembler.dump('%s(%s)' % (op, arglocs))
        self.assembler.regalloc_perform_discard(op, arglocs)

    def can_merge_with_next_guard(self, op, i, operations):
        if op.getopnum() == rop.CALL_MAY_FORCE or op.getopnum() == rop.CALL_ASSEMBLER:
            assert operations[i + 1].getopnum() == rop.GUARD_NOT_FORCED
            return True
        if not op.is_comparison():
            if op.is_ovf():
                if (operations[i + 1].getopnum() != rop.GUARD_NO_OVERFLOW and
                    operations[i + 1].getopnum() != rop.GUARD_OVERFLOW):
                    not_implemented("int_xxx_ovf not followed by "
                                    "guard_(no)_overflow")
                return True
            return False
        if (operations[i + 1].getopnum() != rop.GUARD_TRUE and
            operations[i + 1].getopnum() != rop.GUARD_FALSE):
            return False
        if operations[i + 1].getarg(0) is not op.result:
            return False
        if (self.longevity[op.result][1] > i + 1 or
            op.result in operations[i + 1].getfailargs()):
            return False
        return True

    def walk_operations(self, operations):
        i = 0
        #self.operations = operations
        while i < len(operations):
            op = operations[i]
            self.rm.position = i
            self.xrm.position = i
            if op.has_no_side_effect() and op.result not in self.longevity:
                i += 1
                self.possibly_free_vars_for_op(op)
                continue
            if self.can_merge_with_next_guard(op, i, operations):
                oplist_with_guard[op.getopnum()](self, op, operations[i + 1])
                i += 1
            else:
                oplist[op.getopnum()](self, op)
            if op.result is not None:
                self.possibly_free_var(op.result)
            self.rm._check_invariants()
            self.xrm._check_invariants()
            i += 1
        assert not self.rm.reg_bindings
        assert not self.xrm.reg_bindings

    def _compute_vars_longevity(self, inputargs, operations):
        # compute a dictionary that maps variables to index in
        # operations that is a "last-time-seen"
        longevity = {}
        start_live = {}
        for inputarg in inputargs:
            start_live[inputarg] = 0
        for i in range(len(operations)):
            op = operations[i]
            if op.result is not None:
                start_live[op.result] = i
            for j in range(op.numargs()):
                arg = op.getarg(j)
                if isinstance(arg, Box):
                    if arg not in start_live:
                        not_implemented("Bogus arg in operation %d at %d" %
                                        (op.getopnum(), i))
                    longevity[arg] = (start_live[arg], i)
            if op.is_guard():
                for arg in op.getfailargs():
                    if arg is None: # hole
                        continue
                    assert isinstance(arg, Box)
                    if arg not in start_live:
                        not_implemented("Bogus arg in guard %d at %d" %
                                        (op.getopnum(), i))
                    longevity[arg] = (start_live[arg], i)
        for arg in inputargs:
            if arg not in longevity:
                longevity[arg] = (-1, -1)
        for arg in longevity:
            assert isinstance(arg, Box)
        return longevity

    def loc(self, v):
        if v is None: # xxx kludgy
            return None
        if v.type == FLOAT:
            return self.xrm.loc(v)
        return self.rm.loc(v)

    def _consider_guard(self, op):
        loc = self.rm.make_sure_var_in_reg(op.getarg(0))
        self.perform_guard(op, [loc], None)
        self.rm.possibly_free_var(op.getarg(0))

    consider_guard_true = _consider_guard
    consider_guard_false = _consider_guard
    consider_guard_nonnull = _consider_guard
    consider_guard_isnull = _consider_guard

    def consider_finish(self, op):
        locs = [self.loc(op.getarg(i)) for i in range(op.numargs())]
        locs_are_ref = [op.getarg(i).type == REF for i in range(op.numargs())]
        fail_index = self.assembler.cpu.get_fail_descr_number(op.getdescr())
        self.assembler.generate_failure(fail_index, locs, self.exc,
                                        locs_are_ref)
        self.possibly_free_vars_for_op(op)

    def consider_guard_no_exception(self, op):
        self.perform_guard(op, [], None)

    def consider_guard_exception(self, op):
        loc = self.rm.make_sure_var_in_reg(op.getarg(0))
        box = TempBox()
        args = op.getarglist()
        loc1 = self.rm.force_allocate_reg(box, args)
        if op.result in self.longevity:
            # this means, is it ever used
            resloc = self.rm.force_allocate_reg(op.result, args + [box])
        else:
            resloc = None
        self.perform_guard(op, [loc, loc1], resloc)
        self.rm.possibly_free_vars_for_op(op)
        self.rm.possibly_free_var(box)

    consider_guard_no_overflow = consider_guard_no_exception
    consider_guard_overflow    = consider_guard_no_exception

    def consider_guard_value(self, op):
        x = self.make_sure_var_in_reg(op.getarg(0))
        y = self.loc(op.getarg(1))
        self.perform_guard(op, [x, y], None)
        self.possibly_free_vars_for_op(op)

    def consider_guard_class(self, op):
        assert isinstance(op.getarg(0), Box)
        x = self.rm.make_sure_var_in_reg(op.getarg(0))
        y = self.loc(op.getarg(1))
        self.perform_guard(op, [x, y], None)
        self.rm.possibly_free_vars_for_op(op)

    consider_guard_nonnull_class = consider_guard_class

    def _consider_binop_part(self, op):
        x = op.getarg(0)
        argloc = self.loc(op.getarg(1))
        args = op.getarglist()
        loc = self.rm.force_result_in_reg(op.result, x, args)
        self.rm.possibly_free_var(op.getarg(1))
        return loc, argloc

    def _consider_binop(self, op):
        loc, argloc = self._consider_binop_part(op)
        self.Perform(op, [loc, argloc], loc)

    consider_int_add = _consider_binop
    consider_int_mul = _consider_binop
    consider_int_sub = _consider_binop
    consider_int_and = _consider_binop
    consider_int_or  = _consider_binop
    consider_int_xor = _consider_binop

    def _consider_binop_with_guard(self, op, guard_op):
        loc, argloc = self._consider_binop_part(op)
        self.perform_with_guard(op, guard_op, [loc, argloc], loc)

    consider_int_mul_ovf = _consider_binop_with_guard
    consider_int_sub_ovf = _consider_binop_with_guard
    consider_int_add_ovf = _consider_binop_with_guard

    def consider_int_neg(self, op):
        res = self.rm.force_result_in_reg(op.result, op.getarg(0))
        self.Perform(op, [res], res)

    consider_int_invert = consider_int_neg

    def consider_int_lshift(self, op):
        if isinstance(op.getarg(1), Const):
            loc2 = self.rm.convert_to_imm(op.getarg(1))
        else:
            loc2 = self.rm.make_sure_var_in_reg(op.getarg(1), selected_reg=ecx)
        args = op.getarglist()
        loc1 = self.rm.force_result_in_reg(op.result, op.getarg(0), args)
        self.Perform(op, [loc1, loc2], loc1)
        self.rm.possibly_free_vars_for_op(op)

    consider_int_rshift  = consider_int_lshift
    consider_uint_rshift = consider_int_lshift

    def _consider_int_div_or_mod(self, op, resultreg, trashreg):
        l0 = self.rm.make_sure_var_in_reg(op.getarg(0), selected_reg=eax)
        l1 = self.rm.make_sure_var_in_reg(op.getarg(1), selected_reg=ecx)
        l2 = self.rm.force_allocate_reg(op.result, selected_reg=resultreg)
        # the register (eax or edx) not holding what we are looking for
        # will be just trash after that operation
        tmpvar = TempBox()
        self.rm.force_allocate_reg(tmpvar, selected_reg=trashreg)
        assert l0 is eax
        assert l1 is ecx
        assert l2 is resultreg
        self.rm.possibly_free_vars_for_op(op)
        self.rm.possibly_free_var(tmpvar)

    def consider_int_mod(self, op):
        self._consider_int_div_or_mod(op, edx, eax)
        self.Perform(op, [eax, ecx], edx)

    def consider_int_floordiv(self, op):
        self._consider_int_div_or_mod(op, eax, edx)
        self.Perform(op, [eax, ecx], eax)

    consider_uint_floordiv = consider_int_floordiv

    def _consider_compop(self, op, guard_op):
        vx = op.getarg(0)
        vy = op.getarg(1)
        arglocs = [self.loc(vx), self.loc(vy)]
        if (vx in self.rm.reg_bindings or vy in self.rm.reg_bindings or
            isinstance(vx, Const) or isinstance(vy, Const)):
            pass
        else:
            arglocs[0] = self.rm.make_sure_var_in_reg(vx)
        args = op.getarglist()
        self.rm.possibly_free_vars(args)
        if guard_op is None:
            loc = self.rm.force_allocate_reg(op.result, args,
                                             need_lower_byte=True)
            self.Perform(op, arglocs, loc)
        else:
            self.perform_with_guard(op, guard_op, arglocs, None)

    consider_int_lt = _consider_compop
    consider_int_gt = _consider_compop
    consider_int_ge = _consider_compop
    consider_int_le = _consider_compop
    consider_int_ne = _consider_compop
    consider_int_eq = _consider_compop
    consider_uint_gt = _consider_compop
    consider_uint_lt = _consider_compop
    consider_uint_le = _consider_compop
    consider_uint_ge = _consider_compop
    consider_ptr_eq = _consider_compop
    consider_ptr_ne = _consider_compop

    def _consider_float_op(self, op):
        loc1 = self.xrm.loc(op.getarg(1))
        args = op.getarglist()
        loc0 = self.xrm.force_result_in_reg(op.result, op.getarg(0), args)
        self.Perform(op, [loc0, loc1], loc0)
        self.xrm.possibly_free_vars_for_op(op)

    consider_float_add = _consider_float_op
    consider_float_sub = _consider_float_op
    consider_float_mul = _consider_float_op
    consider_float_truediv = _consider_float_op

    def _consider_float_cmp(self, op, guard_op):
        args = op.getarglist()
        loc0 = self.xrm.make_sure_var_in_reg(op.getarg(0), args,
                                             imm_fine=False)
        loc1 = self.xrm.loc(op.getarg(1))
        arglocs = [loc0, loc1]
        self.xrm.possibly_free_vars_for_op(op)
        if guard_op is None:
            res = self.rm.force_allocate_reg(op.result, need_lower_byte=True)
            self.Perform(op, arglocs, res)
        else:
            self.perform_with_guard(op, guard_op, arglocs, None)

    consider_float_lt = _consider_float_cmp
    consider_float_le = _consider_float_cmp
    consider_float_eq = _consider_float_cmp
    consider_float_ne = _consider_float_cmp
    consider_float_gt = _consider_float_cmp
    consider_float_ge = _consider_float_cmp

    def consider_float_neg(self, op):
        loc0 = self.xrm.force_result_in_reg(op.result, op.getarg(0))
        self.Perform(op, [loc0], loc0)
        self.xrm.possibly_free_var(op.getarg(0))

    def consider_float_abs(self, op):
        loc0 = self.xrm.force_result_in_reg(op.result, op.getarg(0))
        self.Perform(op, [loc0], loc0)
        self.xrm.possibly_free_var(op.getarg(0))

    def consider_cast_float_to_int(self, op):
        loc0 = self.xrm.make_sure_var_in_reg(op.getarg(0), imm_fine=False)
        loc1 = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [loc0], loc1)
        self.xrm.possibly_free_var(op.getarg(0))

    def consider_cast_int_to_float(self, op):
        loc0 = self.rm.loc(op.getarg(0))
        loc1 = self.xrm.force_allocate_reg(op.result)
        self.Perform(op, [loc0], loc1)
        self.rm.possibly_free_var(op.getarg(0))

    def _call(self, op, arglocs, force_store=[], guard_not_forced_op=None):
        save_all_regs = guard_not_forced_op is not None
        self.rm.before_call(force_store, save_all_regs=save_all_regs)
        self.xrm.before_call(force_store, save_all_regs=save_all_regs)
        if op.result is not None:
            if op.result.type == FLOAT:
                resloc = self.xrm.after_call(op.result)
            else:
                resloc = self.rm.after_call(op.result)
        else:
            resloc = None
        if guard_not_forced_op is not None:
            self.perform_with_guard(op, guard_not_forced_op, arglocs, resloc)
        else:
            self.Perform(op, arglocs, resloc)

    def _consider_call(self, op, guard_not_forced_op=None):
        calldescr = op.getdescr()
        assert isinstance(calldescr, BaseCallDescr)
        assert len(calldescr.arg_classes) == op.numargs() - 1
        size = calldescr.get_result_size(self.translate_support_code)
        sign = calldescr.is_result_signed()
        if sign:
            sign_loc = imm1
        else:
            sign_loc = imm0
        self._call(op, [imm(size), sign_loc] +
                       [self.loc(op.getarg(i)) for i in range(op.numargs())],
                   guard_not_forced_op=guard_not_forced_op)

    def consider_call(self, op):
        self._consider_call(op)

    def consider_call_may_force(self, op, guard_op):
        assert guard_op is not None
        self._consider_call(op, guard_op)

    def consider_call_assembler(self, op, guard_op):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        jd = descr.outermost_jitdriver_sd
        assert jd is not None
        size = jd.portal_calldescr.get_result_size(self.translate_support_code)
        vable_index = jd.index_of_virtualizable
        if vable_index >= 0:
            self.rm._sync_var(op.getarg(vable_index))
            vable = self.fm.loc(op.getarg(vable_index))
        else:
            vable = imm0
        self._call(op, [imm(size), vable] +
                   [self.loc(op.getarg(i)) for i in range(op.numargs())],
                   guard_not_forced_op=guard_op)
        
    def consider_cond_call_gc_wb(self, op):
        assert op.result is None
        args = op.getarglist()
        loc_newvalue = self.rm.make_sure_var_in_reg(op.getarg(1), args)
        # ^^^ we force loc_newvalue in a reg (unless it's a Const),
        # because it will be needed anyway by the following setfield_gc.
        # It avoids loading it twice from the memory.
        loc_base = self.rm.make_sure_var_in_reg(op.getarg(0), args,
                                                imm_fine=False)
        arglocs = [loc_base, loc_newvalue]
        # add eax, ecx and edx as extra "arguments" to ensure they are
        # saved and restored.  Fish in self.rm to know which of these
        # registers really need to be saved (a bit of a hack).  Moreover,
        # we don't save and restore any SSE register because the called
        # function, a GC write barrier, is known not to touch them.
        # See remember_young_pointer() in rpython/memory/gc/generation.py.
        for v, reg in self.rm.reg_bindings.items():
            if (reg in self.rm.save_around_call_regs
                and self.rm.stays_alive(v)):
                arglocs.append(reg)
        self.PerformDiscard(op, arglocs)
        self.rm.possibly_free_vars_for_op(op)

    def _fastpath_malloc(self, op, descr):
        assert isinstance(descr, BaseSizeDescr)
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        self.rm.force_allocate_reg(op.result, selected_reg=eax)
        # We need to force-allocate each of save_around_call_regs now.
        # The alternative would be to save and restore them around the
        # actual call to malloc(), in the rare case where we need to do
        # it; however, mark_gc_roots() would need to be adapted to know
        # where the variables end up being saved.  Messy.
        for reg in self.rm.save_around_call_regs:
            if reg is not eax:
                tmp_box = TempBox()
                self.rm.force_allocate_reg(tmp_box, selected_reg=reg)
                self.rm.possibly_free_var(tmp_box)

        self.assembler.malloc_cond_fixedsize(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            descr.size, descr.tid,
            )

    def consider_new(self, op):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.can_inline_malloc(op.getdescr()):
            self._fastpath_malloc(op, op.getdescr())
        else:
            args = gc_ll_descr.args_for_new(op.getdescr())
            arglocs = [imm(x) for x in args]
            return self._call(op, arglocs)

    def consider_new_with_vtable(self, op):
        classint = op.getarg(0).getint()
        descrsize = heaptracker.vtable2descr(self.assembler.cpu, classint)
        if self.assembler.cpu.gc_ll_descr.can_inline_malloc(descrsize):
            self._fastpath_malloc(op, descrsize)
            self.assembler.set_vtable(eax, imm(classint))
            # result of fastpath malloc is in eax
        else:
            args = self.assembler.cpu.gc_ll_descr.args_for_new(descrsize)
            arglocs = [imm(x) for x in args]
            arglocs.append(self.loc(op.getarg(0)))
            return self._call(op, arglocs)

    def consider_newstr(self, op):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newstr is not None:
            # framework GC
            loc = self.loc(op.getarg(0))
            return self._call(op, [loc])
        # boehm GC (XXX kill the following code at some point)
        ofs_items, itemsize, ofs = symbolic.get_array_token(rstr.STR, self.translate_support_code)
        assert itemsize == 1
        return self._malloc_varsize(ofs_items, ofs, 0, op.getarg(0),
                                    op.result)

    def consider_newunicode(self, op):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newunicode is not None:
            # framework GC
            loc = self.loc(op.getarg(0))
            return self._call(op, [loc])
        # boehm GC (XXX kill the following code at some point)
        ofs_items, _, ofs = symbolic.get_array_token(rstr.UNICODE,
                                                   self.translate_support_code)
        scale = self._get_unicode_item_scale()
        return self._malloc_varsize(ofs_items, ofs, scale, op.getarg(0),
                                    op.result)

    def _malloc_varsize(self, ofs_items, ofs_length, scale, v, res_v):
        # XXX kill this function at some point
        if isinstance(v, Box):
            loc = self.rm.make_sure_var_in_reg(v, [v])
            tempbox = TempBox()
            other_loc = self.rm.force_allocate_reg(tempbox, [v])
            self.assembler.load_effective_addr(loc, ofs_items,scale, other_loc)
        else:
            tempbox = None
            other_loc = imm(ofs_items + (v.getint() << scale))
        self._call(ResOperation(rop.NEW, [], res_v),
                   [other_loc], [v])
        loc = self.rm.make_sure_var_in_reg(v, [res_v])
        assert self.loc(res_v) == eax
        # now we have to reload length to some reasonable place
        self.rm.possibly_free_var(v)
        if tempbox is not None:
            self.rm.possibly_free_var(tempbox)
        self.PerformDiscard(ResOperation(rop.SETFIELD_GC, [None, None], None),
                            [eax, imm(ofs_length), imm(WORD), loc])

    def consider_new_array(self, op):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newarray is not None:
            # framework GC
            args = self.assembler.cpu.gc_ll_descr.args_for_new_array(op.getdescr())
            arglocs = [imm(x) for x in args]
            arglocs.append(self.loc(op.getarg(0)))
            return self._call(op, arglocs)
        # boehm GC (XXX kill the following code at some point)
        itemsize, basesize, ofs_length, _, _ = (
            self._unpack_arraydescr(op.getdescr()))
        scale_of_field = _get_scale(itemsize)
        return self._malloc_varsize(basesize, ofs_length, scale_of_field,
                                    op.getarg(0), op.result)

    def _unpack_arraydescr(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs_length = arraydescr.get_ofs_length(self.translate_support_code)
        ofs = arraydescr.get_base_size(self.translate_support_code)
        size = arraydescr.get_item_size(self.translate_support_code)
        ptr = arraydescr.is_array_of_pointers()
        sign = arraydescr.is_item_signed()
        return size, ofs, ofs_length, ptr, sign

    def _unpack_fielddescr(self, fielddescr):
        assert isinstance(fielddescr, BaseFieldDescr)
        ofs = fielddescr.offset
        size = fielddescr.get_field_size(self.translate_support_code)
        ptr = fielddescr.is_pointer_field()
        sign = fielddescr.is_field_signed()
        return imm(ofs), imm(size), ptr, sign

    def consider_setfield_gc(self, op):
        ofs_loc, size_loc, _, _ = self._unpack_fielddescr(op.getdescr())
        assert isinstance(size_loc, ImmedLoc)
        if size_loc.value == 1:
            need_lower_byte = True
        else:
            need_lower_byte = False
        args = op.getarglist()
        base_loc = self.rm.make_sure_var_in_reg(op.getarg(0), args)
        value_loc = self.make_sure_var_in_reg(op.getarg(1), args,
                                              need_lower_byte=need_lower_byte)
        self.possibly_free_vars(args)
        self.PerformDiscard(op, [base_loc, ofs_loc, size_loc, value_loc])

    consider_setfield_raw = consider_setfield_gc

    def consider_strsetitem(self, op):
        args = op.getarglist()
        base_loc = self.rm.make_sure_var_in_reg(op.getarg(0), args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.getarg(1), args)
        value_loc = self.rm.make_sure_var_in_reg(op.getarg(2), args,
                                                 need_lower_byte=True)
        self.rm.possibly_free_vars_for_op(op)
        self.PerformDiscard(op, [base_loc, ofs_loc, value_loc])

    consider_unicodesetitem = consider_strsetitem

    def consider_setarrayitem_gc(self, op):
        itemsize, ofs, _, _, _ = self._unpack_arraydescr(op.getdescr())
        args = op.getarglist()
        base_loc  = self.rm.make_sure_var_in_reg(op.getarg(0), args)
        if itemsize == 1:
            need_lower_byte = True
        else:
            need_lower_byte = False
        value_loc = self.make_sure_var_in_reg(op.getarg(2), args,
                                          need_lower_byte=need_lower_byte)
        ofs_loc = self.rm.make_sure_var_in_reg(op.getarg(1), args)
        self.possibly_free_vars(args)
        self.PerformDiscard(op, [base_loc, ofs_loc, value_loc,
                                 imm(itemsize), imm(ofs)])

    consider_setarrayitem_raw = consider_setarrayitem_gc

    def consider_getfield_gc(self, op):
        ofs_loc, size_loc, _, sign = self._unpack_fielddescr(op.getdescr())
        args = op.getarglist()
        base_loc = self.rm.make_sure_var_in_reg(op.getarg(0), args)
        self.rm.possibly_free_vars(args)
        result_loc = self.force_allocate_reg(op.result)
        if sign:
            sign_loc = imm1
        else:
            sign_loc = imm0
        self.Perform(op, [base_loc, ofs_loc, size_loc, sign_loc], result_loc)

    consider_getfield_raw = consider_getfield_gc
    consider_getfield_raw_pure = consider_getfield_gc
    consider_getfield_gc_pure = consider_getfield_gc

    def consider_getarrayitem_gc(self, op):
        itemsize, ofs, _, _, sign = self._unpack_arraydescr(op.getdescr())
        args = op.getarglist()
        base_loc = self.rm.make_sure_var_in_reg(op.getarg(0), args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.getarg(1), args)
        self.rm.possibly_free_vars_for_op(op)
        result_loc = self.force_allocate_reg(op.result)
        if sign:
            sign_loc = imm1
        else:
            sign_loc = imm0
        self.Perform(op, [base_loc, ofs_loc, imm(itemsize), imm(ofs),
                          sign_loc], result_loc)

    consider_getarrayitem_raw = consider_getarrayitem_gc
    consider_getarrayitem_gc_pure = consider_getarrayitem_gc

    def consider_int_is_true(self, op, guard_op):
        # doesn't need arg to be in a register
        argloc = self.loc(op.getarg(0))
        self.rm.possibly_free_var(op.getarg(0))
        if guard_op is not None:
            self.perform_with_guard(op, guard_op, [argloc], None)
        else:
            resloc = self.rm.force_allocate_reg(op.result, need_lower_byte=True)
            self.Perform(op, [argloc], resloc)

    consider_int_is_zero = consider_int_is_true

    def consider_same_as(self, op):
        argloc = self.loc(op.getarg(0))
        self.possibly_free_var(op.getarg(0))
        resloc = self.force_allocate_reg(op.result)
        self.Perform(op, [argloc], resloc)
    #consider_cast_ptr_to_int = consider_same_as

    def consider_strlen(self, op):
        args = op.getarglist()
        base_loc = self.rm.make_sure_var_in_reg(op.getarg(0), args)
        self.rm.possibly_free_vars_for_op(op)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc], result_loc)

    consider_unicodelen = consider_strlen

    def consider_arraylen_gc(self, op):
        arraydescr = op.getdescr()
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_ofs_length(self.translate_support_code)
        args = op.getarglist()
        base_loc = self.rm.make_sure_var_in_reg(op.getarg(0), args)
        self.rm.possibly_free_vars_for_op(op)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, imm(ofs)], result_loc)

    def consider_strgetitem(self, op):
        args = op.getarglist()
        base_loc = self.rm.make_sure_var_in_reg(op.getarg(0), args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.getarg(1), args)
        self.rm.possibly_free_vars_for_op(op)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, ofs_loc], result_loc)

    consider_unicodegetitem = consider_strgetitem

    def consider_copystrcontent(self, op):
        self._consider_copystrcontent(op, is_unicode=False)

    def consider_copyunicodecontent(self, op):
        self._consider_copystrcontent(op, is_unicode=True)

    def _consider_copystrcontent(self, op, is_unicode):
        # compute the source address
        args = op.getarglist()
        base_loc = self.rm.make_sure_var_in_reg(args[0], args)
        ofs_loc = self.rm.make_sure_var_in_reg(args[2], args)
        assert args[0] is not args[1]    # forbidden case of aliasing
        self.rm.possibly_free_var(args[0])
        if args[3] is not args[2] is not args[4]:  # MESS MESS MESS: don't free
            self.rm.possibly_free_var(args[2])     # it if ==args[3] or args[4]
        srcaddr_box = TempBox()
        forbidden_vars = [args[1], args[3], args[4], srcaddr_box]
        srcaddr_loc = self.rm.force_allocate_reg(srcaddr_box, forbidden_vars)
        self._gen_address_inside_string(base_loc, ofs_loc, srcaddr_loc,
                                        is_unicode=is_unicode)
        # compute the destination address
        base_loc = self.rm.make_sure_var_in_reg(args[1], forbidden_vars)
        ofs_loc = self.rm.make_sure_var_in_reg(args[3], forbidden_vars)
        self.rm.possibly_free_var(args[1])
        if args[3] is not args[4]:     # more of the MESS described above
            self.rm.possibly_free_var(args[3])
        forbidden_vars = [args[4], srcaddr_box]
        dstaddr_box = TempBox()
        dstaddr_loc = self.rm.force_allocate_reg(dstaddr_box, forbidden_vars)
        self._gen_address_inside_string(base_loc, ofs_loc, dstaddr_loc,
                                        is_unicode=is_unicode)
        # compute the length in bytes
        length_box = args[4]
        length_loc = self.loc(length_box)
        if is_unicode:
            self.rm.possibly_free_var(length_box)
            forbidden_vars = [srcaddr_box, dstaddr_box]
            bytes_box = TempBox()
            bytes_loc = self.rm.force_allocate_reg(bytes_box, forbidden_vars)
            scale = self._get_unicode_item_scale()
            if not (isinstance(length_loc, ImmedLoc) or
                    isinstance(length_loc, RegLoc)):
                self.assembler.mov(length_loc, bytes_loc)
                length_loc = bytes_loc
            self.assembler.load_effective_addr(length_loc, 0, scale, bytes_loc)
            length_box = bytes_box
            length_loc = bytes_loc
        # call memcpy()
        self.rm.before_call()
        self.xrm.before_call()
        self.assembler._emit_call(imm(self.assembler.memcpy_addr),
                                  [dstaddr_loc, srcaddr_loc, length_loc])
        self.rm.possibly_free_var(length_box)
        self.rm.possibly_free_var(dstaddr_box)
        self.rm.possibly_free_var(srcaddr_box)

    def _gen_address_inside_string(self, baseloc, ofsloc, resloc, is_unicode):
        cpu = self.assembler.cpu
        if is_unicode:
            ofs_items, _, _ = symbolic.get_array_token(rstr.UNICODE,
                                                  self.translate_support_code)
            scale = self._get_unicode_item_scale()
        else:
            ofs_items, itemsize, _ = symbolic.get_array_token(rstr.STR,
                                                  self.translate_support_code)
            assert itemsize == 1
            scale = 0
        self.assembler.load_effective_addr(ofsloc, ofs_items, scale,
                                           resloc, baseloc)

    def _get_unicode_item_scale(self):
        _, itemsize, _ = symbolic.get_array_token(rstr.UNICODE,
                                                  self.translate_support_code)
        if itemsize == 4:
            return 2
        elif itemsize == 2:
            return 1
        else:
            raise AssertionError("bad unicode item size")

    def consider_jump(self, op):
        assembler = self.assembler
        assert self.jump_target_descr is None
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        self.jump_target_descr = descr
        nonfloatlocs, floatlocs = assembler.target_arglocs(self.jump_target_descr)
        # compute 'tmploc' to be all_regs[0] by spilling what is there
        box = TempBox()
        box1 = TempBox()
        tmpreg = X86RegisterManager.all_regs[0]
        tmploc = self.rm.force_allocate_reg(box, selected_reg=tmpreg)
        xmmtmp = X86XMMRegisterManager.all_regs[0]
        xmmtmploc = self.xrm.force_allocate_reg(box1, selected_reg=xmmtmp)
        # Part about non-floats
        # XXX we don't need a copy, we only just the original list
        src_locations = [self.loc(op.getarg(i)) for i in range(op.numargs()) 
                         if op.getarg(i).type != FLOAT]
        assert tmploc not in nonfloatlocs
        dst_locations = [loc for loc in nonfloatlocs if loc is not None]
        remap_frame_layout(assembler, src_locations, dst_locations, tmploc)
        # Part about floats
        src_locations = [self.loc(op.getarg(i)) for i in range(op.numargs()) 
                         if op.getarg(i).type == FLOAT]
        dst_locations = [loc for loc in floatlocs if loc is not None]
        remap_frame_layout(assembler, src_locations, dst_locations, xmmtmp)
        self.rm.possibly_free_var(box)
        self.xrm.possibly_free_var(box1)
        self.possibly_free_vars_for_op(op)
        assembler.closing_jump(self.jump_target_descr)

    def consider_debug_merge_point(self, op):
        pass

    def consider_jit_debug(self, op):
        pass

    def get_mark_gc_roots(self, gcrootmap):
        shape = gcrootmap.get_basic_shape(IS_X86_64)
        for v, val in self.fm.frame_bindings.items():
            if (isinstance(v, BoxPtr) and self.rm.stays_alive(v)):
                assert isinstance(val, StackLoc)
                gcrootmap.add_ebp_offset(shape, get_ebp_ofs(val.position))
        for v, reg in self.rm.reg_bindings.items():
            if reg is eax:
                continue      # ok to ignore this one
            if (isinstance(v, BoxPtr) and self.rm.stays_alive(v)):
                assert reg in self.rm.REGLOC_TO_GCROOTMAP_REG_INDEX
                gcrootmap.add_callee_save_reg(shape, self.rm.REGLOC_TO_GCROOTMAP_REG_INDEX[reg])
        return gcrootmap.compress_callshape(shape)

    def consider_force_token(self, op):
        loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [], loc)

    def not_implemented_op(self, op):
        not_implemented("not implemented operation: %s" % op.getopname())

    def not_implemented_op_with_guard(self, op, guard_op):
        not_implemented("not implemented operation with guard: %s" % (
            op.getopname(),))

oplist = [RegAlloc.not_implemented_op] * rop._LAST
oplist_with_guard = [RegAlloc.not_implemented_op_with_guard] * rop._LAST

def add_none_argument(fn):
    return lambda self, op: fn(self, op, None)

def is_comparison_or_ovf_op(opnum):
    from pypy.jit.metainterp.resoperation import opclasses, AbstractResOp
    cls = opclasses[opnum]
    # hack hack: in theory they are instance method, but they don't use
    # any instance field, we can use a fake object
    class Fake(cls):
        pass
    op = Fake(None)
    return op.is_comparison() or op.is_ovf()

for name, value in RegAlloc.__dict__.iteritems():
    if name.startswith('consider_'):
        name = name[len('consider_'):]
        num = getattr(rop, name.upper())
        if (is_comparison_or_ovf_op(num)
            or num == rop.CALL_MAY_FORCE or num == rop.CALL_ASSEMBLER):
            oplist_with_guard[num] = value
            oplist[num] = add_none_argument(value)
        else:
            oplist[num] = value

def get_ebp_ofs(position):
    # Argument is a frame position (0, 1, 2...).
    # Returns (ebp-20), (ebp-24), (ebp-28)...
    # i.e. the n'th word beyond the fixed frame size.
    return -WORD * (FRAME_FIXED_SIZE + position)

def _get_scale(size):
    assert size == 1 or size == 2 or size == 4 or size == 8
    if size < 4:
        return size - 1         # 1, 2 => 0, 1
    else:
        return (size >> 2) + 1  # 4, 8 => 2, 3

def not_implemented(msg):
    os.write(2, '[x86/regalloc] %s\n' % msg)
    raise NotImplementedError(msg)
