
""" Register allocation scheme.
"""

from pypy.jit.metainterp.history import (Box, Const, ConstInt, ConstPtr,
                                         ResOperation, ConstAddr, BoxPtr)
from pypy.jit.backend.x86.ri386 import *
from pypy.rpython.lltypesystem import lltype, ll2ctypes, rffi, rstr
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib import rgc
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.x86.jump import remap_stack_layout
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llsupport.descr import BaseFieldDescr, BaseArrayDescr
from pypy.jit.backend.llsupport.descr import BaseCallDescr
from pypy.jit.backend.llsupport.regalloc import StackManager, RegisterManager,\
     TempBox

WORD = 4

class X86RegisterManager(RegisterManager):

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

class X86StackManager(StackManager):

    @staticmethod
    def stack_pos(i):
        res = mem(ebp, get_ebp_ofs(i))
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
        self.jump_target = None

    def _prepare(self, inputargs, operations):
        self.sm = X86StackManager()
        cpu = self.assembler.cpu
        cpu.gc_ll_descr.rewrite_assembler(cpu, operations)
        # compute longevity of variables
        longevity = self._compute_vars_longevity(inputargs, operations)
        self.rm = X86RegisterManager(longevity,
                                     stack_manager = self.sm,
                                     assembler = self.assembler)

    def prepare_loop(self, inputargs, operations):
        self._prepare(inputargs, operations)
        jump = operations[-1]
        loop_consts = self._compute_loop_consts(inputargs, jump)
        self.loop_consts = loop_consts
        return self._process_inputargs(inputargs)

    def prepare_bridge(self, prev_stack_depth, inputargs, arglocs, operations):
        self._prepare(inputargs, operations)
        self.loop_consts = {}
        self._update_bindings(arglocs, inputargs)
        self.sm.stack_depth = prev_stack_depth

    def _process_inputargs(self, inputargs):
        # XXX we can sort out here by longevity if we need something
        # more optimal
        locs = [None] * len(inputargs)
        # Don't use all_regs[0] for passing arguments around a loop.
        # Must be kept in sync with consider_jump().
        # XXX this should probably go to llsupport/regalloc.py
        tmpreg = self.rm.free_regs.pop(0)
        assert tmpreg == X86RegisterManager.all_regs[0]
        for i in range(len(inputargs)):
            arg = inputargs[i]
            assert not isinstance(arg, Const)
            reg = None
            if arg not in self.loop_consts and self.rm.longevity[arg][1] > -1:
                reg = self.rm.try_allocate_reg(arg)
            if reg:
                locs[i] = reg
            else:
                loc = self.sm.loc(arg)
                locs[i] = loc
            # otherwise we have it saved on stack, so no worry
        self.rm.free_regs.insert(0, tmpreg)
        assert tmpreg not in locs
        self.rm.possibly_free_vars(inputargs)
        return locs

    def _compute_loop_consts(self, inputargs, jump):
        if jump.opnum != rop.JUMP or jump.jump_target is not None:
            loop_consts = {}
        else:
            loop_consts = {}
            for i in range(len(inputargs)):
                if inputargs[i] is jump.args[i]:
                    loop_consts[inputargs[i]] = i
        return loop_consts

    def _update_bindings(self, locs, args):
        # XXX this should probably go to llsupport/regalloc.py
        newlocs = []
        for loc in locs:
            if not isinstance(loc, IMM8) and not isinstance(loc, IMM32):
                newlocs.append(loc)
        locs = newlocs
        assert len(locs) == len(args)
        used = {}
        for i in range(len(locs)):
            v = args[i]
            loc = locs[i]
            if isinstance(loc, REG) and self.rm.longevity[v][1] > -1:
                self.rm.reg_bindings[v] = loc
                used[loc] = None
            else:
                self.sm.stack_bindings[v] = loc
        self.rm.free_regs = []
        for reg in X86RegisterManager.all_regs:
            if reg not in used:
                self.rm.free_regs.append(reg)
        self.rm._check_invariants()

    def Perform(self, op, arglocs, result_loc):
        if not we_are_translated():
            self.assembler.dump('%s <- %s(%s)' % (result_loc, op, arglocs))
        self.assembler.regalloc_perform(op, arglocs, result_loc)

    def locs_for_fail(self, guard_op):
        assert len(guard_op.suboperations) == 1
        fail_op = guard_op.suboperations[0]
        assert fail_op.opnum == rop.FAIL
        return [self.loc(v) for v in fail_op.args]

    def perform_with_guard(self, op, guard_op, arglocs, result_loc):
        faillocs = self.locs_for_fail(guard_op)
        self.rm.position += 1
        self.assembler.regalloc_perform_with_guard(op, guard_op, faillocs,
                                                   arglocs, result_loc,
                                                   self.sm.stack_depth)
        self.rm.possibly_free_var(op.result)
        self.rm.possibly_free_vars(guard_op.suboperations[0].args)

    def perform_guard(self, guard_op, arglocs, result_loc):
        faillocs = self.locs_for_fail(guard_op)
        if not we_are_translated():
            if result_loc is not None:
                self.assembler.dump('%s <- %s(%s)' % (result_loc, guard_op,
                                                      arglocs))
            else:
                self.assembler.dump('%s(%s)' % (guard_op, arglocs))
        self.assembler.regalloc_perform_guard(guard_op, faillocs, arglocs,
                                              result_loc,
                                              self.sm.stack_depth)
        self.rm.possibly_free_vars(guard_op.suboperations[0].args)        

    def PerformDiscard(self, op, arglocs):
        if not we_are_translated():
            self.assembler.dump('%s(%s)' % (op, arglocs))
        self.assembler.regalloc_perform_discard(op, arglocs)

    def can_optimize_cmp_op(self, op, i, operations):
        if not (op.is_comparison() or op.opnum == rop.OOISNULL or
                op.opnum == rop.OONONNULL):
            return False
        if (operations[i + 1].opnum != rop.GUARD_TRUE and
            operations[i + 1].opnum != rop.GUARD_FALSE):
            return False
        if operations[i + 1].args[0] is not op.result:
            return False
        if (self.rm.longevity[op.result][1] > i + 1 or
            op.result in operations[i + 1].suboperations[0].args):
            return False
        return True

    def walk_operations(self, operations):
        i = 0
        #self.operations = operations
        while i < len(operations):
            op = operations[i]
            self.rm.position = i
            if op.has_no_side_effect() and op.result not in self.rm.longevity:
                i += 1
                self.rm.possibly_free_vars(op.args)
                continue
            if self.can_optimize_cmp_op(op, i, operations):
                oplist[op.opnum](self, op, operations[i + 1])
                i += 1
            else:
                oplist[op.opnum](self, op, None)
            self.rm.possibly_free_var(op.result)
            self.rm._check_invariants()
            i += 1
        assert not self.rm.reg_bindings

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
                for arg in op.suboperations[0].args:
                    if isinstance(arg, Box):
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
        return self.rm.loc(v)

    def _consider_guard(self, op, ignored):
        loc = self.rm.make_sure_var_in_reg(op.args[0])
        self.perform_guard(op, [loc], None)
        self.rm.possibly_free_var(op.args[0])

    consider_guard_true = _consider_guard
    consider_guard_false = _consider_guard

    def consider_fail(self, op, ignored):
        locs = [self.loc(arg) for arg in op.args]
        self.assembler.generate_failure(self.assembler.mc, op.descr, op.args,
                                        locs, self.exc)
        self.rm.possibly_free_vars(op.args)

    consider_finish = consider_fail # for now

    def consider_guard_no_exception(self, op, ignored):
        self.perform_guard(op, [], None)

    def consider_guard_exception(self, op, ignored):
        loc = self.rm.make_sure_var_in_reg(op.args[0])
        box = TempBox()
        loc1 = self.rm.force_allocate_reg(box, op.args)
        if op.result in self.rm.longevity:
            # this means, is it ever used
            resloc = self.rm.force_allocate_reg(op.result, op.args + [box])
        else:
            resloc = None
        self.perform_guard(op, [loc, loc1], resloc)
        self.rm.possibly_free_vars(op.args)
        self.rm.possibly_free_var(box)

    consider_guard_no_overflow = consider_guard_no_exception
    consider_guard_overflow    = consider_guard_no_exception

    def consider_guard_value(self, op, ignored):
        x = self.rm.make_sure_var_in_reg(op.args[0])
        y = self.loc(op.args[1])
        self.perform_guard(op, [x, y], None)
        self.rm.possibly_free_vars(op.args)

    def consider_guard_class(self, op, ignored):
        assert isinstance(op.args[0], Box)
        x = self.rm.make_sure_var_in_reg(op.args[0])
        y = self.loc(op.args[1])
        self.perform_guard(op, [x, y], None)
        self.rm.possibly_free_vars(op.args)
    
    def _consider_binop_part(self, op, ignored):
        x = op.args[0]
        argloc = self.loc(op.args[1])
        loc = self.rm.force_result_in_reg(op.result, x, op.args)
        self.rm.possibly_free_var(op.args[1])
        return loc, argloc

    def _consider_binop(self, op, ignored):
        loc, argloc = self._consider_binop_part(op, ignored)
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

    def consider_int_neg(self, op, ignored):
        res = self.rm.force_result_in_reg(op.result, op.args[0])
        self.Perform(op, [res], res)

    consider_int_invert = consider_int_neg
    consider_bool_not = consider_int_neg

    def consider_int_lshift(self, op, ignored):
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
        self.rm.possibly_free_vars(op.args + [tmpvar])

    def consider_int_mod(self, op, ignored):
        self._consider_int_div_or_mod(op, edx, eax)
        self.Perform(op, [eax, ecx], edx)

    def consider_int_floordiv(self, op, ignored):
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

    def _call(self, op, arglocs, force_store=[]):
        self.rm.before_call(force_store)
        self.Perform(op, arglocs, eax)
        self.rm.after_call(op.result)

    def consider_call(self, op, ignored):
        calldescr = op.descr
        assert isinstance(calldescr, BaseCallDescr)
        assert len(calldescr.arg_classes) == len(op.args) - 1
        size = calldescr.get_result_size(self.translate_support_code)
        self._call(op, [imm(size)] + [self.loc(arg) for arg in op.args])

    consider_call_pure = consider_call

    def consider_cond_call_gc_wb(self, op, ignored):
        assert op.result is None
        arglocs = [self.loc(arg) for arg in op.args]
        # add eax, ecx and edx as extra "arguments" to ensure they are
        # saved and restored.  Fish in self.rm to know which of these
        # registers really need to be saved (a bit of a hack).  Moreover,
        # we don't save and restore any SSE register because the called
        # function, a GC write barrier, is known not to touch them.
        # See remember_young_pointer() in rpython/memory/gc/generation.py.
        for v, reg in self.rm.reg_bindings.items():
            if ((reg is eax or reg is ecx or reg is edx)
                and self.rm.stays_alive(v)
                and reg not in arglocs[3:]):
                arglocs.append(reg)
        self.PerformDiscard(op, arglocs)
        self.rm.possibly_free_vars(op.args)

    def consider_new(self, op, ignored):
        args = self.assembler.cpu.gc_ll_descr.args_for_new(op.descr)
        arglocs = [imm(x) for x in args]
        return self._call(op, arglocs)

    def consider_new_with_vtable(self, op, ignored):
        classint = op.args[0].getint()
        descrsize = self.assembler.cpu.class_sizes[classint]
        args = self.assembler.cpu.gc_ll_descr.args_for_new(descrsize)
        arglocs = [imm(x) for x in args]
        arglocs.append(self.loc(op.args[0]))
        return self._call(op, arglocs)

    def consider_newstr(self, op, ignored):
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

    def consider_newunicode(self, op, ignored):
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
            other_loc = self.rm.force_allocate_reg(TempBox(), [v])
            self.assembler.load_effective_addr(loc, ofs_items,scale, other_loc)
        else:
            other_loc = imm(ofs_items + (v.getint() << scale))
        self._call(ResOperation(rop.NEW, [v], res_v),
                   [other_loc], [v])
        loc = self.rm.make_sure_var_in_reg(v, [res_v])
        assert self.loc(res_v) == eax
        # now we have to reload length to some reasonable place
        self.rm.possibly_free_var(v)
        self.PerformDiscard(ResOperation(rop.SETFIELD_GC, [], None),
                            [eax, imm(ofs_length), imm(WORD), loc])

    def consider_new_array(self, op, ignored):
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

    def consider_setfield_gc(self, op, ignored):
        ofs_loc, size_loc, ptr = self._unpack_fielddescr(op.descr)
        assert isinstance(size_loc, IMM32)
        if size_loc.value == 1:
            need_lower_byte = True
        else:
            need_lower_byte = False
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        value_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args,
                                              need_lower_byte=need_lower_byte)
        self.rm.possibly_free_vars(op.args)
        self.PerformDiscard(op, [base_loc, ofs_loc, size_loc, value_loc])

    consider_setfield_raw = consider_setfield_gc

    def consider_strsetitem(self, op, ignored):
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args)
        value_loc = self.rm.make_sure_var_in_reg(op.args[2], op.args,
                                                 need_lower_byte=True)
        self.rm.possibly_free_vars(op.args)
        self.PerformDiscard(op, [base_loc, ofs_loc, value_loc])

    consider_unicodesetitem = consider_strsetitem

    def consider_setarrayitem_gc(self, op, ignored):
        scale, ofs, ptr = self._unpack_arraydescr(op.descr)
        base_loc  = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        if scale == 0:
            need_lower_byte = True
        else:
            need_lower_byte = False
        value_loc = self.rm.make_sure_var_in_reg(op.args[2], op.args,
                                              need_lower_byte=need_lower_byte)
        ofs_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args)
        self.rm.possibly_free_vars(op.args)
        self.PerformDiscard(op, [base_loc, ofs_loc, value_loc,
                                 imm(scale), imm(ofs)])

    consider_setarrayitem_raw = consider_setarrayitem_gc

    def consider_getfield_gc(self, op, ignored):
        ofs_loc, size_loc, _ = self._unpack_fielddescr(op.descr)
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, ofs_loc, size_loc], result_loc)

    consider_getfield_gc_pure = consider_getfield_gc

    def consider_getarrayitem_gc(self, op, ignored):
        scale, ofs, _ = self._unpack_arraydescr(op.descr)
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, ofs_loc, imm(scale), imm(ofs)], result_loc)

    consider_getfield_raw = consider_getfield_gc
    consider_getarrayitem_gc_pure = consider_getarrayitem_gc


    def _consider_nullity(self, op, guard_op):
        # doesn't need a register in arg
        if guard_op is not None:
            argloc = self.rm.make_sure_var_in_reg(op.args[0])
            self.rm.possibly_free_var(op.args[0])
            self.perform_with_guard(op, guard_op, [argloc], None)
        else:
            argloc = self.loc(op.args[0])
            self.rm.possibly_free_var(op.args[0])
            resloc = self.rm.force_allocate_reg(op.result, need_lower_byte=True)
            self.Perform(op, [argloc], resloc)

    consider_int_is_true = _consider_nullity
    consider_ooisnull = _consider_nullity
    consider_oononnull = _consider_nullity

    def consider_same_as(self, op, ignored):
        argloc = self.loc(op.args[0])
        self.rm.possibly_free_var(op.args[0])
        resloc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [argloc], resloc)
    consider_cast_ptr_to_int = consider_same_as

    def consider_strlen(self, op, ignored):
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc], result_loc)

    consider_unicodelen = consider_strlen

    def consider_arraylen_gc(self, op, ignored):
        arraydescr = op.descr
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_ofs_length(self.translate_support_code)
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.rm.force_allocate_reg(op.result, [])
        self.Perform(op, [base_loc, imm(ofs)], result_loc)

    def consider_strgetitem(self, op, ignored):
        base_loc = self.rm.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.rm.make_sure_var_in_reg(op.args[1], op.args)
        self.rm.possibly_free_vars(op.args)
        result_loc = self.rm.force_allocate_reg(op.result)
        self.Perform(op, [base_loc, ofs_loc], result_loc)

    consider_unicodegetitem = consider_strgetitem

    def consider_jump(self, op, ignored):
        assembler = self.assembler
        assert self.jump_target is None
        self.jump_target = op.jump_target
        arglocs = assembler.target_arglocs(self.jump_target)
        # compute 'tmploc' to be all_regs[0] by spilling what is there
        box = TempBox()
        tmpreg = X86RegisterManager.all_regs[0]
        tmploc = self.rm.force_allocate_reg(box, [], selected_reg=tmpreg)
        src_locations = [self.rm.loc(arg) for arg in op.args]
        dst_locations = arglocs
        assert tmploc not in dst_locations
        remap_stack_layout(assembler, src_locations, dst_locations, tmploc)
        self.rm.possibly_free_var(box)
        self.rm.possibly_free_vars(op.args)
        assembler.closing_jump(self.jump_target)

    def consider_debug_merge_point(self, op, ignored):
        pass

    def get_mark_gc_roots(self, gcrootmap):
        shape = gcrootmap.get_basic_shape()
        for v, val in self.sm.stack_bindings.items():
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

    def not_implemented_op(self, op, ignored):
        print "[regalloc] Not implemented operation: %s" % op.getopname()
        raise NotImplementedError

oplist = [RegAlloc.not_implemented_op] * rop._LAST

for name, value in RegAlloc.__dict__.iteritems():
    if name.startswith('consider_'):
        name = name[len('consider_'):]
        num = getattr(rop, name.upper())
        oplist[num] = value

def get_ebp_ofs(position):
    # Argument is a stack position (0, 1, 2...).
    # Returns (ebp-16), (ebp-20), (ebp-24)...
    # This depends on the fact that our function prologue contains
    # exactly 4 PUSHes.
    return -WORD * (4 + position)

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
