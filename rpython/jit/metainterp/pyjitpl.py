import sys

import py

from rpython.jit.codewriter import heaptracker
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.codewriter.jitcode import JitCode, SwitchDictDescr
from rpython.jit.metainterp import history, compile, resume, executor, jitexc
from rpython.jit.metainterp.heapcache import HeapCache
from rpython.jit.metainterp.history import (Const, ConstInt, ConstPtr,
    ConstFloat, Box, TargetToken)
from rpython.jit.metainterp.jitprof import EmptyProfiler
from rpython.jit.metainterp.logger import Logger
from rpython.jit.metainterp.optimizeopt.util import args_dict_box
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib import nonconst, rstack
from rpython.rlib.debug import debug_start, debug_stop, debug_print, make_sure_not_resized
from rpython.rlib.jit import Counters
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.unroll import unrolling_iterable
from rpython.rtyper.lltypesystem import lltype, rclass, rffi



# ____________________________________________________________

def arguments(*args):
    def decorate(func):
        func.argtypes = args
        return func
    return decorate

# ____________________________________________________________


class MIFrame(object):
    debug = False

    def __init__(self, metainterp):
        self.metainterp = metainterp
        self.registers_i = [None] * 256
        self.registers_r = [None] * 256
        self.registers_f = [None] * 256

    def setup(self, jitcode, greenkey=None):
        assert isinstance(jitcode, JitCode)
        self.jitcode = jitcode
        self.bytecode = jitcode.code
        # this is not None for frames that are recursive portal calls
        self.greenkey = greenkey
        # copy the constants in place
        self.copy_constants(self.registers_i, jitcode.constants_i, ConstInt)
        self.copy_constants(self.registers_r, jitcode.constants_r, ConstPtr)
        self.copy_constants(self.registers_f, jitcode.constants_f, ConstFloat)
        self._result_argcode = 'v'
        # for resume.py operation
        self.parent_resumedata_snapshot = None
        self.parent_resumedata_frame_info_list = None
        # counter for unrolling inlined loops
        self.unroll_iterations = 1

    @specialize.arg(3)
    def copy_constants(self, registers, constants, ConstClass):
        """Copy jitcode.constants[0] to registers[255],
                jitcode.constants[1] to registers[254],
                jitcode.constants[2] to registers[253], etc."""
        if nonconst.NonConstant(0):             # force the right type
            constants[0] = ConstClass.value     # (useful for small tests)
        i = len(constants) - 1
        while i >= 0:
            j = 255 - i
            assert j >= 0
            registers[j] = ConstClass(constants[i])
            i -= 1

    def cleanup_registers(self):
        # To avoid keeping references alive, this cleans up the registers_r.
        # It does not clear the references set by copy_constants(), but
        # these are all prebuilt constants anyway.
        for i in range(self.jitcode.num_regs_r()):
            self.registers_r[i] = None

    # ------------------------------
    # Decoding of the JitCode

    @specialize.arg(4)
    def prepare_list_of_boxes(self, outvalue, startindex, position, argcode):
        assert argcode in 'IRF'
        code = self.bytecode
        length = ord(code[position])
        position += 1
        for i in range(length):
            index = ord(code[position+i])
            if   argcode == 'I': reg = self.registers_i[index]
            elif argcode == 'R': reg = self.registers_r[index]
            elif argcode == 'F': reg = self.registers_f[index]
            else: raise AssertionError(argcode)
            outvalue[startindex+i] = reg

    def _put_back_list_of_boxes(self, outvalue, startindex, position):
        code = self.bytecode
        length = ord(code[position])
        position += 1
        for i in range(length):
            index = ord(code[position+i])
            box = outvalue[startindex+i]
            if   box.type == history.INT:   self.registers_i[index] = box
            elif box.type == history.REF:   self.registers_r[index] = box
            elif box.type == history.FLOAT: self.registers_f[index] = box
            else: raise AssertionError(box.type)

    def get_current_position_info(self):
        return self.jitcode.get_live_vars_info(self.pc)

    def get_list_of_active_boxes(self, in_a_call):
        if in_a_call:
            # If we are not the topmost frame, self._result_argcode contains
            # the type of the result of the call instruction in the bytecode.
            # We use it to clear the box that will hold the result: this box
            # is not defined yet.
            argcode = self._result_argcode
            index = ord(self.bytecode[self.pc - 1])
            if   argcode == 'i': self.registers_i[index] = history.CONST_FALSE
            elif argcode == 'r': self.registers_r[index] = history.CONST_NULL
            elif argcode == 'f': self.registers_f[index] = history.CONST_FZERO
            self._result_argcode = '?'     # done
        #
        info = self.get_current_position_info()
        start_i = 0
        start_r = start_i + info.get_register_count_i()
        start_f = start_r + info.get_register_count_r()
        total   = start_f + info.get_register_count_f()
        # allocate a list of the correct size
        env = [None] * total
        make_sure_not_resized(env)
        # fill it now
        for i in range(info.get_register_count_i()):
            index = info.get_register_index_i(i)
            env[start_i + i] = self.registers_i[index]
        for i in range(info.get_register_count_r()):
            index = info.get_register_index_r(i)
            env[start_r + i] = self.registers_r[index]
        for i in range(info.get_register_count_f()):
            index = info.get_register_index_f(i)
            env[start_f + i] = self.registers_f[index]
        return env

    def replace_active_box_in_frame(self, oldbox, newbox):
        if isinstance(oldbox, history.BoxInt):
            count = self.jitcode.num_regs_i()
            registers = self.registers_i
        elif isinstance(oldbox, history.BoxPtr):
            count = self.jitcode.num_regs_r()
            registers = self.registers_r
        elif isinstance(oldbox, history.BoxFloat):
            count = self.jitcode.num_regs_f()
            registers = self.registers_f
        else:
            assert 0, oldbox
        for i in range(count):
            if registers[i] is oldbox:
                registers[i] = newbox
        if not we_are_translated():
            for b in registers[count:]:
                assert not oldbox.same_box(b)


    def make_result_of_lastop(self, resultbox):
        got_type = resultbox.type
        # XXX disabled for now, conflicts with str_guard_value
        #if not we_are_translated():
        #    typeof = {'i': history.INT,
        #              'r': history.REF,
        #              'f': history.FLOAT}
        #    assert typeof[self.jitcode._resulttypes[self.pc]] == got_type
        target_index = ord(self.bytecode[self.pc-1])
        if got_type == history.INT:
            self.registers_i[target_index] = resultbox
        elif got_type == history.REF:
            #debug_print(' ->',
            #            llmemory.cast_ptr_to_adr(resultbox.getref_base()))
            self.registers_r[target_index] = resultbox
        elif got_type == history.FLOAT:
            self.registers_f[target_index] = resultbox
        else:
            raise AssertionError("bad result box type")

    # ------------------------------

    for _opimpl in ['int_add', 'int_sub', 'int_mul', 'int_floordiv', 'int_mod',
                    'int_lt', 'int_le', 'int_eq',
                    'int_ne', 'int_gt', 'int_ge',
                    'int_and', 'int_or', 'int_xor',
                    'int_rshift', 'int_lshift', 'uint_rshift',
                    'uint_lt', 'uint_le', 'uint_gt', 'uint_ge',
                    'uint_floordiv',
                    'float_add', 'float_sub', 'float_mul', 'float_truediv',
                    'float_lt', 'float_le', 'float_eq',
                    'float_ne', 'float_gt', 'float_ge',
                    'ptr_eq', 'ptr_ne', 'instance_ptr_eq', 'instance_ptr_ne',
                    ]:
        exec py.code.Source('''
            @arguments("box", "box")
            def opimpl_%s(self, b1, b2):
                return self.execute(rop.%s, b1, b2)
        ''' % (_opimpl, _opimpl.upper())).compile()

    for _opimpl in ['int_add_ovf', 'int_sub_ovf', 'int_mul_ovf']:
        exec py.code.Source('''
            @arguments("box", "box")
            def opimpl_%s(self, b1, b2):
                self.metainterp.clear_exception()
                resbox = self.execute(rop.%s, b1, b2)
                self.make_result_of_lastop(resbox)  # same as execute_varargs()
                if not isinstance(resbox, Const):
                    self.metainterp.handle_possible_overflow_error()
                return resbox
        ''' % (_opimpl, _opimpl.upper())).compile()

    for _opimpl in ['int_is_true', 'int_is_zero', 'int_neg', 'int_invert',
                    'cast_float_to_int', 'cast_int_to_float',
                    'cast_float_to_singlefloat', 'cast_singlefloat_to_float',
                    'float_neg', 'float_abs',
                    'cast_ptr_to_int', 'cast_int_to_ptr',
                    'convert_float_bytes_to_longlong',
                    'convert_longlong_bytes_to_float', 'int_force_ge_zero',
                    ]:
        exec py.code.Source('''
            @arguments("box")
            def opimpl_%s(self, b):
                return self.execute(rop.%s, b)
        ''' % (_opimpl, _opimpl.upper())).compile()

    @arguments("box")
    def opimpl_ptr_nonzero(self, box):
        return self.execute(rop.PTR_NE, box, history.CONST_NULL)

    @arguments("box")
    def opimpl_ptr_iszero(self, box):
        return self.execute(rop.PTR_EQ, box, history.CONST_NULL)

    @arguments("box")
    def opimpl_mark_opaque_ptr(self, box):
        return self.execute(rop.MARK_OPAQUE_PTR, box)

    @arguments("box", "box")
    def opimpl_record_known_class(self, box, clsbox):
        from rpython.rtyper.lltypesystem import llmemory
        if self.metainterp.heapcache.is_class_known(box):
            return
        adr = clsbox.getaddr()
        bounding_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        if bounding_class.subclassrange_max - bounding_class.subclassrange_min == 1:
            # precise class knowledge, this can be used
            self.execute(rop.RECORD_KNOWN_CLASS, box, clsbox)
            self.metainterp.heapcache.class_now_known(box)

    @arguments("box")
    def _opimpl_any_return(self, box):
        self.metainterp.finishframe(box)

    opimpl_int_return = _opimpl_any_return
    opimpl_ref_return = _opimpl_any_return
    opimpl_float_return = _opimpl_any_return

    @arguments()
    def opimpl_void_return(self):
        self.metainterp.finishframe(None)

    @arguments("box")
    def _opimpl_any_copy(self, box):
        return box

    opimpl_int_copy   = _opimpl_any_copy
    opimpl_ref_copy   = _opimpl_any_copy
    opimpl_float_copy = _opimpl_any_copy

    @arguments("box")
    def _opimpl_any_push(self, box):
        self.pushed_box = box

    opimpl_int_push   = _opimpl_any_push
    opimpl_ref_push   = _opimpl_any_push
    opimpl_float_push = _opimpl_any_push

    @arguments()
    def _opimpl_any_pop(self):
        box = self.pushed_box
        self.pushed_box = None
        return box

    opimpl_int_pop   = _opimpl_any_pop
    opimpl_ref_pop   = _opimpl_any_pop
    opimpl_float_pop = _opimpl_any_pop

    @arguments("label")
    def opimpl_catch_exception(self, target):
        """This is a no-op when run normally.  We can check that
        last_exc_value_box is None; it should have been set to None
        by the previous instruction.  If the previous instruction
        raised instead, finishframe_exception() should have been
        called and we would not be there."""
        assert self.metainterp.last_exc_value_box is None

    @arguments("label")
    def opimpl_goto(self, target):
        self.pc = target

    @arguments("box", "label")
    def opimpl_goto_if_not(self, box, target):
        switchcase = box.getint()
        if switchcase:
            opnum = rop.GUARD_TRUE
        else:
            opnum = rop.GUARD_FALSE
        self.metainterp.generate_guard(opnum, box)
        if not switchcase:
            self.pc = target

    @arguments("box", "label")
    def opimpl_goto_if_not_int_is_true(self, box, target):
        condbox = self.execute(rop.INT_IS_TRUE, box)
        self.opimpl_goto_if_not(condbox, target)

    @arguments("box", "label")
    def opimpl_goto_if_not_int_is_zero(self, box, target):
        condbox = self.execute(rop.INT_IS_ZERO, box)
        self.opimpl_goto_if_not(condbox, target)

    for _opimpl in ['int_lt', 'int_le', 'int_eq', 'int_ne', 'int_gt', 'int_ge',
                    'ptr_eq', 'ptr_ne']:
        exec py.code.Source('''
            @arguments("box", "box", "label")
            def opimpl_goto_if_not_%s(self, b1, b2, target):
                condbox = self.execute(rop.%s, b1, b2)
                self.opimpl_goto_if_not(condbox, target)
        ''' % (_opimpl, _opimpl.upper())).compile()


    def _establish_nullity(self, box, orgpc):
        value = box.nonnull()
        if value:
            if not self.metainterp.heapcache.is_class_known(box):
                self.metainterp.generate_guard(rop.GUARD_NONNULL, box,
                                               resumepc=orgpc)
        else:
            if not isinstance(box, Const):
                self.metainterp.generate_guard(rop.GUARD_ISNULL, box,
                                               resumepc=orgpc)
                promoted_box = box.constbox()
                self.metainterp.replace_box(box, promoted_box)
        return value

    @arguments("box", "label", "orgpc")
    def opimpl_goto_if_not_ptr_nonzero(self, box, target, orgpc):
        if not self._establish_nullity(box, orgpc):
            self.pc = target

    @arguments("box", "label", "orgpc")
    def opimpl_goto_if_not_ptr_iszero(self, box, target, orgpc):
        if self._establish_nullity(box, orgpc):
            self.pc = target

    @arguments("box", "box", "box")
    def opimpl_int_between(self, b1, b2, b3):
        b5 = self.execute(rop.INT_SUB, b3, b1)
        if isinstance(b5, ConstInt) and b5.getint() == 1:
            # the common case of int_between(a, b, a+1) turns into just INT_EQ
            return self.execute(rop.INT_EQ, b2, b1)
        else:
            b4 = self.execute(rop.INT_SUB, b2, b1)
            return self.execute(rop.UINT_LT, b4, b5)

    @arguments("box", "descr", "orgpc")
    def opimpl_switch(self, valuebox, switchdict, orgpc):
        box = self.implement_guard_value(valuebox, orgpc)
        search_value = box.getint()
        assert isinstance(switchdict, SwitchDictDescr)
        try:
            self.pc = switchdict.dict[search_value]
        except KeyError:
            pass

    @arguments()
    def opimpl_unreachable(self):
        raise AssertionError("unreachable")

    @arguments("descr")
    def opimpl_new(self, sizedescr):
        resbox = self.execute_with_descr(rop.NEW, sizedescr)
        self.metainterp.heapcache.new(resbox)
        return resbox

    @arguments("descr")
    def opimpl_new_with_vtable(self, sizedescr):
        cpu = self.metainterp.cpu
        cls = heaptracker.descr2vtable(cpu, sizedescr)
        resbox = self.execute(rop.NEW_WITH_VTABLE, ConstInt(cls))
        self.metainterp.heapcache.new(resbox)
        self.metainterp.heapcache.class_now_known(resbox)
        return resbox

    @arguments("box", "descr")
    def opimpl_new_array(self, lengthbox, itemsizedescr):
        resbox = self.execute_with_descr(rop.NEW_ARRAY, itemsizedescr, lengthbox)
        self.metainterp.heapcache.new_array(resbox, lengthbox)
        return resbox

    @specialize.arg(1)
    def _do_getarrayitem_gc_any(self, op, arraybox, indexbox, arraydescr):
        tobox = self.metainterp.heapcache.getarrayitem(
                arraybox, indexbox, arraydescr)
        if tobox:
            # sanity check: see whether the current array value
            # corresponds to what the cache thinks the value is
            resbox = executor.execute(self.metainterp.cpu, self.metainterp, op,
                                      arraydescr, arraybox, indexbox)
            assert resbox.constbox().same_constant(tobox.constbox())
            return tobox
        resbox = self.execute_with_descr(op, arraydescr, arraybox, indexbox)
        self.metainterp.heapcache.getarrayitem_now_known(
                arraybox, indexbox, resbox, arraydescr)
        return resbox

    @arguments("box", "box", "descr")
    def _opimpl_getarrayitem_gc_any(self, arraybox, indexbox, arraydescr):
        return self._do_getarrayitem_gc_any(rop.GETARRAYITEM_GC, arraybox,
                                            indexbox, arraydescr)

    opimpl_getarrayitem_gc_i = _opimpl_getarrayitem_gc_any
    opimpl_getarrayitem_gc_r = _opimpl_getarrayitem_gc_any
    opimpl_getarrayitem_gc_f = _opimpl_getarrayitem_gc_any

    @arguments("box", "box", "descr")
    def _opimpl_getarrayitem_raw_any(self, arraybox, indexbox, arraydescr):
        return self.execute_with_descr(rop.GETARRAYITEM_RAW,
                                       arraydescr, arraybox, indexbox)

    opimpl_getarrayitem_raw_i = _opimpl_getarrayitem_raw_any
    opimpl_getarrayitem_raw_f = _opimpl_getarrayitem_raw_any

    @arguments("box", "box", "descr")
    def _opimpl_getarrayitem_raw_pure_any(self, arraybox, indexbox,
                                          arraydescr):
        return self.execute_with_descr(rop.GETARRAYITEM_RAW_PURE,
                                       arraydescr, arraybox, indexbox)

    opimpl_getarrayitem_raw_i_pure = _opimpl_getarrayitem_raw_pure_any
    opimpl_getarrayitem_raw_f_pure = _opimpl_getarrayitem_raw_pure_any

    @arguments("box", "box", "descr")
    def _opimpl_getarrayitem_gc_pure_any(self, arraybox, indexbox, arraydescr):
        if isinstance(arraybox, ConstPtr) and isinstance(indexbox, ConstInt):
            # if the arguments are directly constants, bypass the heapcache
            # completely
            resbox = executor.execute(self.metainterp.cpu, self.metainterp,
                                      rop.GETARRAYITEM_GC_PURE, arraydescr,
                                      arraybox, indexbox)
            return resbox.constbox()
        return self._do_getarrayitem_gc_any(rop.GETARRAYITEM_GC_PURE, arraybox,
                                            indexbox, arraydescr)

    opimpl_getarrayitem_gc_i_pure = _opimpl_getarrayitem_gc_pure_any
    opimpl_getarrayitem_gc_r_pure = _opimpl_getarrayitem_gc_pure_any
    opimpl_getarrayitem_gc_f_pure = _opimpl_getarrayitem_gc_pure_any

    @arguments("box", "box", "box", "descr")
    def _opimpl_setarrayitem_gc_any(self, arraybox, indexbox, itembox,
                                    arraydescr):
        self.execute_with_descr(rop.SETARRAYITEM_GC, arraydescr, arraybox,
                                indexbox, itembox)
        self.metainterp.heapcache.setarrayitem(
                arraybox, indexbox, itembox, arraydescr)

    opimpl_setarrayitem_gc_i = _opimpl_setarrayitem_gc_any
    opimpl_setarrayitem_gc_r = _opimpl_setarrayitem_gc_any
    opimpl_setarrayitem_gc_f = _opimpl_setarrayitem_gc_any

    @arguments("box", "box", "box", "descr")
    def _opimpl_setarrayitem_raw_any(self, arraybox, indexbox, itembox,
                                     arraydescr):
        self.execute_with_descr(rop.SETARRAYITEM_RAW, arraydescr, arraybox,
                                indexbox, itembox)

    opimpl_setarrayitem_raw_i = _opimpl_setarrayitem_raw_any
    opimpl_setarrayitem_raw_f = _opimpl_setarrayitem_raw_any

    @arguments("box", "descr")
    def opimpl_arraylen_gc(self, arraybox, arraydescr):
        lengthbox = self.metainterp.heapcache.arraylen(arraybox)
        if lengthbox is None:
            lengthbox = self.execute_with_descr(
                    rop.ARRAYLEN_GC, arraydescr, arraybox)
            self.metainterp.heapcache.arraylen_now_known(arraybox, lengthbox)
        return lengthbox

    @arguments("box", "box", "descr", "orgpc")
    def opimpl_check_neg_index(self, arraybox, indexbox, arraydescr, orgpc):
        negbox = self.metainterp.execute_and_record(
            rop.INT_LT, None, indexbox, history.CONST_FALSE)
        negbox = self.implement_guard_value(negbox, orgpc)
        if negbox.getint():
            # the index is < 0; add the array length to it
            lengthbox = self.opimpl_arraylen_gc(arraybox, arraydescr)
            indexbox = self.metainterp.execute_and_record(
                rop.INT_ADD, None, indexbox, lengthbox)
        return indexbox

    @arguments("box", "descr", "descr", "descr", "descr")
    def opimpl_newlist(self, sizebox, structdescr, lengthdescr,
                       itemsdescr, arraydescr):
        sbox = self.opimpl_new(structdescr)
        self._opimpl_setfield_gc_any(sbox, sizebox, lengthdescr)
        abox = self.opimpl_new_array(sizebox, arraydescr)
        self._opimpl_setfield_gc_any(sbox, abox, itemsdescr)
        return sbox

    @arguments("box", "descr", "descr", "descr", "descr")
    def opimpl_newlist_hint(self, sizehintbox, structdescr, lengthdescr,
                            itemsdescr, arraydescr):
        sbox = self.opimpl_new(structdescr)
        self._opimpl_setfield_gc_any(sbox, history.CONST_FALSE, lengthdescr)
        abox = self.opimpl_new_array(sizehintbox, arraydescr)
        self._opimpl_setfield_gc_any(sbox, abox, itemsdescr)
        return sbox

    @arguments("box", "box", "descr", "descr")
    def _opimpl_getlistitem_gc_any(self, listbox, indexbox,
                                   itemsdescr, arraydescr):
        arraybox = self._opimpl_getfield_gc_any(listbox, itemsdescr)
        return self._opimpl_getarrayitem_gc_any(arraybox, indexbox, arraydescr)

    opimpl_getlistitem_gc_i = _opimpl_getlistitem_gc_any
    opimpl_getlistitem_gc_r = _opimpl_getlistitem_gc_any
    opimpl_getlistitem_gc_f = _opimpl_getlistitem_gc_any

    @arguments("box", "box", "box", "descr", "descr")
    def _opimpl_setlistitem_gc_any(self, listbox, indexbox, valuebox,
                                   itemsdescr, arraydescr):
        arraybox = self._opimpl_getfield_gc_any(listbox, itemsdescr)
        self._opimpl_setarrayitem_gc_any(arraybox, indexbox, valuebox,
                                         arraydescr)

    opimpl_setlistitem_gc_i = _opimpl_setlistitem_gc_any
    opimpl_setlistitem_gc_r = _opimpl_setlistitem_gc_any
    opimpl_setlistitem_gc_f = _opimpl_setlistitem_gc_any

    @arguments("box", "box", "descr", "orgpc")
    def opimpl_check_resizable_neg_index(self, listbox, indexbox,
                                         lengthdescr, orgpc):
        negbox = self.metainterp.execute_and_record(
            rop.INT_LT, None, indexbox, history.CONST_FALSE)
        negbox = self.implement_guard_value(negbox, orgpc)
        if negbox.getint():
            # the index is < 0; add the array length to it
            lenbox = self.metainterp.execute_and_record(
                rop.GETFIELD_GC, lengthdescr, listbox)
            indexbox = self.metainterp.execute_and_record(
                rop.INT_ADD, None, indexbox, lenbox)
        return indexbox

    @arguments("box", "descr")
    def _opimpl_getfield_gc_any(self, box, fielddescr):
        return self._opimpl_getfield_gc_any_pureornot(
                rop.GETFIELD_GC, box, fielddescr)
    opimpl_getfield_gc_i = _opimpl_getfield_gc_any
    opimpl_getfield_gc_r = _opimpl_getfield_gc_any
    opimpl_getfield_gc_f = _opimpl_getfield_gc_any

    @arguments("box", "descr")
    def _opimpl_getfield_gc_pure_any(self, box, fielddescr):
        if isinstance(box, ConstPtr):
            # if 'box' is directly a ConstPtr, bypass the heapcache completely
            resbox = executor.execute(self.metainterp.cpu, self.metainterp,
                                      rop.GETFIELD_GC_PURE, fielddescr, box)
            return resbox.constbox()
        return self._opimpl_getfield_gc_any_pureornot(
                rop.GETFIELD_GC_PURE, box, fielddescr)
    opimpl_getfield_gc_i_pure = _opimpl_getfield_gc_pure_any
    opimpl_getfield_gc_r_pure = _opimpl_getfield_gc_pure_any
    opimpl_getfield_gc_f_pure = _opimpl_getfield_gc_pure_any

    @arguments("box", "box", "descr")
    def _opimpl_getinteriorfield_gc_any(self, array, index, descr):
        return self.execute_with_descr(rop.GETINTERIORFIELD_GC, descr,
                                       array, index)
    opimpl_getinteriorfield_gc_i = _opimpl_getinteriorfield_gc_any
    opimpl_getinteriorfield_gc_f = _opimpl_getinteriorfield_gc_any
    opimpl_getinteriorfield_gc_r = _opimpl_getinteriorfield_gc_any

    @specialize.arg(1)
    def _opimpl_getfield_gc_any_pureornot(self, opnum, box, fielddescr):
        tobox = self.metainterp.heapcache.getfield(box, fielddescr)
        if tobox is not None:
            # sanity check: see whether the current struct value
            # corresponds to what the cache thinks the value is
            #resbox = executor.execute(self.metainterp.cpu, self.metainterp,
            #                          rop.GETFIELD_GC, fielddescr, box)
            # XXX the sanity check does not seem to do anything, remove?
            return tobox
        resbox = self.execute_with_descr(opnum, fielddescr, box)
        self.metainterp.heapcache.getfield_now_known(box, fielddescr, resbox)
        return resbox

    @arguments("box", "descr", "orgpc")
    def _opimpl_getfield_gc_greenfield_any(self, box, fielddescr, pc):
        ginfo = self.metainterp.jitdriver_sd.greenfield_info
        if (ginfo is not None and fielddescr in ginfo.green_field_descrs
            and not self._nonstandard_virtualizable(pc, box, fielddescr)):
            # fetch the result, but consider it as a Const box and don't
            # record any operation
            resbox = executor.execute(self.metainterp.cpu, self.metainterp,
                                      rop.GETFIELD_GC_PURE, fielddescr, box)
            return resbox.constbox()
        # fall-back
        return self.execute_with_descr(rop.GETFIELD_GC_PURE, fielddescr, box)
    opimpl_getfield_gc_i_greenfield = _opimpl_getfield_gc_greenfield_any
    opimpl_getfield_gc_r_greenfield = _opimpl_getfield_gc_greenfield_any
    opimpl_getfield_gc_f_greenfield = _opimpl_getfield_gc_greenfield_any

    @arguments("box", "box", "descr")
    def _opimpl_setfield_gc_any(self, box, valuebox, fielddescr):
        tobox = self.metainterp.heapcache.getfield(box, fielddescr)
        if tobox is valuebox:
            return
        if tobox is not None or not self.metainterp.heapcache.is_unescaped(box) or not isinstance(valuebox, Const) or valuebox.nonnull():
            self.execute_with_descr(rop.SETFIELD_GC, fielddescr, box, valuebox)
        self.metainterp.heapcache.setfield(box, valuebox, fielddescr)
    opimpl_setfield_gc_i = _opimpl_setfield_gc_any
    opimpl_setfield_gc_r = _opimpl_setfield_gc_any
    opimpl_setfield_gc_f = _opimpl_setfield_gc_any

    @arguments("box", "box", "box", "descr")
    def _opimpl_setinteriorfield_gc_any(self, array, index, value, descr):
        self.execute_with_descr(rop.SETINTERIORFIELD_GC, descr,
                                array, index, value)
    opimpl_setinteriorfield_gc_i = _opimpl_setinteriorfield_gc_any
    opimpl_setinteriorfield_gc_f = _opimpl_setinteriorfield_gc_any
    opimpl_setinteriorfield_gc_r = _opimpl_setinteriorfield_gc_any


    @arguments("box", "descr")
    def _opimpl_getfield_raw_any(self, box, fielddescr):
        return self.execute_with_descr(rop.GETFIELD_RAW, fielddescr, box)
    opimpl_getfield_raw_i = _opimpl_getfield_raw_any
    opimpl_getfield_raw_f = _opimpl_getfield_raw_any

    @arguments("box", "descr")
    def _opimpl_getfield_raw_pure_any(self, box, fielddescr):
        return self.execute_with_descr(rop.GETFIELD_RAW_PURE, fielddescr, box)
    opimpl_getfield_raw_i_pure = _opimpl_getfield_raw_pure_any
    opimpl_getfield_raw_r_pure = _opimpl_getfield_raw_pure_any
    opimpl_getfield_raw_f_pure = _opimpl_getfield_raw_pure_any

    @arguments("box", "box", "descr")
    def _opimpl_setfield_raw_any(self, box, valuebox, fielddescr):
        self.execute_with_descr(rop.SETFIELD_RAW, fielddescr, box, valuebox)
    opimpl_setfield_raw_i = _opimpl_setfield_raw_any
    opimpl_setfield_raw_f = _opimpl_setfield_raw_any

    @arguments("box", "box", "box", "descr")
    def _opimpl_raw_store(self, addrbox, offsetbox, valuebox, arraydescr):
        self.execute_with_descr(rop.RAW_STORE, arraydescr,
                                addrbox, offsetbox, valuebox)
    opimpl_raw_store_i = _opimpl_raw_store
    opimpl_raw_store_f = _opimpl_raw_store

    @arguments("box", "box", "descr")
    def _opimpl_raw_load(self, addrbox, offsetbox, arraydescr):
        return self.execute_with_descr(rop.RAW_LOAD, arraydescr,
                                       addrbox, offsetbox)
    opimpl_raw_load_i = _opimpl_raw_load
    opimpl_raw_load_f = _opimpl_raw_load

    @arguments("box")
    def opimpl_hint_force_virtualizable(self, box):
        self.metainterp.gen_store_back_in_vable(box)

    @arguments("box", "descr", "descr", "orgpc")
    def opimpl_record_quasiimmut_field(self, box, fielddescr,
                                       mutatefielddescr, orgpc):
        from rpython.jit.metainterp.quasiimmut import QuasiImmutDescr
        cpu = self.metainterp.cpu
        descr = QuasiImmutDescr(cpu, box, fielddescr, mutatefielddescr)
        self.metainterp.history.record(rop.QUASIIMMUT_FIELD, [box],
                                       None, descr=descr)
        self.metainterp.generate_guard(rop.GUARD_NOT_INVALIDATED,
                                       resumepc=orgpc)

    @arguments("box", "descr", "orgpc")
    def opimpl_jit_force_quasi_immutable(self, box, mutatefielddescr, orgpc):
        # During tracing, a 'jit_force_quasi_immutable' usually turns into
        # the operations that check that the content of 'mutate_xxx' is null.
        # If it is actually not null already now, then we abort tracing.
        # The idea is that if we use 'jit_force_quasi_immutable' on a freshly
        # allocated object, then the GETFIELD_GC will know that the answer is
        # null, and the guard will be removed.  So the fact that the field is
        # quasi-immutable will have no effect, and instead it will work as a
        # regular, probably virtual, structure.
        mutatebox = self.execute_with_descr(rop.GETFIELD_GC,
                                            mutatefielddescr, box)
        if mutatebox.nonnull():
            from rpython.jit.metainterp.quasiimmut import do_force_quasi_immutable
            do_force_quasi_immutable(self.metainterp.cpu, box.getref_base(),
                                     mutatefielddescr)
            raise SwitchToBlackhole(Counters.ABORT_FORCE_QUASIIMMUT)
        self.metainterp.generate_guard(rop.GUARD_ISNULL, mutatebox,
                                       resumepc=orgpc)

    def _nonstandard_virtualizable(self, pc, box, fielddescr):
        # returns True if 'box' is actually not the "standard" virtualizable
        # that is stored in metainterp.virtualizable_boxes[-1]
        if self.metainterp.heapcache.is_nonstandard_virtualizable(box):
            return True
        if box is self.metainterp.forced_virtualizable:
            self.metainterp.forced_virtualizable = None
        if (self.metainterp.jitdriver_sd.virtualizable_info is not None or
            self.metainterp.jitdriver_sd.greenfield_info is not None):
            standard_box = self.metainterp.virtualizable_boxes[-1]
            if standard_box is box:
                return False
            vinfo = self.metainterp.jitdriver_sd.virtualizable_info
            if vinfo is fielddescr.get_vinfo():
                eqbox = self.metainterp.execute_and_record(rop.PTR_EQ, None,
                                                           box, standard_box)
                eqbox = self.implement_guard_value(eqbox, pc)
                isstandard = eqbox.getint()
                if isstandard:
                    self.metainterp.replace_box(box, standard_box)
                    return False
        if not self.metainterp.heapcache.is_unescaped(box):
            self.emit_force_virtualizable(fielddescr, box)
        self.metainterp.heapcache.nonstandard_virtualizables_now_known(box)
        return True

    def emit_force_virtualizable(self, fielddescr, box):
        vinfo = fielddescr.get_vinfo()
        token_descr = vinfo.vable_token_descr
        mi = self.metainterp
        tokenbox = mi.execute_and_record(rop.GETFIELD_GC, token_descr, box)
        condbox = mi.execute_and_record(rop.PTR_NE, None, tokenbox,
                                       history.CONST_NULL)
        funcbox = ConstInt(rffi.cast(lltype.Signed, vinfo.clear_vable_ptr))
        calldescr = vinfo.clear_vable_descr
        self.execute_varargs(rop.COND_CALL, [condbox, funcbox, box],
                             calldescr, False, False)

    def _get_virtualizable_field_index(self, fielddescr):
        # Get the index of a fielddescr.  Must only be called for
        # the "standard" virtualizable.
        vinfo = self.metainterp.jitdriver_sd.virtualizable_info
        return vinfo.static_field_by_descrs[fielddescr]

    @arguments("box", "descr", "orgpc")
    def _opimpl_getfield_vable(self, box, fielddescr, pc):
        if self._nonstandard_virtualizable(pc, box, fielddescr):
            return self._opimpl_getfield_gc_any(box, fielddescr)
        self.metainterp.check_synchronized_virtualizable()
        index = self._get_virtualizable_field_index(fielddescr)
        return self.metainterp.virtualizable_boxes[index]

    opimpl_getfield_vable_i = _opimpl_getfield_vable
    opimpl_getfield_vable_r = _opimpl_getfield_vable
    opimpl_getfield_vable_f = _opimpl_getfield_vable

    @arguments("box", "box", "descr", "orgpc")
    def _opimpl_setfield_vable(self, box, valuebox, fielddescr, pc):
        if self._nonstandard_virtualizable(pc, box, fielddescr):
            return self._opimpl_setfield_gc_any(box, valuebox, fielddescr)
        index = self._get_virtualizable_field_index(fielddescr)
        self.metainterp.virtualizable_boxes[index] = valuebox
        self.metainterp.synchronize_virtualizable()
        # XXX only the index'th field needs to be synchronized, really

    opimpl_setfield_vable_i = _opimpl_setfield_vable
    opimpl_setfield_vable_r = _opimpl_setfield_vable
    opimpl_setfield_vable_f = _opimpl_setfield_vable

    def _get_arrayitem_vable_index(self, pc, arrayfielddescr, indexbox):
        # Get the index of an array item: the index'th of the array
        # described by arrayfielddescr.  Must only be called for
        # the "standard" virtualizable.
        indexbox = self.implement_guard_value(indexbox, pc)
        vinfo = self.metainterp.jitdriver_sd.virtualizable_info
        virtualizable_box = self.metainterp.virtualizable_boxes[-1]
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
        arrayindex = vinfo.array_field_by_descrs[arrayfielddescr]
        index = indexbox.getint()
        # Support for negative index: disabled
        # (see codewriter/jtransform.py, _check_no_vable_array).
        #if index < 0:
        #    index += vinfo.get_array_length(virtualizable, arrayindex)
        assert 0 <= index < vinfo.get_array_length(virtualizable, arrayindex)
        return vinfo.get_index_in_array(virtualizable, arrayindex, index)

    @arguments("box", "box", "descr", "descr", "orgpc")
    def _opimpl_getarrayitem_vable(self, box, indexbox, fdescr, adescr, pc):
        if self._nonstandard_virtualizable(pc, box, fdescr):
            arraybox = self._opimpl_getfield_gc_any(box, fdescr)
            return self._opimpl_getarrayitem_gc_any(arraybox, indexbox, adescr)
        self.metainterp.check_synchronized_virtualizable()
        index = self._get_arrayitem_vable_index(pc, fdescr, indexbox)
        return self.metainterp.virtualizable_boxes[index]

    opimpl_getarrayitem_vable_i = _opimpl_getarrayitem_vable
    opimpl_getarrayitem_vable_r = _opimpl_getarrayitem_vable
    opimpl_getarrayitem_vable_f = _opimpl_getarrayitem_vable

    @arguments("box", "box", "box", "descr", "descr", "orgpc")
    def _opimpl_setarrayitem_vable(self, box, indexbox, valuebox,
                                   fdescr, adescr, pc):
        if self._nonstandard_virtualizable(pc, box, fdescr):
            arraybox = self._opimpl_getfield_gc_any(box, fdescr)
            self._opimpl_setarrayitem_gc_any(arraybox, indexbox, valuebox,
                                             adescr)
            return
        index = self._get_arrayitem_vable_index(pc, fdescr, indexbox)
        self.metainterp.virtualizable_boxes[index] = valuebox
        self.metainterp.synchronize_virtualizable()
        # XXX only the index'th field needs to be synchronized, really

    opimpl_setarrayitem_vable_i = _opimpl_setarrayitem_vable
    opimpl_setarrayitem_vable_r = _opimpl_setarrayitem_vable
    opimpl_setarrayitem_vable_f = _opimpl_setarrayitem_vable

    @arguments("box", "descr", "descr", "orgpc")
    def opimpl_arraylen_vable(self, box, fdescr, adescr, pc):
        if self._nonstandard_virtualizable(pc, box, fdescr):
            arraybox = self._opimpl_getfield_gc_any(box, fdescr)
            return self.opimpl_arraylen_gc(arraybox, adescr)
        vinfo = self.metainterp.jitdriver_sd.virtualizable_info
        virtualizable_box = self.metainterp.virtualizable_boxes[-1]
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
        arrayindex = vinfo.array_field_by_descrs[fdescr]
        result = vinfo.get_array_length(virtualizable, arrayindex)
        return ConstInt(result)

    @arguments("jitcode", "boxes")
    def _opimpl_inline_call1(self, jitcode, argboxes):
        return self.metainterp.perform_call(jitcode, argboxes)
    @arguments("jitcode", "boxes2")
    def _opimpl_inline_call2(self, jitcode, argboxes):
        return self.metainterp.perform_call(jitcode, argboxes)
    @arguments("jitcode", "boxes3")
    def _opimpl_inline_call3(self, jitcode, argboxes):
        return self.metainterp.perform_call(jitcode, argboxes)

    opimpl_inline_call_r_i = _opimpl_inline_call1
    opimpl_inline_call_r_r = _opimpl_inline_call1
    opimpl_inline_call_r_v = _opimpl_inline_call1
    opimpl_inline_call_ir_i = _opimpl_inline_call2
    opimpl_inline_call_ir_r = _opimpl_inline_call2
    opimpl_inline_call_ir_v = _opimpl_inline_call2
    opimpl_inline_call_irf_i = _opimpl_inline_call3
    opimpl_inline_call_irf_r = _opimpl_inline_call3
    opimpl_inline_call_irf_f = _opimpl_inline_call3
    opimpl_inline_call_irf_v = _opimpl_inline_call3

    @arguments("box", "boxes", "descr", "orgpc")
    def _opimpl_residual_call1(self, funcbox, argboxes, calldescr, pc):
        return self.do_residual_or_indirect_call(funcbox, argboxes, calldescr, pc)

    @arguments("box", "boxes2", "descr", "orgpc")
    def _opimpl_residual_call2(self, funcbox, argboxes, calldescr, pc):
        return self.do_residual_or_indirect_call(funcbox, argboxes, calldescr, pc)

    @arguments("box", "boxes3", "descr", "orgpc")
    def _opimpl_residual_call3(self, funcbox, argboxes, calldescr, pc):
        return self.do_residual_or_indirect_call(funcbox, argboxes, calldescr, pc)

    opimpl_residual_call_r_i = _opimpl_residual_call1
    opimpl_residual_call_r_r = _opimpl_residual_call1
    opimpl_residual_call_r_v = _opimpl_residual_call1
    opimpl_residual_call_ir_i = _opimpl_residual_call2
    opimpl_residual_call_ir_r = _opimpl_residual_call2
    opimpl_residual_call_ir_v = _opimpl_residual_call2
    opimpl_residual_call_irf_i = _opimpl_residual_call3
    opimpl_residual_call_irf_r = _opimpl_residual_call3
    opimpl_residual_call_irf_f = _opimpl_residual_call3
    opimpl_residual_call_irf_v = _opimpl_residual_call3

    @arguments("box", "box", "boxes", "descr", "orgpc")
    def opimpl_conditional_call_i_v(self, condbox, funcbox, argboxes, calldescr,
                                    pc):
        self.do_conditional_call(condbox, funcbox, argboxes, calldescr, pc)

    @arguments("box", "box", "boxes2", "descr", "orgpc")
    def opimpl_conditional_call_ir_v(self, condbox, funcbox, argboxes,
                                     calldescr, pc):
        self.do_conditional_call(condbox, funcbox, argboxes, calldescr, pc)

    @arguments("box", "box", "boxes3", "descr", "orgpc")
    def opimpl_conditional_call_irf_v(self, condbox, funcbox, argboxes,
                                      calldescr, pc):
        self.do_conditional_call(condbox, funcbox, argboxes, calldescr, pc)

    @arguments("int", "boxes3", "boxes3", "orgpc")
    def _opimpl_recursive_call(self, jdindex, greenboxes, redboxes, pc):
        targetjitdriver_sd = self.metainterp.staticdata.jitdrivers_sd[jdindex]
        allboxes = greenboxes + redboxes
        warmrunnerstate = targetjitdriver_sd.warmstate
        assembler_call = False
        if warmrunnerstate.inlining:
            if warmrunnerstate.can_inline_callable(greenboxes):
                portal_code = targetjitdriver_sd.mainjitcode
                return self.metainterp.perform_call(portal_code, allboxes,
                                                    greenkey=greenboxes)
            assembler_call = True
            # verify that we have all green args, needed to make sure
            # that assembler that we call is still correct
            self.verify_green_args(targetjitdriver_sd, greenboxes)
        #
        return self.do_recursive_call(targetjitdriver_sd, allboxes, pc,
                                      assembler_call)

    def do_recursive_call(self, targetjitdriver_sd, allboxes, pc,
                          assembler_call=False):
        portal_code = targetjitdriver_sd.mainjitcode
        k = targetjitdriver_sd.portal_runner_adr
        funcbox = ConstInt(heaptracker.adr2int(k))
        return self.do_residual_call(funcbox, allboxes, portal_code.calldescr, pc,
                                     assembler_call=assembler_call,
                                     assembler_call_jd=targetjitdriver_sd)

    opimpl_recursive_call_i = _opimpl_recursive_call
    opimpl_recursive_call_r = _opimpl_recursive_call
    opimpl_recursive_call_f = _opimpl_recursive_call
    opimpl_recursive_call_v = _opimpl_recursive_call

    @arguments("box")
    def opimpl_strlen(self, strbox):
        return self.execute(rop.STRLEN, strbox)

    @arguments("box")
    def opimpl_unicodelen(self, unicodebox):
        return self.execute(rop.UNICODELEN, unicodebox)

    @arguments("box", "box")
    def opimpl_strgetitem(self, strbox, indexbox):
        return self.execute(rop.STRGETITEM, strbox, indexbox)

    @arguments("box", "box")
    def opimpl_unicodegetitem(self, unicodebox, indexbox):
        return self.execute(rop.UNICODEGETITEM, unicodebox, indexbox)

    @arguments("box", "box", "box")
    def opimpl_strsetitem(self, strbox, indexbox, newcharbox):
        return self.execute(rop.STRSETITEM, strbox, indexbox, newcharbox)

    @arguments("box", "box", "box")
    def opimpl_unicodesetitem(self, unicodebox, indexbox, newcharbox):
        self.execute(rop.UNICODESETITEM, unicodebox, indexbox, newcharbox)

    @arguments("box")
    def opimpl_newstr(self, lengthbox):
        return self.execute(rop.NEWSTR, lengthbox)

    @arguments("box")
    def opimpl_newunicode(self, lengthbox):
        return self.execute(rop.NEWUNICODE, lengthbox)

    @arguments("box", "box", "box", "box", "box")
    def opimpl_copystrcontent(self, srcbox, dstbox, srcstartbox, dststartbox, lengthbox):
        return self.execute(rop.COPYSTRCONTENT, srcbox, dstbox, srcstartbox, dststartbox, lengthbox)

    @arguments("box", "box", "box", "box", "box")
    def opimpl_copyunicodecontent(self, srcbox, dstbox, srcstartbox, dststartbox, lengthbox):
        return self.execute(rop.COPYUNICODECONTENT, srcbox, dstbox, srcstartbox, dststartbox, lengthbox)

    @arguments("box", "orgpc")
    def _opimpl_guard_value(self, box, orgpc):
        self.implement_guard_value(box, orgpc)

    @arguments("box", "box", "descr", "orgpc")
    def opimpl_str_guard_value(self, box, funcbox, descr, orgpc):
        if isinstance(box, Const):
            return box     # no promotion needed, already a Const
        else:
            constbox = box.constbox()
            resbox = self.do_residual_call(funcbox, [box, constbox], descr, orgpc)
            promoted_box = resbox.constbox()
            # This is GUARD_VALUE because GUARD_TRUE assumes the existance
            # of a label when computing resumepc
            self.metainterp.generate_guard(rop.GUARD_VALUE, resbox,
                                           [promoted_box],
                                           resumepc=orgpc)
            self.metainterp.replace_box(box, constbox)
            return constbox

    opimpl_int_guard_value = _opimpl_guard_value
    opimpl_ref_guard_value = _opimpl_guard_value
    opimpl_float_guard_value = _opimpl_guard_value

    @arguments("box", "orgpc")
    def opimpl_guard_class(self, box, orgpc):
        clsbox = self.cls_of_box(box)
        if not self.metainterp.heapcache.is_class_known(box):
            self.metainterp.generate_guard(rop.GUARD_CLASS, box, [clsbox],
                                           resumepc=orgpc)
            self.metainterp.heapcache.class_now_known(box)
        return clsbox

    @arguments("int", "orgpc")
    def opimpl_loop_header(self, jdindex, orgpc):
        self.metainterp.seen_loop_header_for_jdindex = jdindex

    def verify_green_args(self, jitdriver_sd, varargs):
        num_green_args = jitdriver_sd.num_green_args
        assert len(varargs) == num_green_args
        for i in range(num_green_args):
            assert isinstance(varargs[i], Const)

    @arguments("int", "boxes3", "jitcode_position", "boxes3", "orgpc")
    def opimpl_jit_merge_point(self, jdindex, greenboxes,
                               jcposition, redboxes, orgpc):
        any_operation = len(self.metainterp.history.operations) > 0
        jitdriver_sd = self.metainterp.staticdata.jitdrivers_sd[jdindex]
        self.verify_green_args(jitdriver_sd, greenboxes)
        self.debug_merge_point(jitdriver_sd, jdindex,
                               self.metainterp.portal_call_depth,
                               self.metainterp.call_ids[-1],
                               greenboxes)

        if self.metainterp.seen_loop_header_for_jdindex < 0:
            if not any_operation:
                return
            if self.metainterp.portal_call_depth or not self.metainterp.get_procedure_token(greenboxes, True):
                if not jitdriver_sd.no_loop_header:
                    return
            # automatically add a loop_header if there is none
            self.metainterp.seen_loop_header_for_jdindex = jdindex
        #
        assert self.metainterp.seen_loop_header_for_jdindex == jdindex, (
            "found a loop_header for a JitDriver that does not match "
            "the following jit_merge_point's")
        self.metainterp.seen_loop_header_for_jdindex = -1

        #
        if not self.metainterp.portal_call_depth:
            assert jitdriver_sd is self.metainterp.jitdriver_sd
            # Set self.pc to point to jit_merge_point instead of just after:
            # if reached_loop_header() raises SwitchToBlackhole, then the
            # pc is still at the jit_merge_point, which is a point that is
            # much less expensive to blackhole out of.
            saved_pc = self.pc
            self.pc = orgpc
            resumedescr = compile.ResumeAtPositionDescr()
            self.metainterp.capture_resumedata(resumedescr, orgpc)

            self.metainterp.reached_loop_header(greenboxes, redboxes, resumedescr)
            self.pc = saved_pc
            # no exception, which means that the jit_merge_point did not
            # close the loop.  We have to put the possibly-modified list
            # 'redboxes' back into the registers where it comes from.
            put_back_list_of_boxes3(self, jcposition, redboxes)
        else:
            if jitdriver_sd.warmstate.should_unroll_one_iteration(greenboxes):
                if self.unroll_iterations > 0:
                    self.unroll_iterations -= 1
                    return
            # warning! careful here.  We have to return from the current
            # frame containing the jit_merge_point, and then use
            # do_recursive_call() to follow the recursive call.  This is
            # needed because do_recursive_call() will write its result
            # with make_result_of_lastop(), so the lastop must be right:
            # it must be the call to 'self', and not the jit_merge_point
            # itself, which has no result at all.
            assert len(self.metainterp.framestack) >= 2
            try:
                self.metainterp.finishframe(None)
            except ChangeFrame:
                pass
            frame = self.metainterp.framestack[-1]
            frame.do_recursive_call(jitdriver_sd, greenboxes + redboxes, orgpc,
                                    assembler_call=True)
            raise ChangeFrame

    def debug_merge_point(self, jitdriver_sd, jd_index, portal_call_depth, current_call_id, greenkey):
        # debugging: produce a DEBUG_MERGE_POINT operation
        loc = jitdriver_sd.warmstate.get_location_str(greenkey)
        debug_print(loc)
        args = [ConstInt(jd_index), ConstInt(portal_call_depth), ConstInt(current_call_id)] + greenkey
        self.metainterp.history.record(rop.DEBUG_MERGE_POINT, args, None)

    @arguments("box", "label")
    def opimpl_goto_if_exception_mismatch(self, vtablebox, next_exc_target):
        metainterp = self.metainterp
        last_exc_value_box = metainterp.last_exc_value_box
        assert last_exc_value_box is not None
        assert metainterp.class_of_last_exc_is_const
        if not metainterp.cpu.ts.instanceOf(last_exc_value_box, vtablebox):
            self.pc = next_exc_target

    @arguments("box", "orgpc")
    def opimpl_raise(self, exc_value_box, orgpc):
        # xxx hack
        if not self.metainterp.heapcache.is_class_known(exc_value_box):
            clsbox = self.cls_of_box(exc_value_box)
            self.metainterp.generate_guard(rop.GUARD_CLASS, exc_value_box,
                                           [clsbox], resumepc=orgpc)
        self.metainterp.class_of_last_exc_is_const = True
        self.metainterp.last_exc_value_box = exc_value_box
        self.metainterp.popframe()
        self.metainterp.finishframe_exception()

    @arguments()
    def opimpl_reraise(self):
        assert self.metainterp.last_exc_value_box is not None
        self.metainterp.popframe()
        self.metainterp.finishframe_exception()

    @arguments()
    def opimpl_last_exception(self):
        # Same comment as in opimpl_goto_if_exception_mismatch().
        exc_value_box = self.metainterp.last_exc_value_box
        assert exc_value_box is not None
        assert self.metainterp.class_of_last_exc_is_const
        return self.metainterp.cpu.ts.cls_of_box(exc_value_box)

    @arguments()
    def opimpl_last_exc_value(self):
        exc_value_box = self.metainterp.last_exc_value_box
        assert exc_value_box is not None
        return exc_value_box

    @arguments("box")
    def opimpl_debug_fatalerror(self, box):
        from rpython.rtyper.lltypesystem import rstr, lloperation
        msg = box.getref(lltype.Ptr(rstr.STR))
        lloperation.llop.debug_fatalerror(lltype.Void, msg)

    @arguments("box", "box", "box", "box", "box")
    def opimpl_jit_debug(self, stringbox, arg1box, arg2box, arg3box, arg4box):
        from rpython.rtyper.lltypesystem import rstr
        from rpython.rtyper.annlowlevel import hlstr
        msg = stringbox.getref(lltype.Ptr(rstr.STR))
        debug_print('jit_debug:', hlstr(msg),
                    arg1box.getint(), arg2box.getint(),
                    arg3box.getint(), arg4box.getint())
        args = [stringbox, arg1box, arg2box, arg3box, arg4box]
        i = 4
        while i > 0 and args[i].getint() == -sys.maxint-1:
            i -= 1
        assert i >= 0
        op = self.metainterp.history.record(rop.JIT_DEBUG, args[:i+1], None)
        self.metainterp.attach_debug_info(op)

    @arguments("box")
    def _opimpl_assert_green(self, box):
        if not isinstance(box, Const):
            msg = "assert_green failed at %s:%d" % (
                self.jitcode.name,
                self.pc)
            if we_are_translated():
                from rpython.rtyper.annlowlevel import llstr
                from rpython.rtyper.lltypesystem import lloperation
                lloperation.llop.debug_fatalerror(lltype.Void, llstr(msg))
            else:
                from rpython.rlib.jit import AssertGreenFailed
                raise AssertGreenFailed(msg)

    opimpl_int_assert_green   = _opimpl_assert_green
    opimpl_ref_assert_green   = _opimpl_assert_green
    opimpl_float_assert_green = _opimpl_assert_green

    @arguments()
    def opimpl_current_trace_length(self):
        trace_length = len(self.metainterp.history.operations)
        return ConstInt(trace_length)

    @arguments("box")
    def _opimpl_isconstant(self, box):
        return ConstInt(isinstance(box, Const))

    opimpl_int_isconstant = opimpl_ref_isconstant = _opimpl_isconstant

    @arguments("box")
    def _opimpl_isvirtual(self, box):
        return ConstInt(self.metainterp.heapcache.is_unescaped(box))

    opimpl_ref_isvirtual = _opimpl_isvirtual

    @arguments("box")
    def opimpl_virtual_ref(self, box):
        # Details on the content of metainterp.virtualref_boxes:
        #
        #  * it's a list whose items go two by two, containing first the
        #    virtual box (e.g. the PyFrame) and then the vref box (e.g.
        #    the 'virtual_ref(frame)').
        #
        #  * if we detect that the virtual box escapes during tracing
        #    already (by generating a CALL_MAY_FORCE that marks the flags
        #    in the vref), then we replace the vref in the list with
        #    ConstPtr(NULL).
        #
        metainterp = self.metainterp
        vrefinfo = metainterp.staticdata.virtualref_info
        obj = box.getref_base()
        vref = vrefinfo.virtual_ref_during_tracing(obj)
        resbox = history.BoxPtr(vref)
        self.metainterp.heapcache.new(resbox)
        cindex = history.ConstInt(len(metainterp.virtualref_boxes) // 2)
        metainterp.history.record(rop.VIRTUAL_REF, [box, cindex], resbox)
        # Note: we allocate a JIT_VIRTUAL_REF here
        # (in virtual_ref_during_tracing()), in order to detect when
        # the virtual escapes during tracing already.  We record it as a
        # VIRTUAL_REF operation.  Later, optimizeopt.py should either kill
        # that operation or replace it with a NEW_WITH_VTABLE followed by
        # SETFIELD_GCs.
        metainterp.virtualref_boxes.append(box)
        metainterp.virtualref_boxes.append(resbox)
        return resbox

    @arguments("box")
    def opimpl_virtual_ref_finish(self, box):
        # virtual_ref_finish() assumes that we have a stack-like, last-in
        # first-out order.
        metainterp = self.metainterp
        vrefbox = metainterp.virtualref_boxes.pop()
        lastbox = metainterp.virtualref_boxes.pop()
        assert box.getref_base() == lastbox.getref_base()
        vrefinfo = metainterp.staticdata.virtualref_info
        vref = vrefbox.getref_base()
        if vrefinfo.is_virtual_ref(vref):
            # XXX write a comment about nullbox
            nullbox = self.metainterp.cpu.ts.CONST_NULL
            metainterp.history.record(rop.VIRTUAL_REF_FINISH,
                                      [vrefbox, nullbox], None)

    @arguments()
    def opimpl_ll_read_timestamp(self):
        return self.metainterp.execute_and_record(rop.READ_TIMESTAMP, None)

    @arguments("box", "box", "box")
    def _opimpl_libffi_save_result(self, box_cif_description,
                                   box_exchange_buffer, box_result):
        from rpython.rtyper.lltypesystem import llmemory
        from rpython.rlib.jit_libffi import CIF_DESCRIPTION_P
        from rpython.jit.backend.llsupport.ffisupport import get_arg_descr

        cif_description = box_cif_description.getint()
        cif_description = llmemory.cast_int_to_adr(cif_description)
        cif_description = llmemory.cast_adr_to_ptr(cif_description,
                                                   CIF_DESCRIPTION_P)

        kind, descr, itemsize = get_arg_descr(self.metainterp.cpu, cif_description.rtype)

        if kind != 'v':
            ofs = cif_description.exchange_result
            assert ofs % itemsize == 0     # alignment check (result)
            self.metainterp.history.record(rop.SETARRAYITEM_RAW,
                                           [box_exchange_buffer,
                                            ConstInt(ofs // itemsize),
                                            box_result],
                                           None, descr)

    opimpl_libffi_save_result_int         = _opimpl_libffi_save_result
    opimpl_libffi_save_result_float       = _opimpl_libffi_save_result
    opimpl_libffi_save_result_longlong    = _opimpl_libffi_save_result
    opimpl_libffi_save_result_singlefloat = _opimpl_libffi_save_result

    # ------------------------------

    def setup_call(self, argboxes):
        self.pc = 0
        count_i = count_r = count_f = 0
        for box in argboxes:
            if box.type == history.INT:
                self.registers_i[count_i] = box
                count_i += 1
            elif box.type == history.REF:
                self.registers_r[count_r] = box
                count_r += 1
            elif box.type == history.FLOAT:
                self.registers_f[count_f] = box
                count_f += 1
            else:
                raise AssertionError(box.type)

    def setup_resume_at_op(self, pc):
        self.pc = pc

    def run_one_step(self):
        # Execute the frame forward.  This method contains a loop that leaves
        # whenever the 'opcode_implementations' (which is one of the 'opimpl_'
        # methods) raises ChangeFrame.  This is the case when the current frame
        # changes, due to a call or a return.
        try:
            staticdata = self.metainterp.staticdata
            while True:
                pc = self.pc
                op = ord(self.bytecode[pc])
                #debug_print(self.jitcode.name, pc)
                #print staticdata.opcode_names[op]
                staticdata.opcode_implementations[op](self, pc)
        except ChangeFrame:
            pass

    def implement_guard_value(self, box, orgpc):
        """Promote the given Box into a Const.  Note: be careful, it's a
        bit unclear what occurs if a single opcode needs to generate
        several ones and/or ones not near the beginning."""
        if isinstance(box, Const):
            return box     # no promotion needed, already a Const
        else:
            promoted_box = box.constbox()
            self.metainterp.generate_guard(rop.GUARD_VALUE, box, [promoted_box],
                                           resumepc=orgpc)
            self.metainterp.replace_box(box, promoted_box)
            return promoted_box

    def cls_of_box(self, box):
        return self.metainterp.cpu.ts.cls_of_box(box)

    @specialize.arg(1)
    def execute(self, opnum, *argboxes):
        return self.metainterp.execute_and_record(opnum, None, *argboxes)

    @specialize.arg(1)
    def execute_with_descr(self, opnum, descr, *argboxes):
        return self.metainterp.execute_and_record(opnum, descr, *argboxes)

    @specialize.arg(1)
    def execute_varargs(self, opnum, argboxes, descr, exc, pure):
        self.metainterp.clear_exception()
        resbox = self.metainterp.execute_and_record_varargs(opnum, argboxes,
                                                            descr=descr)
        if resbox is not None:
            self.make_result_of_lastop(resbox)
            # ^^^ this is done before handle_possible_exception() because we
            # need the box to show up in get_list_of_active_boxes()
        if pure and self.metainterp.last_exc_value_box is None and resbox:
            resbox = self.metainterp.record_result_of_call_pure(resbox)
            exc = exc and not isinstance(resbox, Const)
        if exc:
            self.metainterp.handle_possible_exception()
        else:
            self.metainterp.assert_no_exception()
        return resbox

    def _build_allboxes(self, funcbox, argboxes, descr):
        allboxes = [None] * (len(argboxes)+1)
        allboxes[0] = funcbox
        src_i = src_r = src_f = 0
        i = 1
        for kind in descr.get_arg_types():
            if kind == history.INT or kind == 'S':        # single float
                while True:
                    box = argboxes[src_i]
                    src_i += 1
                    if box.type == history.INT:
                        break
            elif kind == history.REF:
                while True:
                    box = argboxes[src_r]
                    src_r += 1
                    if box.type == history.REF:
                        break
            elif kind == history.FLOAT or kind == 'L':    # long long
                while True:
                    box = argboxes[src_f]
                    src_f += 1
                    if box.type == history.FLOAT:
                        break
            else:
                raise AssertionError
            allboxes[i] = box
            i += 1
        assert i == len(allboxes)
        return allboxes

    def do_residual_call(self, funcbox, argboxes, descr, pc,
                         assembler_call=False,
                         assembler_call_jd=None):
        # First build allboxes: it may need some reordering from the
        # list provided in argboxes, depending on the order in which
        # the arguments are expected by the function
        #
        allboxes = self._build_allboxes(funcbox, argboxes, descr)
        effectinfo = descr.get_extra_info()
        if (assembler_call or
                effectinfo.check_forces_virtual_or_virtualizable()):
            # residual calls require attention to keep virtualizables in-sync
            self.metainterp.clear_exception()
            if effectinfo.oopspecindex == EffectInfo.OS_JIT_FORCE_VIRTUAL:
                resbox = self._do_jit_force_virtual(allboxes, descr, pc)
                if resbox is not None:
                    return resbox
            self.metainterp.vable_and_vrefs_before_residual_call()
            resbox = self.metainterp.execute_and_record_varargs(
                rop.CALL_MAY_FORCE, allboxes, descr=descr)
            if effectinfo.is_call_release_gil():
                self.metainterp.direct_call_release_gil()
            self.metainterp.vrefs_after_residual_call()
            vablebox = None
            if assembler_call:
                vablebox = self.metainterp.direct_assembler_call(
                    assembler_call_jd)
            if resbox is not None:
                self.make_result_of_lastop(resbox)
            self.metainterp.vable_after_residual_call(funcbox)
            self.metainterp.generate_guard(rop.GUARD_NOT_FORCED, None)
            if vablebox is not None:
                self.metainterp.history.record(rop.KEEPALIVE, [vablebox], None)
            self.metainterp.handle_possible_exception()
            # XXX refactor: direct_libffi_call() is a hack
            if effectinfo.oopspecindex == effectinfo.OS_LIBFFI_CALL:
                self.metainterp.direct_libffi_call()
            return resbox
        else:
            effect = effectinfo.extraeffect
            if effect == effectinfo.EF_LOOPINVARIANT:
                return self.execute_varargs(rop.CALL_LOOPINVARIANT, allboxes,
                                            descr, False, False)
            exc = effectinfo.check_can_raise()
            pure = effectinfo.check_is_elidable()
            return self.execute_varargs(rop.CALL, allboxes, descr, exc, pure)

    def do_conditional_call(self, condbox, funcbox, argboxes, descr, pc):
        allboxes = self._build_allboxes(funcbox, argboxes, descr)
        effectinfo = descr.get_extra_info()
        assert not effectinfo.check_forces_virtual_or_virtualizable()
        exc = effectinfo.check_can_raise()
        pure = effectinfo.check_is_elidable()
        return self.execute_varargs(rop.COND_CALL, [condbox] + allboxes, descr,
                                    exc, pure)

    def _do_jit_force_virtual(self, allboxes, descr, pc):
        assert len(allboxes) == 2
        if (self.metainterp.jitdriver_sd.virtualizable_info is None and
            self.metainterp.jitdriver_sd.greenfield_info is None):
            # can occur in case of multiple JITs
            return None
        vref_box = allboxes[1]
        standard_box = self.metainterp.virtualizable_boxes[-1]
        if standard_box is vref_box:
            return vref_box
        if self.metainterp.heapcache.is_nonstandard_virtualizable(vref_box):
            return None
        eqbox = self.metainterp.execute_and_record(rop.PTR_EQ, None, vref_box, standard_box)
        eqbox = self.implement_guard_value(eqbox, pc)
        isstandard = eqbox.getint()
        if isstandard:
            return standard_box
        else:
            return None

    def do_residual_or_indirect_call(self, funcbox, argboxes, calldescr, pc):
        """The 'residual_call' operation is emitted in two cases:
        when we have to generate a residual CALL operation, but also
        to handle an indirect_call that may need to be inlined."""
        if isinstance(funcbox, Const):
            sd = self.metainterp.staticdata
            key = sd.cpu.ts.getaddr_for_box(funcbox)
            jitcode = sd.bytecode_for_address(key)
            if jitcode is not None:
                # we should follow calls to this graph
                return self.metainterp.perform_call(jitcode, argboxes)
        # but we should not follow calls to that graph
        return self.do_residual_call(funcbox, argboxes, calldescr, pc)

# ____________________________________________________________

class MetaInterpStaticData(object):
    logger_noopt = None
    logger_ops = None

    def __init__(self, cpu, options,
                 ProfilerClass=EmptyProfiler, warmrunnerdesc=None):
        self.cpu = cpu
        self.stats = self.cpu.stats
        self.options = options
        self.logger_noopt = Logger(self)
        self.logger_ops = Logger(self, guard_number=True)

        self.profiler = ProfilerClass()
        self.profiler.cpu = cpu
        self.warmrunnerdesc = warmrunnerdesc
        if warmrunnerdesc:
            self.config = warmrunnerdesc.translator.config
        else:
            from rpython.config.translationoption import get_combined_translation_config
            self.config = get_combined_translation_config(translating=True)

        backendmodule = self.cpu.__module__
        backendmodule = backendmodule.split('.')[-2]
        self.jit_starting_line = 'JIT starting (%s)' % backendmodule

        self._addr2name_keys = []
        self._addr2name_values = []

        self.__dict__.update(compile.make_done_loop_tokens())
        for val in ['int', 'float', 'ref', 'void']:
            fullname = 'done_with_this_frame_descr_' + val
            setattr(self.cpu, fullname, getattr(self, fullname))
        d = self.exit_frame_with_exception_descr_ref
        self.cpu.exit_frame_with_exception_descr_ref = d

    def _freeze_(self):
        return True

    def setup_insns(self, insns):
        self.opcode_names = ['?'] * len(insns)
        self.opcode_implementations = [None] * len(insns)
        for key, value in insns.items():
            assert self.opcode_implementations[value] is None
            self.opcode_names[value] = key
            name, argcodes = key.split('/')
            opimpl = _get_opimpl_method(name, argcodes)
            self.opcode_implementations[value] = opimpl
        self.op_catch_exception = insns.get('catch_exception/L', -1)

    def setup_descrs(self, descrs):
        self.opcode_descrs = descrs

    def setup_indirectcalltargets(self, indirectcalltargets):
        self.indirectcalltargets = list(indirectcalltargets)

    def setup_list_of_addr2name(self, list_of_addr2name):
        self._addr2name_keys = [key for key, value in list_of_addr2name]
        self._addr2name_values = [value for key, value in list_of_addr2name]

    def finish_setup(self, codewriter, optimizer=None):
        from rpython.jit.metainterp.blackhole import BlackholeInterpBuilder
        self.blackholeinterpbuilder = BlackholeInterpBuilder(codewriter, self)
        #
        asm = codewriter.assembler
        self.setup_insns(asm.insns)
        self.setup_descrs(asm.descrs)
        self.setup_indirectcalltargets(asm.indirectcalltargets)
        self.setup_list_of_addr2name(asm.list_of_addr2name)
        #
        self.jitdrivers_sd = codewriter.callcontrol.jitdrivers_sd
        self.virtualref_info = codewriter.callcontrol.virtualref_info
        self.callinfocollection = codewriter.callcontrol.callinfocollection
        self.has_libffi_call = codewriter.callcontrol.has_libffi_call
        #
        # store this information for fastpath of call_assembler
        # (only the paths that can actually be taken)
        exc_descr = compile.PropagateExceptionDescr()
        for jd in self.jitdrivers_sd:
            name = {history.INT: 'int',
                    history.REF: 'ref',
                    history.FLOAT: 'float',
                    history.VOID: 'void'}[jd.result_type]
            tokens = getattr(self, 'loop_tokens_done_with_this_frame_%s' % name)
            jd.portal_finishtoken = tokens[0].finishdescr
            jd.propagate_exc_descr = exc_descr
        #
        self.cpu.propagate_exception_descr = exc_descr
        #
        self.globaldata = MetaInterpGlobalData(self)

    def _setup_once(self):
        """Runtime setup needed by the various components of the JIT."""
        if not self.globaldata.initialized:
            debug_print(self.jit_starting_line)
            self.cpu.setup_once()
            if not self.profiler.initialized:
                self.profiler.start()
                self.profiler.initialized = True
            self.globaldata.initialized = True

    def get_name_from_address(self, addr):
        # for debugging only
        if we_are_translated():
            d = self.globaldata.addr2name
            if d is None:
                # Build the dictionary at run-time.  This is needed
                # because the keys are function/class addresses, so they
                # can change from run to run.
                d = {}
                keys = self._addr2name_keys
                values = self._addr2name_values
                for i in range(len(keys)):
                    d[keys[i]] = values[i]
                self.globaldata.addr2name = d
            return d.get(addr, '')
        else:
            for i in range(len(self._addr2name_keys)):
                if addr == self._addr2name_keys[i]:
                    return self._addr2name_values[i]
            return ''

    def bytecode_for_address(self, fnaddress):
        if we_are_translated():
            d = self.globaldata.indirectcall_dict
            if d is None:
                # Build the dictionary at run-time.  This is needed
                # because the keys are function addresses, so they
                # can change from run to run.
                d = {}
                for jitcode in self.indirectcalltargets:
                    assert jitcode.fnaddr not in d
                    d[jitcode.fnaddr] = jitcode
                self.globaldata.indirectcall_dict = d
            return d.get(fnaddress, None)
        else:
            for jitcode in self.indirectcalltargets:
                if jitcode.fnaddr == fnaddress:
                    return jitcode
            return None

    def try_to_free_some_loops(self):
        # Increase here the generation recorded by the memory manager.
        if self.warmrunnerdesc is not None:       # for tests
            self.warmrunnerdesc.memory_manager.next_generation()

    # ---------------- logging ------------------------

    def log(self, msg):
        debug_print(msg)

# ____________________________________________________________

class MetaInterpGlobalData(object):
    """This object contains the JIT's global, mutable data.

    Warning: for any data that you put here, think that there might be
    multiple MetaInterps accessing it at the same time.  As usual we are
    safe from corruption thanks to the GIL, but keep in mind that any
    MetaInterp might modify any of these fields while another MetaInterp
    is, say, currently in a residual call to a function.  Multiple
    MetaInterps occur either with threads or, in single-threaded cases,
    with recursion.  This is a case that is not well-tested, so please
    be careful :-(  But thankfully this is one of the very few places
    where multiple concurrent MetaInterps may interact with each other.
    """
    def __init__(self, staticdata):
        self.initialized = False
        self.indirectcall_dict = None
        self.addr2name = None
        self.loopnumbering = 0

# ____________________________________________________________

class MetaInterp(object):
    portal_call_depth = 0
    cancel_count = 0

    def __init__(self, staticdata, jitdriver_sd):
        self.staticdata = staticdata
        self.cpu = staticdata.cpu
        self.jitdriver_sd = jitdriver_sd
        # Note: self.jitdriver_sd is the JitDriverStaticData that corresponds
        # to the current loop -- the outermost one.  Be careful, because
        # during recursion we can also see other jitdrivers.
        self.portal_trace_positions = []
        self.free_frames_list = []
        self.last_exc_value_box = None
        self.forced_virtualizable = None
        self.partial_trace = None
        self.retracing_from = -1
        self.call_pure_results = args_dict_box()
        self.heapcache = HeapCache()

        self.call_ids = []
        self.current_call_id = 0

    def retrace_needed(self, trace):
        self.partial_trace = trace
        self.retracing_from = len(self.history.operations) - 1
        self.heapcache.reset()


    def perform_call(self, jitcode, boxes, greenkey=None):
        # causes the metainterp to enter the given subfunction
        f = self.newframe(jitcode, greenkey)
        f.setup_call(boxes)
        raise ChangeFrame

    def is_main_jitcode(self, jitcode):
        return self.jitdriver_sd is not None and jitcode is self.jitdriver_sd.mainjitcode

    def newframe(self, jitcode, greenkey=None):
        if jitcode.is_portal:
            self.portal_call_depth += 1
            self.call_ids.append(self.current_call_id)
            self.current_call_id += 1
        if greenkey is not None and self.is_main_jitcode(jitcode):
            self.portal_trace_positions.append(
                    (greenkey, len(self.history.operations)))
        if len(self.free_frames_list) > 0:
            f = self.free_frames_list.pop()
        else:
            f = MIFrame(self)
        f.setup(jitcode, greenkey)
        self.framestack.append(f)
        return f

    def popframe(self):
        frame = self.framestack.pop()
        jitcode = frame.jitcode
        if jitcode.is_portal:
            self.portal_call_depth -= 1
            self.call_ids.pop()
        if frame.greenkey is not None and self.is_main_jitcode(jitcode):
            self.portal_trace_positions.append(
                    (None, len(self.history.operations)))
        # we save the freed MIFrames to avoid needing to re-create new
        # MIFrame objects all the time; they are a bit big, with their
        # 3*256 register entries.
        frame.cleanup_registers()
        self.free_frames_list.append(frame)

    def finishframe(self, resultbox):
        # handle a non-exceptional return from the current frame
        self.last_exc_value_box = None
        self.popframe()
        if self.framestack:
            if resultbox is not None:
                self.framestack[-1].make_result_of_lastop(resultbox)
            raise ChangeFrame
        else:
            try:
                self.compile_done_with_this_frame(resultbox)
            except SwitchToBlackhole, stb:
                self.aborted_tracing(stb.reason)
            sd = self.staticdata
            result_type = self.jitdriver_sd.result_type
            if result_type == history.VOID:
                assert resultbox is None
                raise jitexc.DoneWithThisFrameVoid()
            elif result_type == history.INT:
                raise jitexc.DoneWithThisFrameInt(resultbox.getint())
            elif result_type == history.REF:
                raise jitexc.DoneWithThisFrameRef(self.cpu, resultbox.getref_base())
            elif result_type == history.FLOAT:
                raise jitexc.DoneWithThisFrameFloat(resultbox.getfloatstorage())
            else:
                assert False

    def finishframe_exception(self):
        excvaluebox = self.last_exc_value_box
        while self.framestack:
            frame = self.framestack[-1]
            code = frame.bytecode
            position = frame.pc    # <-- just after the insn that raised
            if position < len(code):
                opcode = ord(code[position])
                if opcode == self.staticdata.op_catch_exception:
                    # found a 'catch_exception' instruction;
                    # jump to the handler
                    target = ord(code[position+1]) | (ord(code[position+2])<<8)
                    frame.pc = target
                    raise ChangeFrame
            self.popframe()
        try:
            self.compile_exit_frame_with_exception(excvaluebox)
        except SwitchToBlackhole, stb:
            self.aborted_tracing(stb.reason)
        raise jitexc.ExitFrameWithExceptionRef(self.cpu, excvaluebox.getref_base())

    def check_recursion_invariant(self):
        portal_call_depth = -1
        for frame in self.framestack:
            jitcode = frame.jitcode
            assert jitcode.is_portal == len([
                jd for jd in self.staticdata.jitdrivers_sd
                   if jd.mainjitcode is jitcode])
            if jitcode.is_portal:
                portal_call_depth += 1
        if portal_call_depth != self.portal_call_depth:
            print "portal_call_depth problem!!!"
            print portal_call_depth, self.portal_call_depth
            for frame in self.framestack:
                jitcode = frame.jitcode
                if jitcode.is_portal:
                    print "P",
                else:
                    print " ",
                print jitcode.name
            raise AssertionError

    def generate_guard(self, opnum, box=None, extraargs=[], resumepc=-1):
        if isinstance(box, Const):    # no need for a guard
            return
        if box is not None:
            moreargs = [box] + extraargs
        else:
            moreargs = list(extraargs)
        metainterp_sd = self.staticdata
        if opnum == rop.GUARD_NOT_FORCED or opnum == rop.GUARD_NOT_FORCED_2:
            resumedescr = compile.ResumeGuardForcedDescr(metainterp_sd,
                                                         self.jitdriver_sd)
        elif opnum == rop.GUARD_NOT_INVALIDATED:
            resumedescr = compile.ResumeGuardNotInvalidated()
        else:
            resumedescr = compile.ResumeGuardDescr()
        guard_op = self.history.record(opnum, moreargs, None,
                                             descr=resumedescr)
        self.capture_resumedata(resumedescr, resumepc)
        self.staticdata.profiler.count_ops(opnum, Counters.GUARDS)
        # count
        self.attach_debug_info(guard_op)
        return guard_op

    def capture_resumedata(self, resumedescr, resumepc=-1):
        virtualizable_boxes = None
        if (self.jitdriver_sd.virtualizable_info is not None or
            self.jitdriver_sd.greenfield_info is not None):
            virtualizable_boxes = self.virtualizable_boxes
        saved_pc = 0
        if self.framestack:
            frame = self.framestack[-1]
            saved_pc = frame.pc
            if resumepc >= 0:
                frame.pc = resumepc
        resume.capture_resumedata(self.framestack, virtualizable_boxes,
                                  self.virtualref_boxes, resumedescr)
        if self.framestack:
            self.framestack[-1].pc = saved_pc

    def create_empty_history(self):
        self.history = history.History()
        self.staticdata.stats.set_history(self.history)

    def _all_constants(self, *boxes):
        if len(boxes) == 0:
            return True
        return isinstance(boxes[0], Const) and self._all_constants(*boxes[1:])

    def _all_constants_varargs(self, boxes):
        for box in boxes:
            if not isinstance(box, Const):
                return False
        return True

    @specialize.arg(1)
    def execute_and_record(self, opnum, descr, *argboxes):
        history.check_descr(descr)
        assert not (rop._CANRAISE_FIRST <= opnum <= rop._CANRAISE_LAST)
        # execute the operation
        profiler = self.staticdata.profiler
        profiler.count_ops(opnum)
        resbox = executor.execute(self.cpu, self, opnum, descr, *argboxes)
        if rop._ALWAYS_PURE_FIRST <= opnum <= rop._ALWAYS_PURE_LAST:
            return self._record_helper_pure(opnum, resbox, descr, *argboxes)
        else:
            return self._record_helper_nonpure_varargs(opnum, resbox, descr,
                                                       list(argboxes))

    @specialize.arg(1)
    def execute_and_record_varargs(self, opnum, argboxes, descr=None):
        history.check_descr(descr)
        # execute the operation
        profiler = self.staticdata.profiler
        profiler.count_ops(opnum)
        resbox = executor.execute_varargs(self.cpu, self,
                                          opnum, argboxes, descr)
        # check if the operation can be constant-folded away
        argboxes = list(argboxes)
        if rop._ALWAYS_PURE_FIRST <= opnum <= rop._ALWAYS_PURE_LAST:
            resbox = self._record_helper_pure_varargs(opnum, resbox, descr, argboxes)
        else:
            resbox = self._record_helper_nonpure_varargs(opnum, resbox, descr, argboxes)
        return resbox

    def _record_helper_pure(self, opnum, resbox, descr, *argboxes):
        canfold = self._all_constants(*argboxes)
        if canfold:
            resbox = resbox.constbox()       # ensure it is a Const
            return resbox
        else:
            resbox = resbox.nonconstbox()    # ensure it is a Box
            return self._record_helper_nonpure_varargs(opnum, resbox, descr, list(argboxes))

    def _record_helper_pure_varargs(self, opnum, resbox, descr, argboxes):
        canfold = self._all_constants_varargs(argboxes)
        if canfold:
            resbox = resbox.constbox()       # ensure it is a Const
            return resbox
        else:
            resbox = resbox.nonconstbox()    # ensure it is a Box
            return self._record_helper_nonpure_varargs(opnum, resbox, descr, argboxes)

    def _record_helper_nonpure_varargs(self, opnum, resbox, descr, argboxes):
        assert resbox is None or isinstance(resbox, Box)
        if (rop._OVF_FIRST <= opnum <= rop._OVF_LAST and
            self.last_exc_value_box is None and
            self._all_constants_varargs(argboxes)):
            return resbox.constbox()
        # record the operation
        profiler = self.staticdata.profiler
        profiler.count_ops(opnum, Counters.RECORDED_OPS)
        self.heapcache.invalidate_caches(opnum, descr, argboxes)
        op = self.history.record(opnum, argboxes, resbox, descr)
        self.attach_debug_info(op)
        return resbox


    def attach_debug_info(self, op):
        if (not we_are_translated() and op is not None
            and getattr(self, 'framestack', None)):
            op.pc = self.framestack[-1].pc
            op.name = self.framestack[-1].jitcode.name

    def execute_raised(self, exception, constant=False):
        if isinstance(exception, jitexc.JitException):
            raise jitexc.JitException, exception      # go through
        llexception = jitexc.get_llexception(self.cpu, exception)
        self.execute_ll_raised(llexception, constant)

    def execute_ll_raised(self, llexception, constant=False):
        # Exception handling: when execute.do_call() gets an exception it
        # calls metainterp.execute_raised(), which puts it into
        # 'self.last_exc_value_box'.  This is used shortly afterwards
        # to generate either GUARD_EXCEPTION or GUARD_NO_EXCEPTION, and also
        # to handle the following opcodes 'goto_if_exception_mismatch'.
        llexception = self.cpu.ts.cast_to_ref(llexception)
        exc_value_box = self.cpu.ts.get_exc_value_box(llexception)
        if constant:
            exc_value_box = exc_value_box.constbox()
        self.last_exc_value_box = exc_value_box
        self.class_of_last_exc_is_const = constant
        # 'class_of_last_exc_is_const' means that the class of the value
        # stored in the exc_value Box can be assumed to be a Const.  This
        # is only True after a GUARD_EXCEPTION or GUARD_CLASS.

    def clear_exception(self):
        self.last_exc_value_box = None

    def aborted_tracing(self, reason):
        self.staticdata.profiler.count(reason)
        debug_print('~~~ ABORTING TRACING')
        jd_sd = self.jitdriver_sd
        if not self.current_merge_points:
            greenkey = None # we're in the bridge
        else:
            greenkey = self.current_merge_points[0][0][:jd_sd.num_green_args]
            self.staticdata.warmrunnerdesc.hooks.on_abort(reason,
                                                          jd_sd.jitdriver,
                                                          greenkey,
                                                          jd_sd.warmstate.get_location_str(greenkey),
                                                          self.staticdata.logger_ops._make_log_operations(),
                                                          self.history.operations)
        self.staticdata.stats.aborted()

    def blackhole_if_trace_too_long(self):
        warmrunnerstate = self.jitdriver_sd.warmstate
        if len(self.history.operations) > warmrunnerstate.trace_limit:
            greenkey_of_huge_function = self.find_biggest_function()
            self.staticdata.stats.record_aborted(greenkey_of_huge_function)
            self.portal_trace_positions = None
            if greenkey_of_huge_function is not None:
                warmrunnerstate.disable_noninlinable_function(
                    greenkey_of_huge_function)
            raise SwitchToBlackhole(Counters.ABORT_TOO_LONG)

    def _interpret(self):
        # Execute the frames forward until we raise a DoneWithThisFrame,
        # a ExitFrameWithException, or a ContinueRunningNormally exception.
        self.staticdata.stats.entered()
        while True:
            self.framestack[-1].run_one_step()
            self.blackhole_if_trace_too_long()
            if not we_are_translated():
                self.check_recursion_invariant()

    def interpret(self):
        if we_are_translated():
            self._interpret()
        else:
            try:
                self._interpret()
            except:
                import sys
                if sys.exc_info()[0] is not None:
                    self.staticdata.log(sys.exc_info()[0].__name__)
                raise

    @specialize.arg(1)
    def compile_and_run_once(self, jitdriver_sd, *args):
        # NB. we pass explicity 'jitdriver_sd' around here, even though it
        # is also available as 'self.jitdriver_sd', because we need to
        # specialize this function and a few other ones for the '*args'.
        debug_start('jit-tracing')
        self.staticdata._setup_once()
        self.staticdata.profiler.start_tracing()
        assert jitdriver_sd is self.jitdriver_sd
        self.staticdata.try_to_free_some_loops()
        self.create_empty_history()
        try:
            original_boxes = self.initialize_original_boxes(jitdriver_sd, *args)
            return self._compile_and_run_once(original_boxes)
        finally:
            self.staticdata.profiler.end_tracing()
            debug_stop('jit-tracing')

    def _compile_and_run_once(self, original_boxes):
        self.initialize_state_from_start(original_boxes)
        self.current_merge_points = [(original_boxes, 0)]
        num_green_args = self.jitdriver_sd.num_green_args
        original_greenkey = original_boxes[:num_green_args]
        self.resumekey = compile.ResumeFromInterpDescr(original_greenkey)
        self.history.inputargs = original_boxes[num_green_args:]
        self.seen_loop_header_for_jdindex = -1
        try:
            self.interpret()
        except SwitchToBlackhole, stb:
            self.run_blackhole_interp_to_cancel_tracing(stb)
        assert False, "should always raise"

    def handle_guard_failure(self, key, deadframe):
        debug_start('jit-tracing')
        self.staticdata.profiler.start_tracing()
        assert isinstance(key, compile.ResumeGuardDescr)
        # store the resumekey.wref_original_loop_token() on 'self' to make
        # sure that it stays alive as long as this MetaInterp
        self.resumekey_original_loop_token = key.wref_original_loop_token()
        self.staticdata.try_to_free_some_loops()
        self.initialize_state_from_guard_failure(key, deadframe)
        try:
            return self._handle_guard_failure(key, deadframe)
        finally:
            self.resumekey_original_loop_token = None
            self.staticdata.profiler.end_tracing()
            debug_stop('jit-tracing')

    def _handle_guard_failure(self, key, deadframe):
        self.current_merge_points = []
        self.resumekey = key
        self.seen_loop_header_for_jdindex = -1
        if isinstance(key, compile.ResumeAtPositionDescr):
            self.seen_loop_header_for_jdindex = self.jitdriver_sd.index
            dont_change_position = True
        else:
            dont_change_position = False
        try:
            self.prepare_resume_from_failure(key.guard_opnum,
                                             dont_change_position,
                                             deadframe)
            if self.resumekey_original_loop_token is None:   # very rare case
                raise SwitchToBlackhole(Counters.ABORT_BRIDGE)
            self.interpret()
        except SwitchToBlackhole, stb:
            self.run_blackhole_interp_to_cancel_tracing(stb)
        assert False, "should always raise"

    def run_blackhole_interp_to_cancel_tracing(self, stb):
        # We got a SwitchToBlackhole exception.  Convert the framestack into
        # a stack of blackhole interpreters filled with the same values, and
        # run it.
        from rpython.jit.metainterp.blackhole import convert_and_run_from_pyjitpl
        self.aborted_tracing(stb.reason)
        convert_and_run_from_pyjitpl(self, stb.raising_exception)
        assert False    # ^^^ must raise

    def remove_consts_and_duplicates(self, boxes, endindex, duplicates):
        for i in range(endindex):
            box = boxes[i]
            if isinstance(box, Const) or box in duplicates:
                oldbox = box
                box = oldbox.clonebox()
                boxes[i] = box
                self.history.record(rop.SAME_AS, [oldbox], box)
            else:
                duplicates[box] = None

    def reached_loop_header(self, greenboxes, redboxes, resumedescr):
        self.heapcache.reset(reset_virtuals=False)

        duplicates = {}
        self.remove_consts_and_duplicates(redboxes, len(redboxes),
                                          duplicates)
        live_arg_boxes = greenboxes + redboxes
        if self.jitdriver_sd.virtualizable_info is not None:
            # we use pop() to remove the last item, which is the virtualizable
            # itself
            self.remove_consts_and_duplicates(self.virtualizable_boxes,
                                              len(self.virtualizable_boxes)-1,
                                              duplicates)
            live_arg_boxes += self.virtualizable_boxes
            live_arg_boxes.pop()
        #
        assert len(self.virtualref_boxes) == 0, "missing virtual_ref_finish()?"
        # Called whenever we reach the 'loop_header' hint.
        # First, attempt to make a bridge:
        # - if self.resumekey is a ResumeGuardDescr, it starts from a guard
        #   that failed;
        # - if self.resumekey is a ResumeFromInterpDescr, it starts directly
        #   from the interpreter.
        if not self.partial_trace:
            # FIXME: Support a retrace to be a bridge as well as a loop
            self.compile_trace(live_arg_boxes, resumedescr)

        # raises in case it works -- which is the common case, hopefully,
        # at least for bridges starting from a guard.

        # Search in current_merge_points for original_boxes with compatible
        # green keys, representing the beginning of the same loop as the one
        # we end now.

        num_green_args = self.jitdriver_sd.num_green_args
        for j in range(len(self.current_merge_points)-1, -1, -1):
            original_boxes, start = self.current_merge_points[j]
            assert len(original_boxes) == len(live_arg_boxes)
            for i in range(num_green_args):
                box1 = original_boxes[i]
                box2 = live_arg_boxes[i]
                assert isinstance(box1, Const)
                if not box1.same_constant(box2):
                    break
            else:
                # Found!  Compile it as a loop.
                # raises in case it works -- which is the common case
                if self.partial_trace:
                    if  start != self.retracing_from:
                        raise SwitchToBlackhole(Counters.ABORT_BAD_LOOP) # For now
                self.compile_loop(original_boxes, live_arg_boxes, start, resumedescr)
                # creation of the loop was cancelled!
                self.cancel_count += 1
                if self.staticdata.warmrunnerdesc:
                    memmgr = self.staticdata.warmrunnerdesc.memory_manager
                    if memmgr:
                        if self.cancel_count > memmgr.max_unroll_loops:
                            self.compile_loop_or_abort(original_boxes,
                                                       live_arg_boxes,
                                                       start, resumedescr)
                self.staticdata.log('cancelled, tracing more...')

        # Otherwise, no loop found so far, so continue tracing.
        start = len(self.history.operations)
        self.current_merge_points.append((live_arg_boxes, start))

    def _unpack_boxes(self, boxes, start, stop):
        ints = []; refs = []; floats = []
        for i in range(start, stop):
            box = boxes[i]
            if   box.type == history.INT: ints.append(box.getint())
            elif box.type == history.REF: refs.append(box.getref_base())
            elif box.type == history.FLOAT:floats.append(box.getfloatstorage())
            else: assert 0
        return ints[:], refs[:], floats[:]

    def raise_continue_running_normally(self, live_arg_boxes, loop_token):
        self.history.inputargs = None
        self.history.operations = None
        # For simplicity, we just raise ContinueRunningNormally here and
        # ignore the loop_token passed in.  It means that we go back to
        # interpreted mode, but it should come back very quickly to the
        # JIT, find probably the same 'loop_token', and execute it.
        if we_are_translated():
            num_green_args = self.jitdriver_sd.num_green_args
            gi, gr, gf = self._unpack_boxes(live_arg_boxes, 0, num_green_args)
            ri, rr, rf = self._unpack_boxes(live_arg_boxes, num_green_args,
                                            len(live_arg_boxes))
            CRN = jitexc.ContinueRunningNormally
            raise CRN(gi, gr, gf, ri, rr, rf)
        else:
            # However, in order to keep the existing tests working
            # (which are based on the assumption that 'loop_token' is
            # directly used here), a bit of custom non-translatable code...
            self._nontranslated_run_directly(live_arg_boxes, loop_token)
            assert 0, "unreachable"

    def _nontranslated_run_directly(self, live_arg_boxes, loop_token):
        "NOT_RPYTHON"
        args = []
        num_green_args = self.jitdriver_sd.num_green_args
        num_red_args = self.jitdriver_sd.num_red_args
        for box in live_arg_boxes[num_green_args:num_green_args+num_red_args]:
            if   box.type == history.INT: args.append(box.getint())
            elif box.type == history.REF: args.append(box.getref_base())
            elif box.type == history.FLOAT: args.append(box.getfloatstorage())
            else: assert 0
        self.jitdriver_sd.warmstate.execute_assembler(loop_token, *args)

    def prepare_resume_from_failure(self, opnum, dont_change_position,
                                    deadframe):
        frame = self.framestack[-1]
        if opnum == rop.GUARD_TRUE:     # a goto_if_not that jumps only now
            if not dont_change_position:
                frame.pc = frame.jitcode.follow_jump(frame.pc)
        elif opnum == rop.GUARD_FALSE:     # a goto_if_not that stops jumping
            pass
        elif opnum == rop.GUARD_VALUE or opnum == rop.GUARD_CLASS:
            pass        # the pc is already set to the *start* of the opcode
        elif (opnum == rop.GUARD_NONNULL or
              opnum == rop.GUARD_ISNULL or
              opnum == rop.GUARD_NONNULL_CLASS):
            pass        # the pc is already set to the *start* of the opcode
        elif opnum == rop.GUARD_NO_EXCEPTION or opnum == rop.GUARD_EXCEPTION:
            exception = self.cpu.grab_exc_value(deadframe)
            if exception:
                self.execute_ll_raised(lltype.cast_opaque_ptr(rclass.OBJECTPTR,
                                                              exception))
            else:
                self.clear_exception()
            try:
                self.handle_possible_exception()
            except ChangeFrame:
                pass
        elif opnum == rop.GUARD_NOT_INVALIDATED:
            pass # XXX we want to do something special in resume descr,
                 # but not now
        elif opnum == rop.GUARD_NO_OVERFLOW:   # an overflow now detected
            if not dont_change_position:
                self.execute_raised(OverflowError(), constant=True)
                try:
                    self.finishframe_exception()
                except ChangeFrame:
                    pass
        elif opnum == rop.GUARD_OVERFLOW:      # no longer overflowing
            self.clear_exception()
        else:
            from rpython.jit.metainterp.resoperation import opname
            raise NotImplementedError(opname[opnum])

    def get_procedure_token(self, greenkey, with_compiled_targets=False):
        cell = self.jitdriver_sd.warmstate.jit_cell_at_key(greenkey)
        token = cell.get_procedure_token()
        if with_compiled_targets:
            if not token:
                return None
            if not token.target_tokens:
                return None
        return token

    def compile_loop(self, original_boxes, live_arg_boxes, start,
                     resume_at_jump_descr, try_disabling_unroll=False):
        num_green_args = self.jitdriver_sd.num_green_args
        greenkey = original_boxes[:num_green_args]
        if not self.partial_trace:
            ptoken = self.get_procedure_token(greenkey)
            if ptoken is not None and ptoken.target_tokens is not None:
                # XXX this path not tested, but shown to occur on pypy-c :-(
                self.staticdata.log('cancelled: we already have a token now')
                raise SwitchToBlackhole(Counters.ABORT_BAD_LOOP)
        if self.partial_trace:
            target_token = compile.compile_retrace(self, greenkey, start,
                                                   original_boxes[num_green_args:],
                                                   live_arg_boxes[num_green_args:],
                                                   resume_at_jump_descr, self.partial_trace,
                                                   self.resumekey)
        else:
            target_token = compile.compile_loop(self, greenkey, start,
                                                original_boxes[num_green_args:],
                                                live_arg_boxes[num_green_args:],
                                                resume_at_jump_descr,
                                     try_disabling_unroll=try_disabling_unroll)
            if target_token is not None:
                assert isinstance(target_token, TargetToken)
                self.jitdriver_sd.warmstate.attach_procedure_to_interp(greenkey, target_token.targeting_jitcell_token)
                self.staticdata.stats.add_jitcell_token(target_token.targeting_jitcell_token)


        if target_token is not None: # raise if it *worked* correctly
            assert isinstance(target_token, TargetToken)
            jitcell_token = target_token.targeting_jitcell_token
            self.raise_continue_running_normally(live_arg_boxes, jitcell_token)

    def compile_loop_or_abort(self, original_boxes, live_arg_boxes,
                              start, resume_at_jump_descr):
        """Called after we aborted more than 'max_unroll_loops' times.
        As a last attempt, try to compile the loop with unrolling disabled.
        """
        if not self.partial_trace:
            self.compile_loop(original_boxes, live_arg_boxes, start,
                              resume_at_jump_descr, try_disabling_unroll=True)
        #
        self.staticdata.log('cancelled too many times!')
        raise SwitchToBlackhole(Counters.ABORT_BAD_LOOP)

    def compile_trace(self, live_arg_boxes, resume_at_jump_descr):
        num_green_args = self.jitdriver_sd.num_green_args
        greenkey = live_arg_boxes[:num_green_args]
        target_jitcell_token = self.get_procedure_token(greenkey, True)
        if not target_jitcell_token:
            return

        self.history.record(rop.JUMP, live_arg_boxes[num_green_args:], None,
                            descr=target_jitcell_token)
        try:
            target_token = compile.compile_trace(self, self.resumekey, resume_at_jump_descr)
        finally:
            self.history.operations.pop()     # remove the JUMP
        if target_token is not None: # raise if it *worked* correctly
            assert isinstance(target_token, TargetToken)
            jitcell_token = target_token.targeting_jitcell_token
            self.raise_continue_running_normally(live_arg_boxes, jitcell_token)

    def compile_done_with_this_frame(self, exitbox):
        # temporarily put a JUMP to a pseudo-loop
        self.store_token_in_vable()
        sd = self.staticdata
        result_type = self.jitdriver_sd.result_type
        if result_type == history.VOID:
            assert exitbox is None
            exits = []
            loop_tokens = sd.loop_tokens_done_with_this_frame_void
        elif result_type == history.INT:
            exits = [exitbox]
            loop_tokens = sd.loop_tokens_done_with_this_frame_int
        elif result_type == history.REF:
            exits = [exitbox]
            loop_tokens = sd.loop_tokens_done_with_this_frame_ref
        elif result_type == history.FLOAT:
            exits = [exitbox]
            loop_tokens = sd.loop_tokens_done_with_this_frame_float
        else:
            assert False
        # FIXME: kill TerminatingLoopToken?
        # FIXME: can we call compile_trace?
        token = loop_tokens[0].finishdescr
        self.history.record(rop.FINISH, exits, None, descr=token)
        target_token = compile.compile_trace(self, self.resumekey)
        if target_token is not token:
            compile.giveup()

    def store_token_in_vable(self):
        vinfo = self.jitdriver_sd.virtualizable_info
        if vinfo is None:
            return
        vbox = self.virtualizable_boxes[-1]
        if vbox is self.forced_virtualizable:
            return # we already forced it by hand
        force_token_box = history.BoxPtr()
        # in case the force_token has not been recorded, record it here
        # to make sure we know the virtualizable can be broken. However, the
        # contents of the virtualizable should be generally correct
        self.history.record(rop.FORCE_TOKEN, [], force_token_box)
        self.history.record(rop.SETFIELD_GC, [vbox, force_token_box],
                            None, descr=vinfo.vable_token_descr)
        self.generate_guard(rop.GUARD_NOT_FORCED_2, None)

    def compile_exit_frame_with_exception(self, valuebox):
        self.store_token_in_vable()
        sd = self.staticdata
        token = sd.loop_tokens_exit_frame_with_exception_ref[0].finishdescr
        self.history.record(rop.FINISH, [valuebox], None, descr=token)
        target_token = compile.compile_trace(self, self.resumekey)
        if target_token is not token:
            compile.giveup()

    @specialize.arg(1)
    def initialize_original_boxes(self, jitdriver_sd, *args):
        original_boxes = []
        self._fill_original_boxes(jitdriver_sd, original_boxes,
                                  jitdriver_sd.num_green_args, *args)
        return original_boxes

    @specialize.arg(1)
    def _fill_original_boxes(self, jitdriver_sd, original_boxes,
                             num_green_args, *args):
        if args:
            from rpython.jit.metainterp.warmstate import wrap
            box = wrap(self.cpu, args[0], num_green_args > 0)
            original_boxes.append(box)
            self._fill_original_boxes(jitdriver_sd, original_boxes,
                                      num_green_args-1, *args[1:])

    def initialize_state_from_start(self, original_boxes):
        # ----- make a new frame -----
        self.portal_call_depth = -1 # always one portal around
        self.framestack = []
        f = self.newframe(self.jitdriver_sd.mainjitcode)
        f.setup_call(original_boxes)
        assert self.portal_call_depth == 0
        self.virtualref_boxes = []
        self.initialize_withgreenfields(original_boxes)
        self.initialize_virtualizable(original_boxes)

    def initialize_state_from_guard_failure(self, resumedescr, deadframe):
        # guard failure: rebuild a complete MIFrame stack
        # This is stack-critical code: it must not be interrupted by StackOverflow,
        # otherwise the jit_virtual_refs are left in a dangling state.
        rstack._stack_criticalcode_start()
        try:
            self.portal_call_depth = -1 # always one portal around
            self.history = history.History()
            inputargs_and_holes = self.rebuild_state_after_failure(resumedescr,
                                                                   deadframe)
            self.history.inputargs = [box for box in inputargs_and_holes if box]
        finally:
            rstack._stack_criticalcode_stop()

    def initialize_virtualizable(self, original_boxes):
        vinfo = self.jitdriver_sd.virtualizable_info
        if vinfo is not None:
            index = (self.jitdriver_sd.num_green_args +
                     self.jitdriver_sd.index_of_virtualizable)
            virtualizable_box = original_boxes[index]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            # The field 'virtualizable_boxes' is not even present
            # if 'virtualizable_info' is None.  Check for that first.
            self.virtualizable_boxes = vinfo.read_boxes(self.cpu,
                                                        virtualizable)
            original_boxes += self.virtualizable_boxes
            self.virtualizable_boxes.append(virtualizable_box)
            self.initialize_virtualizable_enter()

    def initialize_withgreenfields(self, original_boxes):
        ginfo = self.jitdriver_sd.greenfield_info
        if ginfo is not None:
            assert self.jitdriver_sd.virtualizable_info is None
            index = (self.jitdriver_sd.num_green_args +
                     ginfo.red_index)
            self.virtualizable_boxes = [original_boxes[index]]

    def initialize_virtualizable_enter(self):
        vinfo = self.jitdriver_sd.virtualizable_info
        virtualizable_box = self.virtualizable_boxes[-1]
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
        vinfo.clear_vable_token(virtualizable)

    def vable_and_vrefs_before_residual_call(self):
        vrefinfo = self.staticdata.virtualref_info
        for i in range(1, len(self.virtualref_boxes), 2):
            vrefbox = self.virtualref_boxes[i]
            vref = vrefbox.getref_base()
            vrefinfo.tracing_before_residual_call(vref)
            # the FORCE_TOKEN is already set at runtime in each vref when
            # it is created, by optimizeopt.py.
        #
        vinfo = self.jitdriver_sd.virtualizable_info
        if vinfo is not None:
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            vinfo.tracing_before_residual_call(virtualizable)
            #
            force_token_box = history.BoxPtr()
            self.history.record(rop.FORCE_TOKEN, [], force_token_box)
            self.history.record(rop.SETFIELD_GC, [virtualizable_box,
                                                  force_token_box],
                                None, descr=vinfo.vable_token_descr)

    def vrefs_after_residual_call(self):
        vrefinfo = self.staticdata.virtualref_info
        for i in range(0, len(self.virtualref_boxes), 2):
            vrefbox = self.virtualref_boxes[i+1]
            vref = vrefbox.getref_base()
            if vrefinfo.tracing_after_residual_call(vref):
                # this vref was really a virtual_ref, but it escaped
                # during this CALL_MAY_FORCE.  Mark this fact by
                # generating a VIRTUAL_REF_FINISH on it and replacing
                # it by ConstPtr(NULL).
                self.stop_tracking_virtualref(i)

    def vable_after_residual_call(self, funcbox):
        vinfo = self.jitdriver_sd.virtualizable_info
        if vinfo is not None:
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            if vinfo.tracing_after_residual_call(virtualizable):
                # the virtualizable escaped during CALL_MAY_FORCE.
                self.load_fields_from_virtualizable()
                target_name = self.staticdata.get_name_from_address(funcbox.getaddr())
                if target_name:
                    target_name = "ConstClass(%s)" % target_name
                else:
                    target_name = str(funcbox.getaddr())
                debug_print('vable escaped during a call in %s to %s' % (
                    self.framestack[-1].jitcode.name, target_name
                ))
                raise SwitchToBlackhole(Counters.ABORT_ESCAPE,
                                        raising_exception=True)
                # ^^^ we set 'raising_exception' to True because we must still
                # have the eventual exception raised (this is normally done
                # after the call to vable_after_residual_call()).

    def stop_tracking_virtualref(self, i):
        virtualbox = self.virtualref_boxes[i]
        vrefbox = self.virtualref_boxes[i+1]
        # record VIRTUAL_REF_FINISH just before the current CALL_MAY_FORCE
        call_may_force_op = self.history.operations.pop()
        assert call_may_force_op.getopnum() == rop.CALL_MAY_FORCE
        self.history.record(rop.VIRTUAL_REF_FINISH,
                            [vrefbox, virtualbox], None)
        self.history.operations.append(call_may_force_op)
        # mark by replacing it with ConstPtr(NULL)
        self.virtualref_boxes[i+1] = self.cpu.ts.CONST_NULL

    def handle_possible_exception(self):
        if self.last_exc_value_box is not None:
            exception_box = self.cpu.ts.cls_of_box(self.last_exc_value_box)
            op = self.generate_guard(rop.GUARD_EXCEPTION,
                                     None, [exception_box])
            assert op is not None
            op.result = self.last_exc_value_box
            self.class_of_last_exc_is_const = True
            self.finishframe_exception()
        else:
            self.generate_guard(rop.GUARD_NO_EXCEPTION, None, [])

    def handle_possible_overflow_error(self):
        if self.last_exc_value_box is not None:
            self.generate_guard(rop.GUARD_OVERFLOW, None)
            assert isinstance(self.last_exc_value_box, Const)
            assert self.class_of_last_exc_is_const
            self.finishframe_exception()
        else:
            self.generate_guard(rop.GUARD_NO_OVERFLOW, None)

    def assert_no_exception(self):
        assert self.last_exc_value_box is None

    def rebuild_state_after_failure(self, resumedescr, deadframe):
        vinfo = self.jitdriver_sd.virtualizable_info
        ginfo = self.jitdriver_sd.greenfield_info
        self.framestack = []
        boxlists = resume.rebuild_from_resumedata(self, resumedescr, deadframe,
                                                  vinfo, ginfo)
        inputargs_and_holes, virtualizable_boxes, virtualref_boxes = boxlists
        #
        # virtual refs: make the vrefs point to the freshly allocated virtuals
        self.virtualref_boxes = virtualref_boxes
        vrefinfo = self.staticdata.virtualref_info
        for i in range(0, len(virtualref_boxes), 2):
            virtualbox = virtualref_boxes[i]
            vrefbox = virtualref_boxes[i+1]
            vrefinfo.continue_tracing(vrefbox.getref_base(),
                                      virtualbox.getref_base())
        #
        # virtualizable: synchronize the real virtualizable and the local
        # boxes, in whichever direction is appropriate
        if vinfo is not None:
            self.virtualizable_boxes = virtualizable_boxes
            # just jumped away from assembler (case 4 in the comment in
            # virtualizable.py) into tracing (case 2); if we get the
            # virtualizable from somewhere strange it might not be forced,
            # do it
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            if vinfo.is_token_nonnull_gcref(virtualizable):
                vinfo.reset_token_gcref(virtualizable)
            # fill the virtualizable with the local boxes
            self.synchronize_virtualizable()
        #
        elif self.jitdriver_sd.greenfield_info:
            self.virtualizable_boxes = virtualizable_boxes
        else:
            assert not virtualizable_boxes
        #
        return inputargs_and_holes

    def check_synchronized_virtualizable(self):
        if not we_are_translated():
            vinfo = self.jitdriver_sd.virtualizable_info
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            vinfo.check_boxes(virtualizable, self.virtualizable_boxes)

    def synchronize_virtualizable(self):
        vinfo = self.jitdriver_sd.virtualizable_info
        virtualizable_box = self.virtualizable_boxes[-1]
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
        vinfo.write_boxes(virtualizable, self.virtualizable_boxes)

    def load_fields_from_virtualizable(self):
        # Force a reload of the virtualizable fields into the local
        # boxes (called only in escaping cases).  Only call this function
        # just before SwitchToBlackhole.
        vinfo = self.jitdriver_sd.virtualizable_info
        if vinfo is not None:
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            self.virtualizable_boxes = vinfo.read_boxes(self.cpu,
                                                        virtualizable)
            self.virtualizable_boxes.append(virtualizable_box)

    def gen_store_back_in_vable(self, box):
        vinfo = self.jitdriver_sd.virtualizable_info
        if vinfo is not None:
            # xxx only write back the fields really modified
            vbox = self.virtualizable_boxes[-1]
            if vbox is not box:
                # ignore the hint on non-standard virtualizable
                # specifically, ignore it on a virtual
                return
            if self.forced_virtualizable is not None:
                # this can happen only in strange cases, but we don't care
                # it was already forced
                return
            self.forced_virtualizable = vbox
            for i in range(vinfo.num_static_extra_boxes):
                fieldbox = self.virtualizable_boxes[i]
                descr = vinfo.static_field_descrs[i]
                self.execute_and_record(rop.SETFIELD_GC, descr, vbox, fieldbox)
            i = vinfo.num_static_extra_boxes
            virtualizable = vinfo.unwrap_virtualizable_box(vbox)
            for k in range(vinfo.num_arrays):
                descr = vinfo.array_field_descrs[k]
                abox = self.execute_and_record(rop.GETFIELD_GC, descr, vbox)
                descr = vinfo.array_descrs[k]
                for j in range(vinfo.get_array_length(virtualizable, k)):
                    itembox = self.virtualizable_boxes[i]
                    i += 1
                    self.execute_and_record(rop.SETARRAYITEM_GC, descr,
                                            abox, ConstInt(j), itembox)
            assert i + 1 == len(self.virtualizable_boxes)
            # we're during tracing, so we should not execute it
            self.history.record(rop.SETFIELD_GC, [vbox, self.cpu.ts.CONST_NULL],
                                None, descr=vinfo.vable_token_descr)

    def replace_box(self, oldbox, newbox):
        assert isinstance(oldbox, Box)
        for frame in self.framestack:
            frame.replace_active_box_in_frame(oldbox, newbox)
        boxes = self.virtualref_boxes
        for i in range(len(boxes)):
            if boxes[i] is oldbox:
                boxes[i] = newbox
        if (self.jitdriver_sd.virtualizable_info is not None or
            self.jitdriver_sd.greenfield_info is not None):
            boxes = self.virtualizable_boxes
            for i in range(len(boxes)):
                if boxes[i] is oldbox:
                    boxes[i] = newbox
        self.heapcache.replace_box(oldbox, newbox)

    def find_biggest_function(self):
        start_stack = []
        max_size = 0
        max_key = None
        for pair in self.portal_trace_positions:
            key, pos = pair
            if key is not None:
                start_stack.append(pair)
            else:
                greenkey, startpos = start_stack.pop()
                size = pos - startpos
                if size > max_size:
                    max_size = size
                    max_key = greenkey
        if start_stack:
            key, pos = start_stack[0]
            size = len(self.history.operations) - pos
            if size > max_size:
                max_size = size
                max_key = key
        return max_key

    def record_result_of_call_pure(self, resbox):
        """ Patch a CALL into a CALL_PURE.
        """
        op = self.history.operations[-1]
        assert op.getopnum() == rop.CALL
        resbox_as_const = resbox.constbox()
        for i in range(op.numargs()):
            if not isinstance(op.getarg(i), Const):
                break
        else:
            # all-constants: remove the CALL operation now and propagate a
            # constant result
            self.history.operations.pop()
            return resbox_as_const
        # not all constants (so far): turn CALL into CALL_PURE, which might
        # be either removed later by optimizeopt or turned back into CALL.
        arg_consts = [a.constbox() for a in op.getarglist()]
        self.call_pure_results[arg_consts] = resbox_as_const
        newop = op.copy_and_change(rop.CALL_PURE, args=op.getarglist())
        self.history.operations[-1] = newop
        return resbox

    def direct_assembler_call(self, targetjitdriver_sd):
        """ Generate a direct call to assembler for portal entry point,
        patching the CALL_MAY_FORCE that occurred just now.
        """
        op = self.history.operations.pop()
        assert op.getopnum() == rop.CALL_MAY_FORCE
        num_green_args = targetjitdriver_sd.num_green_args
        arglist = op.getarglist()
        greenargs = arglist[1:num_green_args+1]
        args = arglist[num_green_args+1:]
        assert len(args) == targetjitdriver_sd.num_red_args
        warmrunnerstate = targetjitdriver_sd.warmstate
        token = warmrunnerstate.get_assembler_token(greenargs)
        op = op.copy_and_change(rop.CALL_ASSEMBLER, args=args, descr=token)
        self.history.operations.append(op)
        #
        # To fix an obscure issue, make sure the vable stays alive
        # longer than the CALL_ASSEMBLER operation.  We do it by
        # inserting explicitly an extra KEEPALIVE operation.
        jd = token.outermost_jitdriver_sd
        if jd.index_of_virtualizable >= 0:
            return args[jd.index_of_virtualizable]
        else:
            return None

    def direct_libffi_call(self):
        """Generate a direct call to C code, patching the CALL_MAY_FORCE
        to jit_ffi_call() that occurred just now.
        """
        # an 'assert' that constant-folds away the rest of this function
        # if the codewriter didn't produce any OS_LIBFFI_CALL at all.
        assert self.staticdata.has_libffi_call
        #
        from rpython.rtyper.lltypesystem import llmemory
        from rpython.rlib.jit_libffi import CIF_DESCRIPTION_P
        from rpython.jit.backend.llsupport.ffisupport import get_arg_descr
        #
        num_extra_guards = 0
        while True:
            op = self.history.operations[-1-num_extra_guards]
            if op.getopnum() == rop.CALL_MAY_FORCE:
                break
            assert op.is_guard()
            num_extra_guards += 1
        #
        box_cif_description = op.getarg(1)
        if not isinstance(box_cif_description, ConstInt):
            return
        cif_description = box_cif_description.getint()
        cif_description = llmemory.cast_int_to_adr(cif_description)
        cif_description = llmemory.cast_adr_to_ptr(cif_description,
                                                   CIF_DESCRIPTION_P)
        extrainfo = op.getdescr().get_extra_info()
        calldescr = self.cpu.calldescrof_dynamic(cif_description, extrainfo)
        if calldescr is None:
            return
        #
        extra_guards = []
        for i in range(num_extra_guards):
            extra_guards.append(self.history.operations.pop())
        extra_guards.reverse()
        #
        box_exchange_buffer = op.getarg(3)
        self.history.operations.pop()
        arg_boxes = []

        for i in range(cif_description.nargs):
            kind, descr, itemsize = get_arg_descr(self.cpu,
                                                  cif_description.atypes[i])
            if kind == 'i':
                box_arg = history.BoxInt()
            elif kind == 'f':
                box_arg = history.BoxFloat()
            else:
                assert kind == 'v'
                continue
            ofs = cif_description.exchange_args[i]
            assert ofs % itemsize == 0     # alignment check
            self.history.record(rop.GETARRAYITEM_RAW,
                                [box_exchange_buffer,
                                 ConstInt(ofs // itemsize)],
                                box_arg, descr)
            arg_boxes.append(box_arg)
        #
        box_result = op.result
        self.history.record(rop.CALL_RELEASE_GIL,
                            [op.getarg(2)] + arg_boxes,
                            box_result, calldescr)
        #
        self.history.operations.extend(extra_guards)
        #
        # note that the result is written back to the exchange_buffer by the
        # special op libffi_save_result_{int,float}

    def direct_call_release_gil(self):
        op = self.history.operations.pop()
        assert op.opnum == rop.CALL_MAY_FORCE
        descr = op.getdescr()
        effectinfo = descr.get_extra_info()
        realfuncaddr = effectinfo.call_release_gil_target
        funcbox = ConstInt(heaptracker.adr2int(realfuncaddr))
        self.history.record(rop.CALL_RELEASE_GIL,
                            [funcbox] + op.getarglist()[1:],
                            op.result, descr)
        if not we_are_translated():       # for llgraph
            descr._original_func_ = op.getarg(0).value

# ____________________________________________________________

class ChangeFrame(jitexc.JitException):
    """Raised after we mutated metainterp.framestack, in order to force
    it to reload the current top-of-stack frame that gets interpreted."""

class SwitchToBlackhole(jitexc.JitException):
    def __init__(self, reason, raising_exception=False):
        self.reason = reason
        self.raising_exception = raising_exception
        # ^^^ must be set to True if the SwitchToBlackhole is raised at a
        #     point where the exception on metainterp.last_exc_value_box
        #     is supposed to be raised.  The default False means that it
        #     should just be copied into the blackhole interp, but not raised.

# ____________________________________________________________

def _get_opimpl_method(name, argcodes):
    from rpython.jit.metainterp.blackhole import signedord
    #
    def handler(self, position):
        assert position >= 0
        args = ()
        next_argcode = 0
        code = self.bytecode
        orgpc = position
        position += 1
        for argtype in argtypes:
            if argtype == "box":     # a box, of whatever type
                argcode = argcodes[next_argcode]
                next_argcode = next_argcode + 1
                if argcode == 'i':
                    value = self.registers_i[ord(code[position])]
                elif argcode == 'c':
                    value = ConstInt(signedord(code[position]))
                elif argcode == 'r':
                    value = self.registers_r[ord(code[position])]
                elif argcode == 'f':
                    value = self.registers_f[ord(code[position])]
                else:
                    raise AssertionError("bad argcode")
                position += 1
            elif argtype == "descr" or argtype == "jitcode":
                assert argcodes[next_argcode] == 'd'
                next_argcode = next_argcode + 1
                index = ord(code[position]) | (ord(code[position+1])<<8)
                value = self.metainterp.staticdata.opcode_descrs[index]
                if argtype == "jitcode":
                    assert isinstance(value, JitCode)
                position += 2
            elif argtype == "label":
                assert argcodes[next_argcode] == 'L'
                next_argcode = next_argcode + 1
                value = ord(code[position]) | (ord(code[position+1])<<8)
                position += 2
            elif argtype == "boxes":     # a list of boxes of some type
                length = ord(code[position])
                value = [None] * length
                self.prepare_list_of_boxes(value, 0, position,
                                           argcodes[next_argcode])
                next_argcode = next_argcode + 1
                position += 1 + length
            elif argtype == "boxes2":     # two lists of boxes merged into one
                length1 = ord(code[position])
                position2 = position + 1 + length1
                length2 = ord(code[position2])
                value = [None] * (length1 + length2)
                self.prepare_list_of_boxes(value, 0, position,
                                           argcodes[next_argcode])
                self.prepare_list_of_boxes(value, length1, position2,
                                           argcodes[next_argcode + 1])
                next_argcode = next_argcode + 2
                position = position2 + 1 + length2
            elif argtype == "boxes3":    # three lists of boxes merged into one
                length1 = ord(code[position])
                position2 = position + 1 + length1
                length2 = ord(code[position2])
                position3 = position2 + 1 + length2
                length3 = ord(code[position3])
                value = [None] * (length1 + length2 + length3)
                self.prepare_list_of_boxes(value, 0, position,
                                           argcodes[next_argcode])
                self.prepare_list_of_boxes(value, length1, position2,
                                           argcodes[next_argcode + 1])
                self.prepare_list_of_boxes(value, length1 + length2, position3,
                                           argcodes[next_argcode + 2])
                next_argcode = next_argcode + 3
                position = position3 + 1 + length3
            elif argtype == "orgpc":
                value = orgpc
            elif argtype == "int":
                argcode = argcodes[next_argcode]
                next_argcode = next_argcode + 1
                if argcode == 'i':
                    value = self.registers_i[ord(code[position])].getint()
                elif argcode == 'c':
                    value = signedord(code[position])
                else:
                    raise AssertionError("bad argcode")
                position += 1
            elif argtype == "jitcode_position":
                value = position
            else:
                raise AssertionError("bad argtype: %r" % (argtype,))
            args += (value,)
        #
        num_return_args = len(argcodes) - next_argcode
        assert num_return_args == 0 or num_return_args == 2
        if num_return_args:
            # Save the type of the resulting box.  This is needed if there is
            # a get_list_of_active_boxes().  See comments there.
            self._result_argcode = argcodes[next_argcode + 1]
            position += 1
        else:
            self._result_argcode = 'v'
        self.pc = position
        #
        if not we_are_translated():
            if self.debug:
                print '\tpyjitpl: %s(%s)' % (name, ', '.join(map(repr, args))),
            try:
                resultbox = unboundmethod(self, *args)
            except Exception, e:
                if self.debug:
                    print '-> %s!' % e.__class__.__name__
                raise
            if num_return_args == 0:
                if self.debug:
                    print
                assert resultbox is None
            else:
                if self.debug:
                    print '-> %r' % (resultbox,)
                assert argcodes[next_argcode] == '>'
                result_argcode = argcodes[next_argcode + 1]
                assert resultbox.type == {'i': history.INT,
                                          'r': history.REF,
                                          'f': history.FLOAT}[result_argcode]
        else:
            resultbox = unboundmethod(self, *args)
        #
        if resultbox is not None:
            self.make_result_of_lastop(resultbox)
        elif not we_are_translated():
            assert self._result_argcode in 'v?'
    #
    unboundmethod = getattr(MIFrame, 'opimpl_' + name).im_func
    argtypes = unrolling_iterable(unboundmethod.argtypes)
    handler.func_name = 'handler_' + name
    return handler

def put_back_list_of_boxes3(frame, position, newvalue):
    code = frame.bytecode
    length1 = ord(code[position])
    position2 = position + 1 + length1
    length2 = ord(code[position2])
    position3 = position2 + 1 + length2
    length3 = ord(code[position3])
    assert len(newvalue) == length1 + length2 + length3
    frame._put_back_list_of_boxes(newvalue, 0, position)
    frame._put_back_list_of_boxes(newvalue, length1, position2)
    frame._put_back_list_of_boxes(newvalue, length1 + length2, position3)
