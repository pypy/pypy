
""" Register allocation scheme.
"""

from pypy.jit.metainterp.history import (Box, Const, ConstInt, ConstPtr,
                                         ResOperation, ConstAddr, BoxPtr,
                                         LoopToken, INT, REF, FLOAT)
from pypy.jit.backend.x86.ri386 import *
from pypy.rpython.lltypesystem import lltype, ll2ctypes, rffi, rstr
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib import rgc
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.x86.jump import remap_frame_layout
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llsupport.descr import BaseFieldDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.descr import BaseCallDescr, BaseSizeDescr
from pypy.jit.backend.llsupport.regalloc import FrameManager, RegisterManager,\
     TempBox

WORD = 4
FRAME_FIXED_SIZE = 5     # ebp + ebx + esi + edi + force_index = 5 words
FORCE_INDEX_OFS = -4*WORD

width_of_type = {
    INT : 1,
    REF : 1,
    FLOAT : 2,
    }

class X86RegisterManager(RegisterManager):

    box_types = [INT, REF]
    all_regs = [eax, ecx, edx, ebx, esi, edi]
    no_lower_byte_regs = [esi, edi]
    save_around_call_regs = [eax, edx, ecx]

    def call_result_location(self, v):
        return eax

    def convert_to_imm(self, c):
        if isinstance(c, ConstInt):
            return imm(c.value)
        elif isinstance(c, ConstPtr):
            if we_are_translated() and c.value and rgc.can_move(c.value):
                print "convert_to_imm: ConstPtr needs special care"
                raise AssertionError
            return imm(rffi.cast(lltype.Signed, c.value))
        elif isinstance(c, ConstAddr):
            return imm(ll2ctypes.cast_adr_to_int(c.value))
        else:
            print "convert_to_imm: got a %s" % c
            raise AssertionError


class FloatConstants(object):
    BASE_CONSTANT_SIZE = 1000

    def __init__(self):
        self.cur_array_free = 0

    def _get_new_array(self):
        n = self.BASE_CONSTANT_SIZE
        self.cur_array = lltype.malloc(rffi.CArray(lltype.Float), n,
                                       flavor='raw')
        self.cur_array_free = n
    _get_new_array._dont_inline_ = True

    def record_float(self, floatval):
        if self.cur_array_free == 0:
            self._get_new_array()
        arr = self.cur_array
        n = self.cur_array_free - 1
        arr[n] = floatval
        self.cur_array_free = n
        return rffi.cast(lltype.Signed, arr) + n * 8


class X86XMMRegisterManager(RegisterManager):

    box_types = [FLOAT]
    all_regs = [xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7]
    # we never need lower byte I hope
    save_around_call_regs = all_regs
    reg_width = 2

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
        adr = self.float_constants.record_float(c.getfloat())
        return heap64(adr)
        
    def after_call(self, v):
        # the result is stored in st0, but we don't have this around,
        # so genop_call will move it to some frame location immediately
        # after the call
        return self.frame_manager.loc(v, 2)

class X86FrameManager(FrameManager):

    @staticmethod
    def frame_pos(i, size):
        if size == 1:
            res = mem(ebp, get_ebp_ofs(i))
        elif size == 2:
            res = mem64(ebp, get_ebp_ofs(i + 1))
        else:
            print "Unimplemented size %d" % i
            raise NotImplementedError("unimplemented size %d" % i)
        res.position = i
        return res

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
        self.rm = X86RegisterManager(longevity,
                                     frame_manager = self.fm,
                                     assembler = self.assembler)
        self.xrm = X86XMMRegisterManager(longevity, frame_manager = self.fm,
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
                loc = self.fm.loc(arg, width_of_type[arg.type])
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
        # is also used on op.args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))
        return nonfloatlocs, floatlocs

    def possibly_free_var(self, var):
        if var.type == FLOAT:
            self.xrm.possibly_free_var(var)
        else:
            self.rm.possibly_free_var(var)

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
        if jump.opnum != rop.JUMP or jump.descr is not looptoken:
            loop_consts = {}
        else:
            loop_consts = {}
            for i in range(len(inputargs)):
                if inputargs[i] is jump.args[i]:
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
                if isinstance(loc, REG):
                    self.xrm.reg_bindings[arg] = loc
                    used[loc] = None
                else:
                    self.fm.frame_bindings[arg] = loc
            else:
                if isinstance(loc, REG):
                    self.rm.reg_bindings[arg] = loc
                    used[loc] = None
                else:
                    self.fm.frame_bindings[arg] = loc
        self.rm.free_regs = []
        for reg in X86RegisterManager.all_regs:
            if reg not in used:
                self.rm.free_regs.append(reg)
        self.xrm.free_regs = []
        for reg in X86XMMRegisterManager.all_regs:
            if reg not in used:
                self.xrm.free_regs.append(reg)
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op.args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))
        self.rm._check_invariants()
        self.xrm._check_invariants()

    def Perform(self, op, arglocs, result_loc):
        if not we_are_translated():
            self.assembler.dump('%s <- %s(%s)' % (result_loc, op, arglocs))
        self.assembler.regalloc_perform(op, arglocs, result_loc)

    def locs_for_fail(self, guard_op):
        return [self.loc(v) for v in guard_op.fail_args]

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
        self.possibly_free_vars(guard_op.fail_args)

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
        self.possibly_free_vars(guard_op.fail_args)        

    def PerformDiscard(self, op, arglocs):
        if not we_are_translated():
            self.assembler.dump('%s(%s)' % (op, arglocs))
        self.assembler.regalloc_perform_discard(op, arglocs)

    def can_merge_with_next_guard(self, op, i, operations):
        if op.opnum == rop.CALL_MAY_FORCE or op.opnum == rop.CALL_ASSEMBLER:
            assert operations[i + 1].opnum == rop.GUARD_NOT_FORCED
            return True
        if not op.is_comparison():
            return False
        if (operations[i + 1].opnum != rop.GUARD_TRUE and
            operations[i + 1].opnum != rop.GUARD_FALSE):
            return False
        if operations[i + 1].args[0] is not op.result:
            return False
        if (self.longevity[op.result][1] > i + 1 or
            op.result in operations[i + 1].fail_args):
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
                self.possibly_free_vars(op.args)
                continue
            if self.can_merge_with_next_guard(op, i, operations):
                oplist_with_guard[op.opnum](self, op, operations[i + 1])
                i += 1
            else:
                oplist[op.opnum](self, op)
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
            for arg in op.args:
                if isinstance(arg, Box):
                    if arg not in start_live:
                        print "Bogus arg in operation %d at %d" % (op.opnum, i)
                        raise AssertionError
                    longevity[arg] = (start_live[arg], i)
            if op.is_guard():
                for arg in op.fail_args:
                    if arg is None: # hole
                        continue
                    assert isinstance(arg, Box)
                    if arg not in start_live:
                        print "Bogus arg in guard %d at %d" % (op.opnum, i)
                        raise AssertionError
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
        loc = self.rm.make_sure_var_in_reg(op.args[0])
        self.perform_guard(op, [loc], None)
        self.rm.possibly_free_var(op.args[0])

    consider_guard_true = _consider_guard
    consider_guard_false = _consider_guard
    consider_guard_nonnull = _consider_guard
    consider_guard_isnull = _consider_guard

    def consider_finish(self, op):
        locs = [self.loc(v) for v in op.args]
        locs_are_ref = [v.type == REF for v in op.args]
        fail_index = self.assembler.cpu.get_fail_descr_number(op.descr)
        self.assembler.generate_failure(fail_index, locs, self.exc,
                                        locs_are_ref)
        self.possibly_free_vars(op.args)

    def consider_guard_no_exception(self, op):
        self.perform_guard(op, [], None)

    def consider_guard_exception(self, op):
        loc = self.rm.make_sure_var_in_reg(op.args[0])
        box = TempBox()
        loc1 = self.rm.force_allocate_reg(box, op.args)
        if op.result in self.longevity:
            # this means, is it ever used
            resloc = self.rm.force_allocate_reg(op.result, op.args + [box])
        else:
            resloc = None
        self.perform_guard(op, [loc, loc1], resloc)
        self.rm.possibly_free_vars(op.args)
        self.rm.possibly_free_var(box)

    consider_guard_no_overflow = consider_guard_no_exception
    consider_guard_overflow    = consider_guard_no_exception

    def consider_guard_value(self, op):
        x = self.make_sure_var_in_reg(op.args[0])
        y = self.loc(op.args[1])
        self.perform_guard(op, [x, y], None)
        self.possibly_free_vars(op.args)

    def consider_guard_class(self, op):
        assert isinstance(op.args[0], Box)
        x = self.rm.make_sure_var_in_reg(op.args[0])
        y = self.loc(op.args[1])
        self.perform_guard(op, [x, y], None)
        self.rm.possibly_free_vars(op.args)

    consider_guard_nonnull_class = consider_guard_class

    def _consider_binop_part(self, op):
        x = op.args[0]
        argloc = self.loc(op.args[1])
        loc = self.rm.force_result_in_reg(op.result, x, op.args)
        self.rm.possibly_free_var(op.args[1])
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

    consider_int_mul_ovf = _consider_binop
    consider_int_sub_ovf = _consider_binop
    consider_int_add_ovf = _consider_binop

    def consider_int_neg(self, op):
        res = self.rm.force_result_in_reg(op.result, op.args[0])
        self.Perform(op, [res], res)

    consider_int_invert = consider_int_neg

    def consider_int_lshift(self, op):
        if isinstance(op.args[1], Const):
            loc2 = self.rm.convert_to_imm(op.args[1])
        else:
            loc2 = self.rm.make_sure_var_in_reg(op.args[1], selected_reg=ecx)
        loc1 = self.rm.force_result_in_reg(op.result, op.args[0], op.args)
        self.Perform(op, [loc1, loc2], loc1)
        self.rm.possibly_free_vars(op.args)

    consider_int_rshift  = consider_int_lshift
    consider_uint_rshift = consider_int_lshift

    def _consider_int_div_or_mod(self, op, resultreg, trashreg):
        l0 = self.rm.make_sure_var_in_reg(op.args[0], selected_reg=eax)
        l1 = self.rm.make_sure_var_in_reg(op.args[1], selected_reg=ecx)
        l2 = self.rm.force_allocate_reg(op.result, selected_reg=resultreg)
        # the register (eax or edx) not holding what we are looking for
        # will be just trash after that operation
        tmpvar = TempBox()
        self.rm.force_allocate_reg(tmpvar, selected_reg=trashreg)
        assert l0 is eax
        assert l1 is ecx
        assert l2 is resultreg
        self.rm.possibly_free_vars(op.args)
        self.rm.possibly_free_var(tmpvar)

    def consider_int_mod(self, op):
        self._consider_int_div_or_mod(op, edx, eax)
        self.Perform(op, [eax, ecx], edx)

    def consider_int_floordiv(self, op):
        self._consider_int_div_or_mod(op, eax, edx)
        self.Perform(op, [eax, ecx], eax)

    def _consider_compop(self, op, guard_op):
        vx = op.args[0]
        vy = op.args[1]
        arglocs = [self.loc(vx), self.loc(vy)]
        if (vx in self.rm.reg_bindings or vy in self.rm.reg_bindings or
            isinstance(vx, Const) or isinstance(vy, Const)):
            pass
        else:
            arglocs[0] = self.rm.make_sure_var_in_reg(vx)
        self.rm.possibly_free_vars(op.args)
        if guard_op is None:
            loc = self.rm.force_allocate_reg(op.result, op.args,
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
    consider_oois = _consider_compop
    consider_ooisnot = _consider_compop

    def _consider_float_op(self, op):
        loc1 = self.xrm.loc(op.args[1])
        loc0 = self.xrm.force_result_in_reg(op.result, op.args[0], op.args)
        self.Perform(op, [loc0, loc1], loc0)
        self.xrm.possibly_free_vars(op.args)

    consider_float_add = _consider_float_op
    consider_float_sub = _consider_float_op
    consider_float_mul = _consider_float_op
    consider_float_truediv = _consider_float_op

    def _consider_float_cmp(self, op, guard_op):
        loc0 = self.xrm.make_sure_var_in_reg(op.args[0], op.args,
                                             imm_fine=False)
        loc1 = self.xrm.loc(op.args[1])
        arglocs = [loc0, loc1]
        self.xrm.possibly_free_vars(op.args)
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
        loc0 = self.xrm.force_result_in_reg(op.result, op.args[0])
        self.Perform(op, [loc0], loc0)
        self.xrm.possibly_free_var(op.args[0])

    def consider_float_abs(self, op):
        loc0 = self.xrm.force_result_in_reg(op.result, op.args[0])
        self.Perform(op, [loc0], loc0)
        self.xrm.possibly_free_var(op.args[0])

    def consider_float_is_true(self, op, guard_op):
        # doesn't need arg to be in a register
        tmpbox0 = TempBox()
        loc0 = self.xrm.force_allocate_reg(tmpbox0)
        loc1 = self.xrm.loc(op.args[0])
        arglocs = [loc0, loc1]
        self.xrm.possibly_free_var(op.args[0])
        self.xrm.possibly_free_var(tmpbox0)
        if guard_op is not None:
            self.perform_with_guard(op, guard_op, arglocs, None)
        else:
            loc2 = self.rm.force_allocate_reg(op.result, need_lower_byte=True)
            self.Perform(op, arglocs, loc2)

    def consider_cast_float_to_int(self, op):
        loc0 = self.xrm.make_sure_var_in_reg(op.args[0], imm_fine=False)
        loc1 = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [loc0], loc1)
        self.xrm.possibly_free_var(op.args[0])

    def consider_cast_int_to_float(self, op):
        loc0 = self.rm.loc(op.args[0])
        loc1 = self.xrm.force_allocate_reg(op.result)
        self.Perform(op, [loc0], loc1)
        self.rm.possibly_free_var(op.args[0])

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
        calldescr = op.descr
        assert isinstance(calldescr, BaseCallDescr)
        assert len(calldescr.arg_classes) == len(op.args) - 1
        size = calldescr.get_result_size(self.translate_support_code)
        self._call(op, [imm(size)] + [self.loc(arg) for arg in op.args],
                   guard_not_forced_op=guard_not_forced_op)

    def consider_call(self, op):
        self._consider_call(op)
    consider_call_pure = consider_call

    def consider_call_may_force(self, op, guard_op):
        assert guard_op is not None
        self._consider_call(op, guard_op)

    def consider_call_assembler(self, op, guard_op):
        descr = op.descr
        portal_calldescr = self.assembler.cpu.portal_calldescr
        size = portal_calldescr.get_result_size(self.translate_support_code)
        vable_index = self.assembler.cpu.index_of_virtualizable
        if vable_index != -1:
            self.rm._sync_var(op.args[vable_index])
            vable = self.fm.loc(op.args[vable_index], 1)
        else:
            vable = imm(0)
        self._call(op, [imm(size), vable] +
                   [self.loc(arg) for arg in op.args],
                   guard_not_forced_op=guard_op)
        
    def consider_cond_call_gc_wb(self, op):
        assert op.result is None
        loc_base = self.rm.make_sure_var_in_reg(op.args[0], op.args,
                                                imm_fine=False)
        loc_newvalue = self.rm.make_sure_var_in_reg(op.args[1], op.args,
                                                    imm_fine=False)
        # ^^^ we also force loc_newvalue in a reg, because it will be needed
        # anyway by the following setfield_gc.  It avoids loading it twice
        # from the memory.
        arglocs = [loc_base, loc_newvalue]
        # add eax, ecx and edx as extra "arguments" to ensure they are
        # saved and restored.  Fish in self.rm to know which of these
        # registers really need to be saved (a bit of a hack).  Moreover,
        # we don't save and restore any SSE register because the called
        # function, a GC write barrier, is known not to touch them.
        # See remember_young_pointer() in rpython/memory/gc/generation.py.
        for v, reg in self.rm.reg_bindings.items():
            if ((reg is eax or reg is ecx or reg is edx)
                and self.rm.stays_alive(v)):
                arglocs.append(reg)
        self.PerformDiscard(op, arglocs)
        self.rm.possibly_free_vars(op.args)

    def _fastpath_malloc(self, op, descr):
        assert isinstance(descr, BaseSizeDescr)
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        tmp0 = TempBox()
        self.rm.force_allocate_reg(op.result, selected_reg=eax)
        self.rm.force_allocate_reg(tmp0, selected_reg=edx)
        # XXX about the next 10 lines: why not just say
        #      force_allocate_reg(tmp1, selected_reg=ecx)?????
        for v, reg in self.rm.reg_bindings.items():
            if reg is ecx:
                to_sync = v
                break
        else:
            to_sync = None
        if to_sync is not None:
            self.rm._sync_var(to_sync)
            del self.rm.reg_bindings[to_sync]
            self.rm.free_regs.append(ecx)
        # we need to do it here, so edx is not in reg_bindings
        self.rm.possibly_free_var(tmp0)
        self.assembler.malloc_cond_fixedsize(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            descr.size, descr.tid,
            gc_ll_descr.get_malloc_fixedsize_slowpath_addr(),
            )

    def consider_new(self, op):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.can_inline_malloc(op.descr):
            self._fastpath_malloc(op, op.descr)
        else:
            args = gc_ll_descr.args_for_new(op.descr)
            arglocs = [imm(x) for x in args]
            return self._call(op, arglocs)

    def consider_new_with_vtable(self, op):
        classint = op.args[0].getint()
        descrsize = self.assembler.cpu.class_sizes[classint]
        if self.assembler.cpu.gc_ll_descr.can_inline_malloc(descrsize):
            self._fastpath_malloc(op, descrsize)
            self.assembler.set_vtable(eax, imm(classint))
            # result of fastpath malloc is in eax
        else:
            args = self.assembler.cpu.gc_ll_descr.args_for_new(descrsize)
            arglocs = [imm(x) for x in args]
            arglocs.append(self.loc(op.args[0]))
            return self._call(op, arglocs)

    def consider_newstr(self, op):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newstr is not None:
            # framework GC
            loc = self.loc(op.args[0])
            return self._call(op, [loc])
        # boehm GC (XXX kill the following code at some point)
        ofs_items, itemsize, ofs = symbolic.get_array_token(rstr.STR, self.translate_support_code)
        assert itemsize == 1
        return self._malloc_varsize(ofs_items, ofs, 0, op.args[0],
                                    op.result)

    def consider_newunicode(self, op):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newunicode is not None:
            # framework GC
            loc = self.loc(op.args[0])
            return self._call(op, [loc])
        # boehm GC (XXX kill the following code at some point)
        ofs_items, itemsize, ofs = symbolic.get_array_token(rstr.UNICODE, self.translate_support_code)
        if itemsize == 4:
            return self._malloc_varsize(ofs_items, ofs, 2, op.args[0],
                                        op.result)
        elif itemsize == 2:
            return self._malloc_varsize(ofs_items, ofs, 1, op.args[0],
                                        op.result)
        else:
            assert False, itemsize

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
        self._call(ResOperation(rop.NEW, [v], res_v),
                   [other_loc], [v])
        loc = self.rm.make_sure_var_in_reg(v, [res_v])
        assert self.loc(res_v) == eax
        # now we have to reload length to some reasonable place
        self.rm.possibly_free_var(v)
        if tempbox is not None:
            self.rm.possibly_free_var(tempbox)
        self.PerformDiscard(ResOperation(rop.SETFIELD_GC, [], None),
                            [eax, imm(ofs_length), imm(WORD), loc])

    def consider_new_array(self, op):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newarray is not None:
            # framework GC
            args = self.assembler.cpu.gc_ll_descr.args_for_new_array(op.descr)
            arglocs = [imm(x) for x in args]
            arglocs.append(self.loc(op.args[0]))
            return self._call(op, arglocs)
        # boehm GC (XXX kill the following code at some point)
        scale_of_field, basesize, _ = self._unpack_arraydescr(op.descr)
        return self._malloc_varsize(basesize, 0, scale_of_field, op.args[0],
                                    op.result)

    def _unpack_arraydescr(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_base_size(self.translate_support_code)
        size = arraydescr.get_item_size(self.translate_support_code)
        ptr = arraydescr.is_array_of_pointers()
        scale = 0
        while (1 << scale) < size:
            scale += 1
        assert (1 << scale) == size
        return scale, ofs, ptr

    def _unpack_fielddescr(self, fielddescr):
        assert isinstance(fielddescr, BaseFieldDescr)
        ofs = fielddescr.offset
        size = fielddescr.get_field_size(self.translate_support_code)
        ptr = fielddescr.is_pointer_field()
        return imm(ofs), imm(size), ptr

    def consider_setfield_gc(self, op):
        ofs_loc, size_loc, ptr = self._unpack_fielddescr(op.descr)
        assert isinstance(size_loc, IMM32)
        if size_loc.value == 1:
            need_lower_byte = True
        else:
            need_lower_byte = False
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        value_loc = self.make_sure_var_in_reg(op.args[1], op.args,
                                              need_lower_byte=need_lower_byte)
        self.possibly_free_vars(op.args)
        self.PerformDiscard(op, [base_loc, ofs_loc, size_loc, value_loc])

    consider_setfield_raw = consider_setfield_gc

    def consider_strsetitem(self, op):
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args)
        value_loc = self.rm.make_sure_var_in_reg(op.args[2], op.args,
                                                 need_lower_byte=True)
        self.rm.possibly_free_vars(op.args)
        self.PerformDiscard(op, [base_loc, ofs_loc, value_loc])

    consider_unicodesetitem = consider_strsetitem

    def consider_setarrayitem_gc(self, op):
        scale, ofs, ptr = self._unpack_arraydescr(op.descr)
        base_loc  = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        if scale == 0:
            need_lower_byte = True
        else:
            need_lower_byte = False
        value_loc = self.make_sure_var_in_reg(op.args[2], op.args,
                                          need_lower_byte=need_lower_byte)
        ofs_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args)
        self.possibly_free_vars(op.args)
        self.PerformDiscard(op, [base_loc, ofs_loc, value_loc,
                                 imm(scale), imm(ofs)])

    consider_setarrayitem_raw = consider_setarrayitem_gc

    def consider_getfield_gc(self, op):
        ofs_loc, size_loc, _ = self._unpack_fielddescr(op.descr)
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, ofs_loc, size_loc], result_loc)

    consider_getfield_raw = consider_getfield_gc
    consider_getfield_raw_pure = consider_getfield_gc
    consider_getfield_gc_pure = consider_getfield_gc

    def consider_getarrayitem_gc(self, op):
        scale, ofs, _ = self._unpack_arraydescr(op.descr)
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, ofs_loc, imm(scale), imm(ofs)], result_loc)

    consider_getarrayitem_gc_pure = consider_getarrayitem_gc

    def consider_int_is_true(self, op, guard_op):
        # doesn't need arg to be in a register
        argloc = self.loc(op.args[0])
        self.rm.possibly_free_var(op.args[0])
        if guard_op is not None:
            self.perform_with_guard(op, guard_op, [argloc], None)
        else:
            resloc = self.rm.force_allocate_reg(op.result, need_lower_byte=True)
            self.Perform(op, [argloc], resloc)

    def consider_bool_not(self, op, guard_op):
        if guard_op is not None:
            # doesn't need arg to be in a register
            argloc = self.loc(op.args[0])
            self.rm.possibly_free_var(op.args[0])
            self.perform_with_guard(op, guard_op, [argloc], None)
        else:
            self.consider_int_neg(op)

    def consider_same_as(self, op):
        argloc = self.loc(op.args[0])
        self.possibly_free_var(op.args[0])
        resloc = self.force_allocate_reg(op.result)
        self.Perform(op, [argloc], resloc)
    consider_cast_ptr_to_int = consider_same_as
    consider_virtual_ref = consider_same_as

    def consider_strlen(self, op):
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc], result_loc)

    consider_unicodelen = consider_strlen

    def consider_arraylen_gc(self, op):
        arraydescr = op.descr
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_ofs_length(self.translate_support_code)
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, imm(ofs)], result_loc)

    def consider_strgetitem(self, op):
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, ofs_loc], result_loc)

    consider_unicodegetitem = consider_strgetitem

    def consider_jump(self, op):
        assembler = self.assembler
        assert self.jump_target_descr is None
        descr = op.descr
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
        src_locations = [self.loc(arg) for arg in op.args if arg.type != FLOAT]
        assert tmploc not in nonfloatlocs
        dst_locations = [loc for loc in nonfloatlocs if loc is not None]
        remap_frame_layout(assembler, src_locations, dst_locations, tmploc)
        # Part about floats
        src_locations = [self.loc(arg) for arg in op.args if arg.type == FLOAT]
        dst_locations = [loc for loc in floatlocs if loc is not None]
        remap_frame_layout(assembler, src_locations, dst_locations, xmmtmp)
        self.rm.possibly_free_var(box)
        self.xrm.possibly_free_var(box1)
        self.possibly_free_vars(op.args)
        assembler.closing_jump(self.jump_target_descr)

    def consider_debug_merge_point(self, op):
        pass

    def consider_virtual_ref_finish(self, op):
        self.possibly_free_vars(op.args)

    def get_mark_gc_roots(self, gcrootmap):
        shape = gcrootmap.get_basic_shape()
        for v, val in self.fm.frame_bindings.items():
            if (isinstance(v, BoxPtr) and self.rm.stays_alive(v)):
                assert isinstance(val, MODRM)
                gcrootmap.add_ebp_offset(shape, get_ebp_ofs(val.position))
        for v, reg in self.rm.reg_bindings.items():
            if (isinstance(v, BoxPtr) and self.rm.stays_alive(v)):
                if reg is ebx:
                    gcrootmap.add_ebx(shape)
                elif reg is esi:
                    gcrootmap.add_esi(shape)
                elif reg is edi:
                    gcrootmap.add_edi(shape)
                else:
                    assert reg is eax     # ok to ignore this one
        return gcrootmap.compress_callshape(shape)

    def consider_force_token(self, op):
        loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [], loc)

    def not_implemented_op(self, op):
        msg = "[regalloc] Not implemented operation: %s" % op.getopname()
        print msg
        raise NotImplementedError(msg)

    def not_implemented_op_with_guard(self, op, guard_op):
        msg = "[regalloc] Not implemented operation with guard: %s" % (
            op.getopname(),)
        print msg
        raise NotImplementedError(msg)

oplist = [RegAlloc.not_implemented_op] * rop._LAST
oplist_with_guard = [RegAlloc.not_implemented_op_with_guard] * rop._LAST

def add_none_argument(fn):
    return lambda self, op: fn(self, op, None)

for name, value in RegAlloc.__dict__.iteritems():
    if name.startswith('consider_'):
        name = name[len('consider_'):]
        num = getattr(rop, name.upper())
        if (ResOperation(num, [], None).is_comparison()
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

def lower_byte(reg):
    # argh, kill, use lowest8bits instead
    if isinstance(reg, MODRM):
        return reg
    if isinstance(reg, IMM32):
        return imm8(reg.value)
    if reg is eax:
        return al
    elif reg is ebx:
        return bl
    elif reg is ecx:
        return cl
    elif reg is edx:
        return dl
    else:
        raise NotImplementedError()
