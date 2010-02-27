import py, os
from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.debug import debug_start, debug_stop, debug_print

from pypy.jit.metainterp import history, compile, resume
from pypy.jit.metainterp.history import Const, ConstInt, Box
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp import codewriter, executor
from pypy.jit.metainterp.logger import Logger
from pypy.jit.metainterp.jitprof import BLACKHOLED_OPS, EmptyProfiler
from pypy.jit.metainterp.jitprof import GUARDS, RECORDED_OPS, ABORT_ESCAPE
from pypy.jit.metainterp.jitprof import ABORT_TOO_LONG, ABORT_BRIDGE
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import specialize
from pypy.rlib.jit import DEBUG_OFF, DEBUG_PROFILE, DEBUG_STEPS, DEBUG_DETAILED
from pypy.jit.metainterp.compile import GiveUp

# ____________________________________________________________

def check_args(*args):
    for arg in args:
        assert isinstance(arg, (Box, Const))

class arguments(object):
    def __init__(self, *argtypes):
        self.argtypes = argtypes

    def __eq__(self, other):
        if not isinstance(other, arguments):
            return NotImplemented
        return self.argtypes == other.argtypes

    def __ne__(self, other):
        if not isinstance(other, arguments):
            return NotImplemented
        return self.argtypes != other.argtypes

    def __call__(self, func):
        argtypes = unrolling_iterable(self.argtypes)
        def wrapped(self, orgpc):
            args = (self, )
            for argspec in argtypes:
                if argspec == "box":
                    box = self.load_arg()
                    args += (box, )
                elif argspec == "constbox":
                    args += (self.load_const_arg(), )
                elif argspec == "int":
                    args += (self.load_int(), )
                elif argspec == "jumptarget":
                    args += (self.load_3byte(), )
                elif argspec == "jumptargets":
                    num = self.load_int()
                    args += ([self.load_3byte() for i in range(num)], )
                elif argspec == "varargs":
                    args += (self.load_varargs(), )
                elif argspec == "constargs":
                    args += (self.load_constargs(), )
                elif argspec == "descr":
                    descr = self.load_const_arg()
                    assert isinstance(descr, history.AbstractDescr)
                    args += (descr, )
                elif argspec == "bytecode":
                    bytecode = self.load_const_arg()
                    assert isinstance(bytecode, codewriter.JitCode)
                    args += (bytecode, )
                elif argspec == "orgpc":
                    args += (orgpc, )
                elif argspec == "methdescr":
                    methdescr = self.load_const_arg()
                    assert isinstance(methdescr,
                                      history.AbstractMethDescr)
                    args += (methdescr, )
                else:
                    assert 0, "unknown argtype declaration: %r" % (argspec,)
            val = func(*args)
            if val is None:
                val = False
            return val
        name = func.func_name
        wrapped.func_name = "wrap_" + name
        wrapped.argspec = self
        return wrapped

# ____________________________________________________________


class MIFrame(object):
    exception_box = None
    exc_value_box = None
    # for resume.py operation
    parent_resumedata_snapshot = None
    parent_resumedata_frame_info_list = None

    def __init__(self, metainterp, jitcode, greenkey=None):
        assert isinstance(jitcode, codewriter.JitCode)
        self.metainterp = metainterp
        self.jitcode = jitcode
        self.bytecode = jitcode.code
        self.constants = jitcode.constants
        self.exception_target = -1
        self.name = jitcode.name # purely for having name attribute
        # this is not None for frames that are recursive portal calls
        self.greenkey = greenkey

    # ------------------------------
    # Decoding of the JitCode

    def load_int(self):
        pc = self.pc
        result = ord(self.bytecode[pc])
        self.pc = pc + 1
        if result > 0x7F:
            result = self._load_larger_int(result)
        return result

    def _load_larger_int(self, result):    # slow path
        result = result & 0x7F
        shift = 7
        pc = self.pc
        while 1:
            byte = ord(self.bytecode[pc])
            pc += 1
            result += (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
        self.pc = pc
        return intmask(result)
    _load_larger_int._dont_inline_ = True

    def load_3byte(self):
        pc = self.pc
        result = (((ord(self.bytecode[pc + 0])) << 16) |
                  ((ord(self.bytecode[pc + 1])) <<  8) |
                  ((ord(self.bytecode[pc + 2])) <<  0))
        self.pc = pc + 3
        return result

    def load_bool(self):
        pc = self.pc
        result = ord(self.bytecode[pc])
        self.pc = pc + 1
        return bool(result)

    def getenv(self, i):
        assert i >= 0
        j = i >> 1
        if i & 1:
            return self.constants[j]
        else:
            assert j < len(self.env)
            return self.env[j]

    def load_arg(self):
        return self.getenv(self.load_int())

    def load_const_arg(self):
        return self.constants[self.load_int()]

    def load_varargs(self):
        count = self.load_int()
        return [self.load_arg() for i in range(count)]

    def load_constargs(self):
        count = self.load_int()
        return [self.load_const_arg() for i in range(count)]

    def ignore_varargs(self):
        count = self.load_int()
        for i in range(count):
            self.load_int()

    def getvarenv(self, i):
        return self.env[i]

    def make_result_box(self, box):
        assert isinstance(box, Box) or isinstance(box, Const)
        self.env.append(box)

    # ------------------------------

    for _n in range(codewriter.MAX_MAKE_NEW_VARS):
        _decl = ', '.join(["'box'" for _i in range(_n)])
        _allargs = ', '.join(["box%d" % _i for _i in range(_n)])
        exec py.code.Source("""
            @arguments(%s)
            def opimpl_make_new_vars_%d(self, %s):
                if not we_are_translated():
                    check_args(%s)
                self.env = [%s]
        """ % (_decl, _n, _allargs, _allargs, _allargs)).compile()

    @arguments("varargs")
    def opimpl_make_new_vars(self, newenv):
        if not we_are_translated():
            check_args(*newenv)
        self.env = newenv

    for _opimpl in ['int_add', 'int_sub', 'int_mul', 'int_floordiv', 'int_mod',
                    'int_lt', 'int_le', 'int_eq',
                    'int_ne', 'int_gt', 'int_ge',
                    'int_and', 'int_or', 'int_xor',
                    'int_rshift', 'int_lshift', 'uint_rshift',
                    'uint_lt', 'uint_le', 'uint_gt', 'uint_ge',
                    'float_add', 'float_sub', 'float_mul', 'float_truediv',
                    'float_lt', 'float_le', 'float_eq',
                    'float_ne', 'float_gt', 'float_ge',
                    ]:
        exec py.code.Source('''
            @arguments("box", "box")
            def opimpl_%s(self, b1, b2):
                self.execute(rop.%s, b1, b2)
        ''' % (_opimpl, _opimpl.upper())).compile()

    for _opimpl in ['int_add_ovf', 'int_sub_ovf', 'int_mul_ovf']:
        exec py.code.Source('''
            @arguments("box", "box")
            def opimpl_%s(self, b1, b2):
                self.execute(rop.%s, b1, b2)
                return self.metainterp.handle_overflow_error()
        ''' % (_opimpl, _opimpl.upper())).compile()

    for _opimpl in ['int_is_true', 'int_neg', 'int_invert', 'bool_not',
                    'cast_ptr_to_int', 'cast_float_to_int',
                    'cast_int_to_float', 'float_neg', 'float_abs',
                    'float_is_true',
                    ]:
        exec py.code.Source('''
            @arguments("box")
            def opimpl_%s(self, b):
                self.execute(rop.%s, b)
        ''' % (_opimpl, _opimpl.upper())).compile()

    @arguments()
    def opimpl_return(self):
        assert len(self.env) == 1
        return self.metainterp.finishframe(self.env[0])

    @arguments()
    def opimpl_void_return(self):
        assert len(self.env) == 0
        return self.metainterp.finishframe(None)

    @arguments("jumptarget")
    def opimpl_goto(self, target):
        self.pc = target

    @arguments("orgpc", "jumptarget", "box", "varargs")
    def opimpl_goto_if_not(self, pc, target, box, livelist):
        switchcase = box.getint()
        if switchcase:
            opnum = rop.GUARD_TRUE
        else:
            self.pc = target
            opnum = rop.GUARD_FALSE
        self.env = livelist
        self.generate_guard(pc, opnum, box)
        # note about handling self.env explicitly here: it is done in
        # such a way that the 'box' on which we generate the guard is
        # typically not included in the livelist.

    def follow_jump(self):
        _op_goto_if_not = self.metainterp.staticdata._op_goto_if_not
        assert ord(self.bytecode[self.pc]) == _op_goto_if_not
        self.pc += 1          # past the bytecode for 'goto_if_not'
        target = self.load_3byte()  # load the 'target' argument
        self.pc = target      # jump

    def ignore_next_guard_nullness(self, opnum):
        _op_ooisnull = self.metainterp.staticdata._op_ooisnull
        _op_oononnull = self.metainterp.staticdata._op_oononnull
        bc = ord(self.bytecode[self.pc])
        if bc == _op_ooisnull:
            if opnum == rop.GUARD_ISNULL:
                res = ConstInt(0)
            else:
                res = ConstInt(1)
        else:
            assert bc == _op_oononnull
            if opnum == rop.GUARD_ISNULL:
                res = ConstInt(1)
            else:
                res = ConstInt(0)
        self.pc += 1    # past the bytecode for ptr_iszero/ptr_nonzero
        self.load_int() # past the 'box' argument
        self.make_result_box(res)

    def dont_follow_jump(self):
        _op_goto_if_not = self.metainterp.staticdata._op_goto_if_not
        assert ord(self.bytecode[self.pc]) == _op_goto_if_not
        self.pc += 1          # past the bytecode for 'goto_if_not'
        self.load_3byte()     # past the 'target' argument
        self.load_int()       # past the 'box' argument
        self.ignore_varargs() # past the 'livelist' argument

    @arguments("orgpc", "box", "constargs", "jumptargets")
    def opimpl_switch(self, pc, valuebox, constargs, jumptargets):
        box = self.implement_guard_value(pc, valuebox)
        for i in range(len(constargs)):
            casebox = constargs[i]
            if box.same_constant(casebox):
                self.pc = jumptargets[i]
                break

    @arguments("orgpc", "box", "constbox")
    def opimpl_switch_dict(self, pc, valuebox, switchdict):
        box = self.implement_guard_value(pc, valuebox)
        search_value = box.getint()
        assert isinstance(switchdict, codewriter.SwitchDict)
        try:
            self.pc = switchdict.dict[search_value]
        except KeyError:
            pass

    @arguments("descr")
    def opimpl_new(self, size):
        self.execute_with_descr(rop.NEW, descr=size)

    @arguments("constbox")
    def opimpl_new_with_vtable(self, vtablebox):
        self.execute(rop.NEW_WITH_VTABLE, vtablebox)

    @arguments("box")
    def opimpl_runtimenew(self, classbox):
        self.execute(rop.RUNTIMENEW, classbox)

    @arguments("orgpc", "box", "descr")
    def opimpl_instanceof(self, pc, objbox, typedescr):
        clsbox = self.cls_of_box(objbox)
        if isinstance(objbox, Box):
            self.generate_guard(pc, rop.GUARD_CLASS, objbox, [clsbox])
        self.execute_with_descr(rop.INSTANCEOF, typedescr, objbox)

    @arguments("box", "box")
    def opimpl_subclassof(self, box1, box2):
        self.execute(rop.SUBCLASSOF, box1, box2)

    @arguments("descr", "box")
    def opimpl_new_array(self, itemsize, countbox):
        self.execute_with_descr(rop.NEW_ARRAY, itemsize, countbox)

    @arguments("box", "descr", "box")
    def opimpl_getarrayitem_gc(self, arraybox, arraydesc, indexbox):
        self.execute_with_descr(rop.GETARRAYITEM_GC, arraydesc, arraybox, indexbox)

    @arguments("box", "descr", "box")
    def opimpl_getarrayitem_gc_pure(self, arraybox, arraydesc, indexbox):
        self.execute_with_descr(rop.GETARRAYITEM_GC_PURE, arraydesc, arraybox, indexbox)

    @arguments("box", "descr", "box", "box")
    def opimpl_setarrayitem_gc(self, arraybox, arraydesc, indexbox, itembox):
        self.execute_with_descr(rop.SETARRAYITEM_GC, arraydesc, arraybox, indexbox, itembox)

    @arguments("box", "descr")
    def opimpl_arraylen_gc(self, arraybox, arraydesc):
        self.execute_with_descr(rop.ARRAYLEN_GC, arraydesc, arraybox)

    @arguments("orgpc", "box", "descr", "box")
    def opimpl_check_neg_index(self, pc, arraybox, arraydesc, indexbox):
        negbox = self.metainterp.execute_and_record(
            rop.INT_LT, None, indexbox, ConstInt(0))
        negbox = self.implement_guard_value(pc, negbox)
        if negbox.getint():
            # the index is < 0; add the array length to it
            lenbox = self.metainterp.execute_and_record(
                rop.ARRAYLEN_GC, arraydesc, arraybox)
            indexbox = self.metainterp.execute_and_record(
                rop.INT_ADD, None, indexbox, lenbox)
        self.make_result_box(indexbox)

    @arguments("descr", "descr", "descr", "descr", "box")
    def opimpl_newlist(self, structdescr, lengthdescr, itemsdescr, arraydescr,
                       sizebox):
        sbox = self.metainterp.execute_and_record(rop.NEW, structdescr)
        self.metainterp.execute_and_record(rop.SETFIELD_GC, lengthdescr, 
                                           sbox, sizebox)
        abox = self.metainterp.execute_and_record(rop.NEW_ARRAY, arraydescr,
                                                  sizebox)
        self.metainterp.execute_and_record(rop.SETFIELD_GC, itemsdescr,
                                           sbox, abox)
        self.make_result_box(sbox)

    @arguments("box", "descr", "descr", "box")
    def opimpl_getlistitem_gc(self, listbox, itemsdescr, arraydescr, indexbox):
        arraybox = self.metainterp.execute_and_record(rop.GETFIELD_GC,
                                                      itemsdescr, listbox)
        self.execute_with_descr(rop.GETARRAYITEM_GC, arraydescr, arraybox, indexbox)

    @arguments("box", "descr", "descr", "box", "box")
    def opimpl_setlistitem_gc(self, listbox, itemsdescr, arraydescr, indexbox,
                              valuebox):
        arraybox = self.metainterp.execute_and_record(rop.GETFIELD_GC,
                                                      itemsdescr, listbox)
        self.execute_with_descr(rop.SETARRAYITEM_GC, arraydescr, arraybox, indexbox, valuebox)

    @arguments("orgpc", "box", "descr", "box")
    def opimpl_check_resizable_neg_index(self, pc, listbox, lengthdesc,
                                         indexbox):
        negbox = self.metainterp.execute_and_record(
            rop.INT_LT, None, indexbox, ConstInt(0))
        negbox = self.implement_guard_value(pc, negbox)
        if negbox.getint():
            # the index is < 0; add the array length to it
            lenbox = self.metainterp.execute_and_record(
                rop.GETFIELD_GC, lengthdesc, listbox)
            indexbox = self.metainterp.execute_and_record(
                rop.INT_ADD, None, indexbox, lenbox)
        self.make_result_box(indexbox)

    @arguments("orgpc", "box")
    def opimpl_check_zerodivisionerror(self, pc, box):
        nonzerobox = self.metainterp.execute_and_record(
            rop.INT_NE, None, box, ConstInt(0))
        nonzerobox = self.implement_guard_value(pc, nonzerobox)
        if nonzerobox.getint():
            return False
        else:
            # division by zero!
            return self.metainterp.raise_zero_division_error()

    @arguments("orgpc", "box", "box")
    def opimpl_check_div_overflow(self, pc, box1, box2):
        # detect the combination "box1 = -sys.maxint-1, box2 = -1".
        import sys
        tmp1 = self.metainterp.execute_and_record(    # combination to detect:
            rop.INT_ADD, None, box1, ConstInt(sys.maxint))    # tmp1=-1, box2=-1
        tmp2 = self.metainterp.execute_and_record(
            rop.INT_AND, None, tmp1, box2)                    # tmp2=-1
        tmp3 = self.metainterp.execute_and_record(
            rop.INT_EQ, None, tmp2, ConstInt(-1))             # tmp3?
        tmp4 = self.implement_guard_value(pc, tmp3)       # tmp4?
        if not tmp4.getint():
            return False
        else:
            # division overflow!
            return self.metainterp.raise_overflow_error()

    @arguments()
    def opimpl_overflow_error(self):
        return self.metainterp.raise_overflow_error()

    @arguments("orgpc", "box")
    def opimpl_int_abs(self, pc, box):
        nonneg = self.metainterp.execute_and_record(
            rop.INT_GE, None, box, ConstInt(0))
        nonneg = self.implement_guard_value(pc, nonneg)
        if nonneg.getint():
            self.make_result_box(box)
        else:
            self.execute(rop.INT_NEG, box)

    @arguments("orgpc", "box")
    def opimpl_oononnull(self, pc, box):
        value = box.nonnull()
        if value:
            opnum = rop.GUARD_NONNULL
            res = ConstInt(1)
        else:
            opnum = rop.GUARD_ISNULL
            res = ConstInt(0)
        self.generate_guard(pc, opnum, box, [])
        self.make_result_box(res)

    @arguments("orgpc", "box")
    def opimpl_ooisnull(self, pc, box):
        value = box.nonnull()
        if value:
            opnum = rop.GUARD_NONNULL
            res = ConstInt(0)
        else:
            opnum = rop.GUARD_ISNULL
            res = ConstInt(1)
        self.generate_guard(pc, opnum, box, [])
        self.make_result_box(res)

    @arguments("box", "box")
    def opimpl_ptr_eq(self, box1, box2):
        self.execute(rop.OOIS, box1, box2)

    @arguments("box", "box")
    def opimpl_ptr_ne(self, box1, box2):
        self.execute(rop.OOISNOT, box1, box2)

    opimpl_oois = opimpl_ptr_eq
    opimpl_ooisnot = opimpl_ptr_ne

    @arguments("box", "descr")
    def opimpl_getfield_gc(self, box, fielddesc):
        self.execute_with_descr(rop.GETFIELD_GC, fielddesc, box)
    @arguments("box", "descr")
    def opimpl_getfield_gc_pure(self, box, fielddesc):
        self.execute_with_descr(rop.GETFIELD_GC_PURE, fielddesc, box)
    @arguments("box", "descr", "box")
    def opimpl_setfield_gc(self, box, fielddesc, valuebox):
        self.execute_with_descr(rop.SETFIELD_GC, fielddesc, box, valuebox)

    @arguments("box", "descr")
    def opimpl_getfield_raw(self, box, fielddesc):
        self.execute_with_descr(rop.GETFIELD_RAW, fielddesc, box)
    @arguments("box", "descr")
    def opimpl_getfield_raw_pure(self, box, fielddesc):
        self.execute_with_descr(rop.GETFIELD_RAW_PURE, fielddesc, box)
    @arguments("box", "descr", "box")
    def opimpl_setfield_raw(self, box, fielddesc, valuebox):
        self.execute_with_descr(rop.SETFIELD_RAW, fielddesc, box, valuebox)

    def _nonstandard_virtualizable(self, pc, box):
        # returns True if 'box' is actually not the "standard" virtualizable
        # that is stored in metainterp.virtualizable_boxes[-1]
        standard_box = self.metainterp.virtualizable_boxes[-1]
        if standard_box is box:
            return False
        eqbox = self.metainterp.execute_and_record(rop.OOIS, None,
                                                   box, standard_box)
        eqbox = self.implement_guard_value(pc, eqbox)
        isstandard = eqbox.getint()
        if isstandard:
            self.metainterp.replace_box(box, standard_box)
        return not isstandard

    def _get_virtualizable_field_descr(self, index):
        vinfo = self.metainterp.staticdata.virtualizable_info
        return vinfo.static_field_descrs[index]

    def _get_virtualizable_array_field_descr(self, index):
        vinfo = self.metainterp.staticdata.virtualizable_info
        return vinfo.array_field_descrs[index]

    def _get_virtualizable_array_descr(self, index):
        vinfo = self.metainterp.staticdata.virtualizable_info
        return vinfo.array_descrs[index]

    @arguments("orgpc", "box", "int")
    def opimpl_getfield_vable(self, pc, basebox, index):
        if self._nonstandard_virtualizable(pc, basebox):
            self.execute_with_descr(rop.GETFIELD_GC, self._get_virtualizable_field_descr(index), basebox)
            return
        self.metainterp.check_synchronized_virtualizable()
        resbox = self.metainterp.virtualizable_boxes[index]
        self.make_result_box(resbox)
    @arguments("orgpc", "box", "int", "box")
    def opimpl_setfield_vable(self, pc, basebox, index, valuebox):
        if self._nonstandard_virtualizable(pc, basebox):
            self.execute_with_descr(rop.SETFIELD_GC, self._get_virtualizable_field_descr(index), basebox, valuebox)
            return
        self.metainterp.virtualizable_boxes[index] = valuebox
        self.metainterp.synchronize_virtualizable()
        # XXX only the index'th field needs to be synchronized, really

    def _get_arrayitem_vable_index(self, pc, arrayindex, indexbox):
        indexbox = self.implement_guard_value(pc, indexbox)
        vinfo = self.metainterp.staticdata.virtualizable_info
        virtualizable_box = self.metainterp.virtualizable_boxes[-1]
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
        index = indexbox.getint()
        if index < 0:
            index += vinfo.get_array_length(virtualizable, arrayindex)
        assert 0 <= index < vinfo.get_array_length(virtualizable, arrayindex)
        return vinfo.get_index_in_array(virtualizable, arrayindex, index)

    @arguments("orgpc", "box", "int", "box")
    def opimpl_getarrayitem_vable(self, pc, basebox, arrayindex, indexbox):
        if self._nonstandard_virtualizable(pc, basebox):
            descr = self._get_virtualizable_array_field_descr(arrayindex)
            arraybox = self.metainterp.execute_and_record(rop.GETFIELD_GC,
                                                          descr, basebox)
            descr = self._get_virtualizable_array_descr(arrayindex)
            self.execute_with_descr(rop.GETARRAYITEM_GC, descr,
                                    arraybox, indexbox)
            return
        self.metainterp.check_synchronized_virtualizable()
        index = self._get_arrayitem_vable_index(pc, arrayindex, indexbox)
        resbox = self.metainterp.virtualizable_boxes[index]
        self.make_result_box(resbox)
    @arguments("orgpc", "box", "int", "box", "box")
    def opimpl_setarrayitem_vable(self, pc, basebox, arrayindex, indexbox,
                                  valuebox):
        if self._nonstandard_virtualizable(pc, basebox):
            descr = self._get_virtualizable_array_field_descr(arrayindex)
            arraybox = self.metainterp.execute_and_record(rop.GETFIELD_GC,
                                                          descr, basebox)
            descr = self._get_virtualizable_array_descr(arrayindex)
            self.execute_with_descr(rop.SETARRAYITEM_GC, descr,
                                    arraybox, indexbox, valuebox)
            return
        index = self._get_arrayitem_vable_index(pc, arrayindex, indexbox)
        self.metainterp.virtualizable_boxes[index] = valuebox
        self.metainterp.synchronize_virtualizable()
        # XXX only the index'th field needs to be synchronized, really
    @arguments("orgpc", "box", "int")
    def opimpl_arraylen_vable(self, pc, basebox, arrayindex):
        if self._nonstandard_virtualizable(pc, basebox):
            descr = self._get_virtualizable_array_field_descr(arrayindex)
            arraybox = self.metainterp.execute_and_record(rop.GETFIELD_GC,
                                                          descr, basebox)
            descr = self._get_virtualizable_array_descr(arrayindex)
            self.execute_with_descr(rop.ARRAYLEN_GC, descr, arraybox)
            return
        vinfo = self.metainterp.staticdata.virtualizable_info
        virtualizable_box = self.metainterp.virtualizable_boxes[-1]
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
        result = vinfo.get_array_length(virtualizable, arrayindex)
        self.make_result_box(ConstInt(result))

    def perform_call(self, jitcode, varargs, greenkey=None):
        if (self.metainterp.is_blackholing() and
            jitcode.calldescr is not None):
            # when producing only a BlackHole, we can implement this by
            # calling the subfunction directly instead of interpreting it
            if jitcode.cfnptr is not None:
                # for non-oosends
                varargs = [jitcode.cfnptr] + varargs
                res = self.execute_varargs(rop.CALL, varargs,
                                             descr=jitcode.calldescr, exc=True)
            else:
                # for oosends (ootype only): calldescr is a MethDescr
                res = self.execute_varargs(rop.OOSEND, varargs,
                                             descr=jitcode.calldescr, exc=True)
            self.metainterp.load_fields_from_virtualizable()
            return res
        else:
            # when tracing, this bytecode causes the subfunction to be entered
            f = self.metainterp.newframe(jitcode, greenkey)
            f.setup_call(varargs)
            return True

    @arguments("bytecode", "varargs")
    def opimpl_call(self, callee, varargs):
        return self.perform_call(callee, varargs)

    @arguments("descr", "varargs")
    def opimpl_residual_call(self, calldescr, varargs):
        return self.do_residual_call(varargs, descr=calldescr, exc=True)

    @arguments("descr", "varargs")
    def opimpl_residual_call_loopinvariant(self, calldescr, varargs):
        return self.execute_varargs(rop.CALL_LOOPINVARIANT, varargs, calldescr, exc=True)

    @arguments("varargs")
    def opimpl_recursion_leave_prep(self, varargs):
        warmrunnerstate = self.metainterp.staticdata.state
        if warmrunnerstate.inlining:
            num_green_args = self.metainterp.staticdata.num_green_args
            greenkey = varargs[:num_green_args]
            if warmrunnerstate.can_inline_callable(greenkey):
                return False
        leave_code = self.metainterp.staticdata.leave_code
        if leave_code is None:
            return False
        return self.perform_call(leave_code, varargs)
        
    @arguments("orgpc", "descr", "varargs")
    def opimpl_recursive_call(self, pc, calldescr, varargs):
        warmrunnerstate = self.metainterp.staticdata.state
        token = None
        if not self.metainterp.is_blackholing() and warmrunnerstate.inlining:
            num_green_args = self.metainterp.staticdata.num_green_args
            portal_code = self.metainterp.staticdata.portal_code
            greenkey = varargs[1:num_green_args + 1]
            if warmrunnerstate.can_inline_callable(greenkey):
                return self.perform_call(portal_code, varargs[1:], greenkey)
            token = warmrunnerstate.get_assembler_token(greenkey)
        call_position = 0
        if token is not None:
            call_position = len(self.metainterp.history.operations)
            # verify that we have all green args, needed to make sure
            # that assembler that we call is still correct
            greenargs = varargs[1:num_green_args + 1]
            self.verify_green_args(greenargs)
        res = self.do_residual_call(varargs, descr=calldescr, exc=True)
        if not self.metainterp.is_blackholing() and token is not None:
            # XXX fix the call position, <UGLY!>
            found = False
            while True:
                op = self.metainterp.history.operations[call_position]
                if op.opnum == rop.CALL or op.opnum == rop.CALL_MAY_FORCE:
                    found = True
                    break
                call_position += 1
            assert found
            # </UGLY!>
            # this will substitute the residual call with assembler call
            self.metainterp.direct_assembler_call(pc, varargs, token,
                                                  call_position)
        return res

    @arguments("descr", "varargs")
    def opimpl_residual_call_noexception(self, calldescr, varargs):
        self.do_residual_call(varargs, descr=calldescr, exc=False)

    @arguments("descr", "varargs")
    def opimpl_residual_call_pure(self, calldescr, varargs):
        self.execute_varargs(rop.CALL_PURE, varargs, descr=calldescr, exc=False)

    @arguments("orgpc", "descr", "box", "varargs")
    def opimpl_indirect_call(self, pc, calldescr, box, varargs):
        box = self.implement_guard_value(pc, box)
        cpu = self.metainterp.cpu
        key = cpu.ts.getaddr_for_box(cpu, box)
        jitcode = self.metainterp.staticdata.bytecode_for_address(key)
        if jitcode is not None:
            # we should follow calls to this graph
            return self.perform_call(jitcode, varargs)
        else:
            # but we should not follow calls to that graph
            return self.do_residual_call([box] + varargs,
                                         descr=calldescr, exc=True)

    @arguments("orgpc", "methdescr", "varargs")
    def opimpl_oosend(self, pc, methdescr, varargs):
        objbox = varargs[0]
        clsbox = self.cls_of_box(objbox)
        if isinstance(objbox, Box):
            self.generate_guard(pc, rop.GUARD_CLASS, objbox, [clsbox])
        oocls = clsbox.getref(ootype.Class)
        jitcode = methdescr.get_jitcode_for_class(oocls)
        if jitcode is not None:
            # we should follow calls to this graph
            return self.perform_call(jitcode, varargs)
        else:
            # but we should not follow calls to that graph
            return self.execute_varargs(rop.OOSEND, varargs,
                                        descr=methdescr, exc=True)

    @arguments("box")
    def opimpl_strlen(self, str):
        self.execute(rop.STRLEN, str)

    @arguments("box")
    def opimpl_unicodelen(self, str):
        self.execute(rop.UNICODELEN, str)

    @arguments("box", "box")
    def opimpl_strgetitem(self, str, index):
        self.execute(rop.STRGETITEM, str, index)

    @arguments("box", "box")
    def opimpl_unicodegetitem(self, str, index):
        self.execute(rop.UNICODEGETITEM, str, index)

    @arguments("box", "box", "box")
    def opimpl_strsetitem(self, str, index, newchar):
        self.execute(rop.STRSETITEM, str, index, newchar)

    @arguments("box", "box", "box")
    def opimpl_unicodesetitem(self, str, index, newchar):
        self.execute(rop.UNICODESETITEM, str, index, newchar)

    @arguments("box")
    def opimpl_newstr(self, length):
        self.execute(rop.NEWSTR, length)

    @arguments("box")
    def opimpl_newunicode(self, length):
        self.execute(rop.NEWUNICODE, length)

    @arguments("descr", "varargs")
    def opimpl_residual_oosend_canraise(self, methdescr, varargs):
        return self.execute_varargs(rop.OOSEND, varargs, descr=methdescr, exc=True)

    @arguments("descr", "varargs")
    def opimpl_residual_oosend_noraise(self, methdescr, varargs):
        self.execute_varargs(rop.OOSEND, varargs, descr=methdescr, exc=False)

    @arguments("descr", "varargs")
    def opimpl_residual_oosend_pure(self, methdescr, boxes):
        self.execute_varargs(rop.OOSEND_PURE, boxes, descr=methdescr, exc=False)

    @arguments("orgpc", "box")
    def opimpl_guard_value(self, pc, box):
        constbox = self.implement_guard_value(pc, box)
        self.make_result_box(constbox)

    @arguments("orgpc", "int")
    def opimpl_guard_green(self, pc, boxindex):
        """Like guard_value, but overwrites the original box with the const.
        Used to prevent Boxes from showing up in the greenkey of some
        operations, like jit_merge_point.  The in-place overwriting is
        convenient for jit_merge_point, which expects self.env to contain
        not more than the greens+reds described in the jitdriver."""
        box = self.env[boxindex]
        constbox = self.implement_guard_value(pc, box)
        self.env[boxindex] = constbox

    @arguments("orgpc", "box")
    def opimpl_guard_class(self, pc, box):
        clsbox = self.cls_of_box(box)
        if isinstance(box, Box):
            self.generate_guard(pc, rop.GUARD_CLASS, box, [clsbox])
        self.make_result_box(clsbox)

##    @arguments("orgpc", "box", "builtin")
##    def opimpl_guard_builtin(self, pc, box, builtin):
##        self.generate_guard(pc, "guard_builtin", box, [builtin])

##    @arguments("orgpc", "box", "builtin")
##    def opimpl_guard_len(self, pc, box, builtin):
##        intbox = self.metainterp.cpu.execute_operation(
##            'len', [builtin.len_func, box], 'int')
##        self.generate_guard(pc, "guard_len", box, [intbox])

    @arguments("box")
    def opimpl_keepalive(self, box):
        pass     # xxx?

    def verify_green_args(self, varargs):
        num_green_args = self.metainterp.staticdata.num_green_args
        for i in range(num_green_args):
            assert isinstance(varargs[i], Const)

    def blackhole_reached_merge_point(self, varargs):
        if self.metainterp.in_recursion:
            portal_code = self.metainterp.staticdata.portal_code
            # small hack: fish for the result box
            lenenv = len(self.env)
            raised = self.perform_call(portal_code, varargs)
            # in general this cannot be assumed, but when blackholing,
            # perform_call returns True only if an exception is called. In
            # this case perform_call has called finishframe_exception
            # already, so we need to return.
            if raised:
                return
            if lenenv == len(self.env):
                res = None
            else:
                assert lenenv == len(self.env) - 1
                res = self.env.pop()
            self.metainterp.finishframe(res)
        else:
            raise self.metainterp.staticdata.ContinueRunningNormally(varargs)

    @arguments()
    def opimpl_can_enter_jit(self):
        # Note: when running with a BlackHole history, this 'can_enter_jit'
        # may be completely skipped by the logic that replaces perform_call
        # with rop.CALL.  But in that case, no-one will check the flag anyway,
        # so it's fine.
        if self.metainterp.in_recursion:
            from pypy.jit.metainterp.warmspot import CannotInlineCanEnterJit
            raise CannotInlineCanEnterJit()
        self.metainterp.seen_can_enter_jit = True

    @arguments()
    def opimpl_jit_merge_point(self):
        if not self.metainterp.is_blackholing():
            self.verify_green_args(self.env)
            # xxx we may disable the following line in some context later
            self.debug_merge_point()
            if self.metainterp.seen_can_enter_jit:
                self.metainterp.seen_can_enter_jit = False
                try:
                    self.metainterp.reached_can_enter_jit(self.env)
                except GiveUp:
                    self.metainterp.switch_to_blackhole(ABORT_BRIDGE)
        if self.metainterp.is_blackholing():
            self.blackhole_reached_merge_point(self.env)
        return True

    def debug_merge_point(self):
        # debugging: produce a DEBUG_MERGE_POINT operation
        num_green_args = self.metainterp.staticdata.num_green_args
        greenkey = self.env[:num_green_args]
        sd = self.metainterp.staticdata
        loc = sd.state.get_location_str(greenkey)
        debug_print(loc)
        constloc = self.metainterp.cpu.ts.conststr(loc)
        self.metainterp.history.record(rop.DEBUG_MERGE_POINT,
                                       [constloc], None)

    @arguments("jumptarget")
    def opimpl_setup_exception_block(self, exception_target):
        self.exception_target = exception_target

    @arguments()
    def opimpl_teardown_exception_block(self):
        self.exception_target = -1

    @arguments("constbox", "jumptarget", "orgpc")
    def opimpl_goto_if_exception_mismatch(self, vtableref, next_exc_target, pc):
        # XXX used to be:
        # assert isinstance(self.exception_box, Const)    # XXX
        # seems this can happen that self.exception_box is not a Const,
        # but I failed to write a test so far :-(
        self.exception_box = self.implement_guard_value(pc, self.exception_box)
        cpu = self.metainterp.cpu
        ts = self.metainterp.cpu.ts
        if not ts.subclassOf(cpu, self.exception_box, vtableref):
            self.pc = next_exc_target

    @arguments("int")
    def opimpl_put_last_exception(self, index):
        assert index >= 0
        self.env.insert(index, self.exception_box)

    @arguments("int")
    def opimpl_put_last_exc_value(self, index):
        assert index >= 0
        self.env.insert(index, self.exc_value_box)

    @arguments()
    def opimpl_raise(self):
        assert len(self.env) == 2
        return self.metainterp.finishframe_exception(self.env[0], self.env[1])

    @arguments()
    def opimpl_reraise(self):
        return self.metainterp.finishframe_exception(self.exception_box,
                                                     self.exc_value_box)

    @arguments("box")
    def opimpl_virtual_ref(self, box):
        # Details on the content of metainterp.virtualref_boxes:
        #
        #  * it's a list whose items go two by two, containing first the
        #    virtual box (e.g. the PyFrame) and then the vref box (e.g.
        #    the 'virtual_ref(frame)').
        #
        #  * if we detect that the virtual box escapes during tracing
        #    already (by generating a CALl_MAY_FORCE that marks the flags
        #    in the vref), then we replace the vref in the list with
        #    ConstPtr(NULL).
        #
        metainterp = self.metainterp
        if metainterp.is_blackholing():
            resbox = box      # good enough when blackholing
        else:
            vrefinfo = metainterp.staticdata.virtualref_info
            obj = box.getref_base()
            vref = vrefinfo.virtual_ref_during_tracing(obj)
            resbox = history.BoxPtr(vref)
            cindex = history.ConstInt(len(metainterp.virtualref_boxes) // 2)
            metainterp.history.record(rop.VIRTUAL_REF, [box, cindex], resbox)
            # Note: we allocate a JIT_VIRTUAL_REF here
            # (in virtual_ref_during_tracing()), in order to detect when
            # the virtual escapes during tracing already.  We record it as a
            # VIRTUAL_REF operation, although the backend sees this operation
            # as a no-op.  The point is that the backend should not really see
            # it in practice, as optimizeopt.py should either kill it or
            # replace it with a NEW_WITH_VTABLE followed by SETFIELD_GCs.
        metainterp.virtualref_boxes.append(box)
        metainterp.virtualref_boxes.append(resbox)
        self.make_result_box(resbox)

    @arguments("box")
    def opimpl_virtual_ref_finish(self, box):
        # virtual_ref_finish() assumes that we have a stack-like, last-in
        # first-out order.
        metainterp = self.metainterp
        vrefbox = metainterp.virtualref_boxes.pop()
        lastbox = metainterp.virtualref_boxes.pop()
        assert box.getref_base() == lastbox.getref_base()
        if not metainterp.is_blackholing():
            vrefinfo = metainterp.staticdata.virtualref_info
            vref = vrefbox.getref_base()
            if vrefinfo.is_virtual_ref(vref):
                metainterp.history.record(rop.VIRTUAL_REF_FINISH,
                                          [vrefbox, lastbox], None)

    # ------------------------------

    def setup_call(self, argboxes):
        if not we_are_translated():
            check_args(*argboxes)
        self.pc = 0
        self.env = argboxes

    def setup_resume_at_op(self, pc, exception_target, env):
        if not we_are_translated():
            check_args(*env)
        self.pc = pc
        self.exception_target = exception_target
        self.env = env
        ##  values = ' '.join([box.repr_rpython() for box in self.env])
        ##  log('setup_resume_at_op  %s:%d [%s] %d' % (self.jitcode.name,
        ##                                             self.pc, values,
        ##                                             self.exception_target))

    def run_one_step(self):
        # Execute the frame forward.  This method contains a loop that leaves
        # whenever the 'opcode_implementations' (which is one of the 'opimpl_'
        # methods) returns True.  This is the case when the current frame
        # changes, due to a call or a return.
        while True:
            pc = self.pc
            op = ord(self.bytecode[pc])
            #print self.metainterp.opcode_names[op]
            self.pc = pc + 1
            staticdata = self.metainterp.staticdata
            stop = staticdata.opcode_implementations[op](self, pc)
            #self.metainterp.most_recent_mp = None
            if stop:
                break

    def generate_guard(self, pc, opnum, box, extraargs=[]):
        if isinstance(box, Const):    # no need for a guard
            return
        metainterp = self.metainterp
        if metainterp.is_blackholing():
            return
        saved_pc = self.pc
        self.pc = pc
        if box is not None:
            moreargs = [box] + extraargs
        else:
            moreargs = list(extraargs)
        metainterp_sd = metainterp.staticdata
        original_greenkey = metainterp.resumekey.original_greenkey
        if opnum == rop.GUARD_NOT_FORCED:
            resumedescr = compile.ResumeGuardForcedDescr(metainterp_sd,
                                                         original_greenkey)
        else:
            resumedescr = compile.ResumeGuardDescr(metainterp_sd,
                                                   original_greenkey)
        guard_op = metainterp.history.record(opnum, moreargs, None,
                                             descr=resumedescr)       
        virtualizable_boxes = None
        if metainterp.staticdata.virtualizable_info is not None:
            virtualizable_boxes = metainterp.virtualizable_boxes
        resume.capture_resumedata(metainterp.framestack, virtualizable_boxes,
                                  metainterp.virtualref_boxes, resumedescr)
        self.metainterp.staticdata.profiler.count_ops(opnum, GUARDS)
        # count
        metainterp.attach_debug_info(guard_op)
        self.pc = saved_pc
        return guard_op

    def implement_guard_value(self, pc, box):
        """Promote the given Box into a Const.  Note: be careful, it's a
        bit unclear what occurs if a single opcode needs to generate
        several ones and/or ones not near the beginning."""
        if isinstance(box, Const):
            return box     # no promotion needed, already a Const
        else:
            promoted_box = box.constbox()
            self.generate_guard(pc, rop.GUARD_VALUE, box, [promoted_box])
            self.metainterp.replace_box(box, promoted_box)
            return promoted_box

    def cls_of_box(self, box):
        return self.metainterp.cpu.ts.cls_of_box(self.metainterp.cpu, box)

    @specialize.arg(1)
    def execute(self, opnum, *argboxes):
        self.execute_with_descr(opnum, None, *argboxes)

    @specialize.arg(1)
    def execute_with_descr(self, opnum, descr, *argboxes):
        resbox = self.metainterp.execute_and_record(opnum, descr, *argboxes)
        if resbox is not None:
            self.make_result_box(resbox)

    @specialize.arg(1)
    def execute_varargs(self, opnum, argboxes, descr, exc):
        resbox = self.metainterp.execute_and_record_varargs(opnum, argboxes,
                                                            descr=descr)
        if resbox is not None:
            self.make_result_box(resbox)
        if exc:
            return self.metainterp.handle_exception()
        else:
            return self.metainterp.assert_no_exception()

    def do_residual_call(self, argboxes, descr, exc):
        effectinfo = descr.get_extra_info()
        if effectinfo is None or effectinfo.forces_virtual_or_virtualizable:
            # residual calls require attention to keep virtualizables in-sync
            self.metainterp.vable_and_vrefs_before_residual_call()
            # xxx do something about code duplication
            resbox = self.metainterp.execute_and_record_varargs(
                rop.CALL_MAY_FORCE, argboxes, descr=descr)
            self.metainterp.vable_and_vrefs_after_residual_call()
            if resbox is not None:
                self.make_result_box(resbox)
            self.generate_guard(self.pc, rop.GUARD_NOT_FORCED, None, [])
            if exc:
                return self.metainterp.handle_exception()
            else:
                return self.metainterp.assert_no_exception()
        else:
            return self.execute_varargs(rop.CALL, argboxes, descr, exc)

# ____________________________________________________________

class MetaInterpStaticData(object):
    virtualizable_info = None
    logger_noopt = None
    logger_ops = None

    def __init__(self, portal_graph, cpu, stats, options,
                 ProfilerClass=EmptyProfiler, warmrunnerdesc=None):
        self.cpu = cpu
        self.stats = stats
        self.options = options
        self.logger_noopt = Logger(self)
        self.logger_ops = Logger(self, guard_number=True)

        RESULT = portal_graph.getreturnvar().concretetype
        self.result_type = history.getkind(RESULT)

        self.opcode_implementations = []
        self.opcode_names = []
        self.opname_to_index = {}

        self.profiler = ProfilerClass()

        self.indirectcall_keys = []
        self.indirectcall_values = []

        self.warmrunnerdesc = warmrunnerdesc
        self._op_goto_if_not = self.find_opcode('goto_if_not')
        self._op_ooisnull    = self.find_opcode('ooisnull')
        self._op_oononnull   = self.find_opcode('oononnull')

        backendmodule = self.cpu.__module__
        backendmodule = backendmodule.split('.')[-2]
        self.jit_starting_line = 'JIT starting (%s)' % backendmodule

        self.portal_code = None
        self.leave_code = None
        self._class_sizes = None
        self._addr2name_keys = []
        self._addr2name_values = []

        self.__dict__.update(compile.make_done_loop_tokens())
        # store this information for fastpath of call_assembler
        d = self.loop_tokens_done_with_this_frame_int[0].finishdescr
        self.cpu.done_with_this_frame_int_v = self.cpu.get_fail_descr_number(d)

    def _freeze_(self):
        return True

    def info_from_codewriter(self, portal_code, leave_code, class_sizes,
                             list_of_addr2name, portal_runner_ptr):
        self.portal_code = portal_code
        self.leave_code = leave_code
        self._class_sizes = class_sizes
        self._addr2name_keys   = [key   for key, value in list_of_addr2name]
        self._addr2name_values = [value for key, value in list_of_addr2name]
        self._portal_runner_ptr = portal_runner_ptr

    def finish_setup(self, optimizer=None):
        warmrunnerdesc = self.warmrunnerdesc
        if warmrunnerdesc is not None:
            self.num_green_args = warmrunnerdesc.num_green_args
            self.state = warmrunnerdesc.state
            if optimizer is not None:
                self.state.set_param_optimizer(optimizer)
        else:
            self.num_green_args = 0
            self.state = None
        self.globaldata = MetaInterpGlobalData(self)

    def _setup_once(self):
        """Runtime setup needed by the various components of the JIT."""
        if not self.globaldata.initialized:
            debug_print(self.jit_starting_line)
            self._setup_class_sizes()
            self.cpu.setup_once()
            if not self.profiler.initialized:
                self.profiler.start()
                self.profiler.initialized = True
            self.globaldata.initialized = True

    def _setup_class_sizes(self):
        class_sizes = {}
        for vtable, sizedescr in self._class_sizes:
            vtable = self.cpu.ts.cast_vtable_to_hashable(self.cpu, vtable)
            class_sizes[vtable] = sizedescr
        self.cpu.set_class_sizes(class_sizes)

    def get_name_from_address(self, addr):
        # for debugging only
        if we_are_translated():
            d = self.globaldata.addr2name
            if d is None:
                # Build the dictionary at run-time.  This is needed
                # because the keys are function/class addresses, so they
                # can change from run to run.
                k = llmemory.cast_ptr_to_adr(self._portal_runner_ptr)
                d = {k: 'recursive call'}
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
                keys = self.indirectcall_keys
                values = self.indirectcall_values
                for i in range(len(keys)):
                    d[keys[i]] = values[i]
                self.globaldata.indirectcall_dict = d
            return d.get(fnaddress, None)
        else:
            for i in range(len(self.indirectcall_keys)):
                if fnaddress == self.indirectcall_keys[i]:
                    return self.indirectcall_values[i]
            return None

    # ---------- construction-time interface ----------

    def _register_indirect_call_target(self, fnaddress, jitcode):
        self.indirectcall_keys.append(fnaddress)
        self.indirectcall_values.append(jitcode)

    def find_opcode(self, name):
        try:
            return self.opname_to_index[name]
        except KeyError:
            self._register_opcode(name)
            return self.opname_to_index[name]

    def _register_opcode(self, opname):
        assert len(self.opcode_implementations) < 256, \
               "too many implementations of opcodes!"
        name = "opimpl_" + opname
        self.opname_to_index[opname] = len(self.opcode_implementations)
        self.opcode_names.append(opname)
        self.opcode_implementations.append(getattr(MIFrame, name).im_func)

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
        self.resume_virtuals = {}
        #
        state = staticdata.state
        if state is not None:
            self.jit_cell_at_key = state.jit_cell_at_key
        else:
            # for tests only; not RPython
            class JitCell:
                compiled_merge_points = None
            _jitcell_dict = {}
            def jit_cell_at_key(greenkey):
                greenkey = tuple(greenkey)
                return _jitcell_dict.setdefault(greenkey, JitCell())
            self.jit_cell_at_key = jit_cell_at_key

    def get_compiled_merge_points(self, greenkey):
        cell = self.jit_cell_at_key(greenkey)
        if cell.compiled_merge_points is None:
            cell.compiled_merge_points = []
        return cell.compiled_merge_points

# ____________________________________________________________

class MetaInterp(object):
    in_recursion = 0
    _already_allocated_resume_virtuals = None

    def __init__(self, staticdata):
        self.staticdata = staticdata
        self.cpu = staticdata.cpu
        self.portal_trace_positions = []
        self.greenkey_of_huge_function = None

    def is_blackholing(self):
        return self.history is None

    def newframe(self, jitcode, greenkey=None):
        if jitcode is self.staticdata.portal_code:
            self.in_recursion += 1
        if greenkey is not None and not self.is_blackholing():
            self.portal_trace_positions.append(
                    (greenkey, len(self.history.operations)))
        f = MIFrame(self, jitcode, greenkey)
        self.framestack.append(f)
        return f

    def popframe(self):
        frame = self.framestack.pop()
        if frame.jitcode is self.staticdata.portal_code:
            self.in_recursion -= 1
        if frame.greenkey is not None and not self.is_blackholing():
            self.portal_trace_positions.append(
                    (None, len(self.history.operations)))
        return frame

    def finishframe(self, resultbox):
        frame = self.popframe()
        if self.framestack:
            if resultbox is not None:
                self.framestack[-1].make_result_box(resultbox)
            return True
        else:
            if not self.is_blackholing():
                try:
                    self.compile_done_with_this_frame(resultbox)
                except GiveUp:
                    self.switch_to_blackhole(ABORT_BRIDGE)
            sd = self.staticdata
            if sd.result_type == 'void':
                assert resultbox is None
                raise sd.DoneWithThisFrameVoid()
            elif sd.result_type == 'int':
                raise sd.DoneWithThisFrameInt(resultbox.getint())
            elif sd.result_type == 'ref':
                raise sd.DoneWithThisFrameRef(self.cpu, resultbox.getref_base())
            elif sd.result_type == 'float':
                raise sd.DoneWithThisFrameFloat(resultbox.getfloat())
            else:
                assert False

    def finishframe_exception(self, exceptionbox, excvaluebox):
        # detect and propagate some exceptions early:
        #  - AssertionError
        #  - all subclasses of JitException
        if we_are_translated():
            from pypy.jit.metainterp.warmspot import JitException
            e = self.cpu.ts.get_exception_obj(excvaluebox)
            if isinstance(e, JitException) or isinstance(e, AssertionError):
                raise Exception, e
        #
        while self.framestack:
            frame = self.framestack[-1]
            if frame.exception_target >= 0:
                frame.pc = frame.exception_target
                frame.exception_target = -1
                frame.exception_box = exceptionbox
                frame.exc_value_box = excvaluebox
                return True
            self.popframe()
        if not self.is_blackholing():
            try:
                self.compile_exit_frame_with_exception(excvaluebox)
            except GiveUp:
                self.switch_to_blackhole(ABORT_BRIDGE)
        raise self.staticdata.ExitFrameWithExceptionRef(self.cpu, excvaluebox.getref_base())

    def check_recursion_invariant(self):
        in_recursion = -1
        for frame in self.framestack:
            jitcode = frame.jitcode
            if jitcode is self.staticdata.portal_code:
                in_recursion += 1
        if in_recursion != self.in_recursion:
            print "in_recursion problem!!!"
            print in_recursion, self.in_recursion
            for frame in self.framestack:
                jitcode = frame.jitcode
                if jitcode is self.staticdata.portal_code:
                    print "P",
                else:
                    print " ",
                print jitcode.name
            raise Exception

    def raise_overflow_error(self):
        etype, evalue = self.cpu.get_overflow_error()
        return self.finishframe_exception(
            self.cpu.ts.get_exception_box(etype),
            self.cpu.ts.get_exc_value_box(evalue))

    def raise_zero_division_error(self):
        etype, evalue = self.cpu.get_zero_division_error()
        return self.finishframe_exception(
            self.cpu.ts.get_exception_box(etype),
            self.cpu.ts.get_exc_value_box(evalue))

    def create_empty_history(self):
        warmrunnerstate = self.staticdata.state
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
        assert (opnum != rop.CALL and opnum != rop.CALL_MAY_FORCE
                and opnum != rop.OOSEND)
        # execute the operation
        profiler = self.staticdata.profiler
        profiler.count_ops(opnum)
        resbox = executor.execute(self.cpu, opnum, descr, *argboxes)
        if self.is_blackholing():
            profiler.count_ops(opnum, BLACKHOLED_OPS)            
            return resbox
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
        resbox = executor.execute_varargs(self.cpu, opnum, argboxes, descr)
        if self.is_blackholing():
            profiler.count_ops(opnum, BLACKHOLED_OPS)
        else:
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
        # record the operation
        profiler = self.staticdata.profiler
        profiler.count_ops(opnum, RECORDED_OPS)        
        op = self.history.record(opnum, argboxes, resbox, descr)
        self.attach_debug_info(op)
        return resbox

    def attach_debug_info(self, op):
        if (not we_are_translated() and op is not None
            and getattr(self, 'framestack', None)):
            op.pc = self.framestack[-1].pc
            op.name = self.framestack[-1].jitcode.name

    def switch_to_blackhole(self, reason):
        self.staticdata.profiler.count(reason)
        debug_print('~~~ ABORTING TRACING')
        debug_stop('jit-tracing')
        debug_start('jit-blackhole')
        self.history = None   # start blackholing
        self.staticdata.stats.aborted()
        self.staticdata.profiler.end_tracing()
        self.staticdata.profiler.start_blackhole()
    switch_to_blackhole._dont_inline_ = True

    def switch_to_blackhole_if_trace_too_long(self):
        if not self.is_blackholing():
            warmrunnerstate = self.staticdata.state
            if len(self.history.operations) > warmrunnerstate.trace_limit:
                self.greenkey_of_huge_function = self.find_biggest_function()
                self.portal_trace_positions = None
                self.switch_to_blackhole(ABORT_TOO_LONG)

    def _interpret(self):
        # Execute the frames forward until we raise a DoneWithThisFrame,
        # a ContinueRunningNormally, or a GenerateMergePoint exception.
        self.staticdata.stats.entered()
        try:
            while True:
                self.framestack[-1].run_one_step()
                self.switch_to_blackhole_if_trace_too_long()
                if not we_are_translated():
                    self.check_recursion_invariant()
        finally:
            if self.is_blackholing():
                self.staticdata.profiler.end_blackhole()
            else:
                self.staticdata.profiler.end_tracing()

    def interpret(self):
        if we_are_translated():
            self._interpret()
        else:
            try:
                self._interpret()
            except:
                import sys
                if sys.exc_info()[0] is not None:
                    codewriter.log.info(sys.exc_info()[0].__name__)
                raise

    def compile_and_run_once(self, *args):
        debug_start('jit-tracing')
        self.staticdata._setup_once()
        self.create_empty_history()
        try:
            return self._compile_and_run_once(*args)
        finally:
            if self.history is None:
                debug_stop('jit-blackhole')
            else:
                debug_stop('jit-tracing')

    def _compile_and_run_once(self, *args):
        original_boxes = self.initialize_state_from_start(*args)
        self.current_merge_points = [(original_boxes, 0)]
        num_green_args = self.staticdata.num_green_args
        original_greenkey = original_boxes[:num_green_args]
        redkey = original_boxes[num_green_args:]
        self.resumekey = compile.ResumeFromInterpDescr(original_greenkey,
                                                       redkey)
        self.seen_can_enter_jit = False
        try:
            self.interpret()
            assert False, "should always raise"
        except GenerateMergePoint, gmp:
            return self.designate_target_loop(gmp)

    def handle_guard_failure(self, key):
        assert isinstance(key, compile.ResumeGuardDescr)
        self.initialize_state_from_guard_failure(key)
        try:
            return self._handle_guard_failure(key)
        finally:
            if self.history is None:
                debug_stop('jit-blackhole')
            else:
                debug_stop('jit-tracing')

    def _handle_guard_failure(self, key):
        from pypy.jit.metainterp.warmspot import ContinueRunningNormallyBase
        original_greenkey = key.original_greenkey
        # notice that here we just put the greenkey
        # use -1 to mark that we will have to give up
        # because we cannot reconstruct the beginning of the proper loop
        self.current_merge_points = [(original_greenkey, -1)]
        self.resumekey = key
        self.seen_can_enter_jit = False
        started_as_blackhole = self.is_blackholing()
        try:
            self.prepare_resume_from_failure(key.guard_opnum)
            self.interpret()
            assert False, "should always raise"
        except GenerateMergePoint, gmp:
            return self.designate_target_loop(gmp)
        except ContinueRunningNormallyBase:
            if not started_as_blackhole:
                key.reset_counter_from_failure(self)
            raise

    def remove_consts_and_duplicates(self, boxes, startindex, endindex,
                                     duplicates):
        for i in range(startindex, endindex):
            box = boxes[i]
            if isinstance(box, Const) or box in duplicates:
                oldbox = box
                box = oldbox.clonebox()
                boxes[i] = box
                self.history.record(rop.SAME_AS, [oldbox], box)
            else:
                duplicates[box] = None

    def reached_can_enter_jit(self, live_arg_boxes):
        num_green_args = self.staticdata.num_green_args
        duplicates = {}
        self.remove_consts_and_duplicates(live_arg_boxes,
                                          num_green_args,
                                          len(live_arg_boxes),
                                          duplicates)
        live_arg_boxes = live_arg_boxes[:]
        if self.staticdata.virtualizable_info is not None:
            # we use ':-1' to remove the last item, which is the virtualizable
            # itself
            self.remove_consts_and_duplicates(self.virtualizable_boxes,
                                              0,
                                              len(self.virtualizable_boxes)-1,
                                              duplicates)
            live_arg_boxes += self.virtualizable_boxes[:-1]
        assert len(self.virtualref_boxes) == 0, "missing virtual_ref_finish()?"
        # Called whenever we reach the 'can_enter_jit' hint.
        # First, attempt to make a bridge:
        # - if self.resumekey is a ResumeGuardDescr, it starts from a guard
        #   that failed;
        # - if self.resumekey is a ResumeFromInterpDescr, it starts directly
        #   from the interpreter.
        self.compile_bridge(live_arg_boxes)
        # raises in case it works -- which is the common case, hopefully,
        # at least for bridges starting from a guard.

        # Search in current_merge_points for original_boxes with compatible
        # green keys, representing the beginning of the same loop as the one
        # we end now. 
       
        for j in range(len(self.current_merge_points)-1, -1, -1):
            original_boxes, start = self.current_merge_points[j]
            assert len(original_boxes) == len(live_arg_boxes) or start < 0
            for i in range(self.staticdata.num_green_args):
                box1 = original_boxes[i]
                box2 = live_arg_boxes[i]
                assert isinstance(box1, Const)
                if not box1.same_constant(box2):
                    break
            else:
                # Found!  Compile it as a loop.
                if start < 0:
                    # we cannot reconstruct the beginning of the proper loop
                    raise GiveUp

                # raises in case it works -- which is the common case
                self.compile(original_boxes, live_arg_boxes, start)
                # creation of the loop was cancelled!

        # Otherwise, no loop found so far, so continue tracing.
        start = len(self.history.operations)
        self.current_merge_points.append((live_arg_boxes, start))

    def designate_target_loop(self, gmp):
        loop_token = gmp.target_loop_token
        num_green_args = self.staticdata.num_green_args
        residual_args = self.get_residual_args(loop_token.specnodes,
                                               gmp.argboxes[num_green_args:])
        history.set_future_values(self.cpu, residual_args)
        return loop_token

    def prepare_resume_from_failure(self, opnum):
        if opnum == rop.GUARD_TRUE:     # a goto_if_not that jumps only now
            self.framestack[-1].follow_jump()
        elif opnum == rop.GUARD_FALSE:     # a goto_if_not that stops jumping
            self.framestack[-1].dont_follow_jump()
        elif (opnum == rop.GUARD_NO_EXCEPTION or opnum == rop.GUARD_EXCEPTION
              or opnum == rop.GUARD_NOT_FORCED):
            self.handle_exception()
        elif opnum == rop.GUARD_NO_OVERFLOW:   # an overflow now detected
            self.raise_overflow_error()
        elif opnum == rop.GUARD_NONNULL or opnum == rop.GUARD_ISNULL:
            self.framestack[-1].ignore_next_guard_nullness(opnum)

    def compile(self, original_boxes, live_arg_boxes, start):
        num_green_args = self.staticdata.num_green_args
        self.history.inputargs = original_boxes[num_green_args:]
        greenkey = original_boxes[:num_green_args]
        glob = self.staticdata.globaldata
        old_loop_tokens = glob.get_compiled_merge_points(greenkey)
        self.history.record(rop.JUMP, live_arg_boxes[num_green_args:], None)
        loop_token = compile.compile_new_loop(self, old_loop_tokens,
                                              greenkey, start)
        if loop_token is not None: # raise if it *worked* correctly
            raise GenerateMergePoint(live_arg_boxes, loop_token)
        self.history.operations.pop()     # remove the JUMP

    def compile_bridge(self, live_arg_boxes):
        num_green_args = self.staticdata.num_green_args
        greenkey = live_arg_boxes[:num_green_args]
        glob = self.staticdata.globaldata
        old_loop_tokens = glob.get_compiled_merge_points(greenkey)
        if len(old_loop_tokens) == 0:
            return
        self.history.record(rop.JUMP, live_arg_boxes[num_green_args:], None)
        target_loop_token = compile.compile_new_bridge(self, old_loop_tokens,
                                                       self.resumekey)
        if target_loop_token is not None:   # raise if it *worked* correctly
            raise GenerateMergePoint(live_arg_boxes, target_loop_token)
        self.history.operations.pop()     # remove the JUMP

    def compile_done_with_this_frame(self, exitbox):
        self.gen_store_back_in_virtualizable()
        # temporarily put a JUMP to a pseudo-loop
        sd = self.staticdata
        if sd.result_type == 'void':
            assert exitbox is None
            exits = []
            loop_tokens = sd.loop_tokens_done_with_this_frame_void
        elif sd.result_type == 'int':
            exits = [exitbox]
            loop_tokens = sd.loop_tokens_done_with_this_frame_int
        elif sd.result_type == 'ref':
            exits = [exitbox]
            loop_tokens = sd.loop_tokens_done_with_this_frame_ref
        elif sd.result_type == 'float':
            exits = [exitbox]
            loop_tokens = sd.loop_tokens_done_with_this_frame_float
        else:
            assert False
        self.history.record(rop.JUMP, exits, None)
        target_loop_token = compile.compile_new_bridge(self, loop_tokens,
                                                       self.resumekey)
        assert target_loop_token is loop_tokens[0]

    def compile_exit_frame_with_exception(self, valuebox):
        self.gen_store_back_in_virtualizable()
        # temporarily put a JUMP to a pseudo-loop
        self.history.record(rop.JUMP, [valuebox], None)
        sd = self.staticdata
        loop_tokens = sd.loop_tokens_exit_frame_with_exception_ref
        target_loop_token = compile.compile_new_bridge(self, loop_tokens,
                                                       self.resumekey)
        assert target_loop_token is loop_tokens[0]

    def get_residual_args(self, specnodes, args):
        if specnodes is None:     # it is None only for tests
            return args
        assert len(specnodes) == len(args)
        expanded_args = []
        for i in range(len(specnodes)):
            specnode = specnodes[i]
            specnode.extract_runtime_data(self.cpu, args[i], expanded_args)
        return expanded_args

    def _initialize_from_start(self, original_boxes, num_green_args, *args):
        if args:
            from pypy.jit.metainterp.warmstate import wrap
            box = wrap(self.cpu, args[0], num_green_args > 0)
            original_boxes.append(box)
            self._initialize_from_start(original_boxes, num_green_args-1,
                                        *args[1:])

    def initialize_state_from_start(self, *args):
        self.in_recursion = -1 # always one portal around
        self.staticdata.profiler.start_tracing()
        num_green_args = self.staticdata.num_green_args
        original_boxes = []
        self._initialize_from_start(original_boxes, num_green_args, *args)
        # ----- make a new frame -----
        self.framestack = []
        f = self.newframe(self.staticdata.portal_code)
        f.pc = 0
        f.env = original_boxes[:]
        self.virtualref_boxes = []
        self.initialize_virtualizable(original_boxes)
        return original_boxes

    def initialize_state_from_guard_failure(self, resumedescr):
        # guard failure: rebuild a complete MIFrame stack
        self.in_recursion = -1 # always one portal around
        inputargs_and_holes = self.cpu.make_boxes_from_latest_values(
                                                                 resumedescr)
        must_compile = resumedescr.must_compile(self.staticdata,
                                                inputargs_and_holes)
        if must_compile:
            debug_start('jit-tracing')
            self.history = history.History()
            self.history.inputargs = [box for box in inputargs_and_holes if box]
            self.staticdata.profiler.start_tracing()
        else:
            debug_start('jit-blackhole')
            self.staticdata.profiler.start_blackhole()
            self.history = None   # this means that is_blackholing() is true
        self.rebuild_state_after_failure(resumedescr, inputargs_and_holes)

    def initialize_virtualizable(self, original_boxes):
        vinfo = self.staticdata.virtualizable_info
        if vinfo is not None:
            virtualizable_box = original_boxes[vinfo.index_of_virtualizable]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            # The field 'virtualizable_boxes' is not even present
            # if 'virtualizable_info' is None.  Check for that first.
            self.virtualizable_boxes = vinfo.read_boxes(self.cpu,
                                                        virtualizable)
            original_boxes += self.virtualizable_boxes
            self.virtualizable_boxes.append(virtualizable_box)
            self.initialize_virtualizable_enter()

    def initialize_virtualizable_enter(self):
        vinfo = self.staticdata.virtualizable_info
        virtualizable_box = self.virtualizable_boxes[-1]
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
        vinfo.clear_vable_token(virtualizable)

    def vable_and_vrefs_before_residual_call(self):
        if self.is_blackholing():
            return
        #
        vrefinfo = self.staticdata.virtualref_info
        for i in range(1, len(self.virtualref_boxes), 2):
            vrefbox = self.virtualref_boxes[i]
            vref = vrefbox.getref_base()
            vrefinfo.tracing_before_residual_call(vref)
            # the FORCE_TOKEN is already set at runtime in each vref when
            # it is created, by optimizeopt.py.
        #
        vinfo = self.staticdata.virtualizable_info
        if vinfo is not None:
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            vinfo.tracing_before_residual_call(virtualizable)
            #
            force_token_box = history.BoxInt()
            self.history.record(rop.FORCE_TOKEN, [], force_token_box)
            self.history.record(rop.SETFIELD_GC, [virtualizable_box,
                                                  force_token_box],
                                None, descr=vinfo.vable_token_descr)

    def vable_and_vrefs_after_residual_call(self):
        if self.is_blackholing():
            escapes = True
        else:
            escapes = False
            #
            vrefinfo = self.staticdata.virtualref_info
            for i in range(0, len(self.virtualref_boxes), 2):
                virtualbox = self.virtualref_boxes[i]
                vrefbox = self.virtualref_boxes[i+1]
                vref = vrefbox.getref_base()
                if vrefinfo.tracing_after_residual_call(vref):
                    # this vref was really a virtual_ref, but it escaped
                    # during this CALL_MAY_FORCE.  Mark this fact by
                    # generating a VIRTUAL_REF_FINISH on it and replacing
                    # it by ConstPtr(NULL).
                    self.stop_tracking_virtualref(i)
            #
            vinfo = self.staticdata.virtualizable_info
            if vinfo is not None:
                virtualizable_box = self.virtualizable_boxes[-1]
                virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
                if vinfo.tracing_after_residual_call(virtualizable):
                    # the virtualizable escaped during CALL_MAY_FORCE.
                    escapes = True
            #
            if escapes:
                self.switch_to_blackhole(ABORT_ESCAPE)
        #
        if escapes:
            self.load_fields_from_virtualizable()

    def stop_tracking_virtualref(self, i):
        virtualbox = self.virtualref_boxes[i]
        vrefbox = self.virtualref_boxes[i+1]
        # record VIRTUAL_REF_FINISH just before the current CALL_MAY_FORCE
        call_may_force_op = self.history.operations.pop()
        assert call_may_force_op.opnum == rop.CALL_MAY_FORCE
        self.history.record(rop.VIRTUAL_REF_FINISH,
                            [vrefbox, virtualbox], None)
        self.history.operations.append(call_may_force_op)
        # mark by replacing it with ConstPtr(NULL)
        self.virtualref_boxes[i+1] = self.cpu.ts.CONST_NULL

    def handle_exception(self):
        etype = self.cpu.get_exception()
        evalue = self.cpu.get_exc_value()
        assert bool(etype) == bool(evalue)
        self.cpu.clear_exception()
        frame = self.framestack[-1]
        if etype:
            exception_box = self.cpu.ts.get_exception_box(etype)
            exc_value_box = self.cpu.ts.get_exc_value_box(evalue)
            op = frame.generate_guard(frame.pc, rop.GUARD_EXCEPTION,
                                      None, [exception_box])
            if op:
                op.result = exc_value_box
            return self.finishframe_exception(exception_box, exc_value_box)
        else:
            frame.generate_guard(frame.pc, rop.GUARD_NO_EXCEPTION, None, [])
            return False

    def assert_no_exception(self):
        assert not self.cpu.get_exception()
        return False

    def handle_overflow_error(self):
        frame = self.framestack[-1]
        if self.cpu._overflow_flag:
            self.cpu._overflow_flag = False
            frame.generate_guard(frame.pc, rop.GUARD_OVERFLOW, None, [])
            return self.raise_overflow_error()
        else:
            frame.generate_guard(frame.pc, rop.GUARD_NO_OVERFLOW, None, [])
            return False

    def rebuild_state_after_failure(self, resumedescr, newboxes):
        vinfo = self.staticdata.virtualizable_info
        self.framestack = []
        expect_virtualizable = vinfo is not None
        virtualizable_boxes, virtualref_boxes = resume.rebuild_from_resumedata(
            self, newboxes, resumedescr, expect_virtualizable)
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
        if expect_virtualizable:
            self.virtualizable_boxes = virtualizable_boxes
            if self._already_allocated_resume_virtuals is not None:
                # resuming from a ResumeGuardForcedDescr: load the new values
                # currently stored on the virtualizable fields
                self.load_fields_from_virtualizable()
                return
            # just jumped away from assembler (case 4 in the comment in
            # virtualizable.py) into tracing (case 2); check that vable_token
            # is and stays 0.  Note the call to reset_vable_token() in
            # warmstate.py.
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            assert not virtualizable.vable_token
            if self._already_allocated_resume_virtuals is not None:
                # resuming from a ResumeGuardForcedDescr: load the new values
                # currently stored on the virtualizable fields
                self.load_fields_from_virtualizable()
            else:
                # normal case: fill the virtualizable with the local boxes
                self.synchronize_virtualizable()

    def check_synchronized_virtualizable(self):
        if not we_are_translated():
            vinfo = self.staticdata.virtualizable_info
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            vinfo.check_boxes(virtualizable, self.virtualizable_boxes)

    def synchronize_virtualizable(self):
        vinfo = self.staticdata.virtualizable_info
        virtualizable_box = self.virtualizable_boxes[-1]
        virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
        vinfo.write_boxes(virtualizable, self.virtualizable_boxes)

    def load_fields_from_virtualizable(self):
        # Force a reload of the virtualizable fields into the local
        # boxes (called only in escaping cases)
        assert self.is_blackholing()
        vinfo = self.staticdata.virtualizable_info
        if vinfo is not None:
            virtualizable_box = self.virtualizable_boxes[-1]
            virtualizable = vinfo.unwrap_virtualizable_box(virtualizable_box)
            self.virtualizable_boxes = vinfo.read_boxes(self.cpu,
                                                        virtualizable)
            self.virtualizable_boxes.append(virtualizable_box)

    def gen_store_back_in_virtualizable(self):
        vinfo = self.staticdata.virtualizable_info
        if vinfo is not None:
            # xxx only write back the fields really modified
            vbox = self.virtualizable_boxes[-1]
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

    def gen_load_from_other_virtualizable(self, vbox):
        vinfo = self.staticdata.virtualizable_info
        boxes = []
        assert vinfo is not None
        for i in range(vinfo.num_static_extra_boxes):
            descr = vinfo.static_field_descrs[i]
            boxes.append(self.execute_and_record(rop.GETFIELD_GC, descr, vbox))
        virtualizable = vinfo.unwrap_virtualizable_box(vbox)
        for k in range(vinfo.num_arrays):
            descr = vinfo.array_field_descrs[k]
            abox = self.execute_and_record(rop.GETFIELD_GC, descr, vbox)
            descr = vinfo.array_descrs[k]
            for j in range(vinfo.get_array_length(virtualizable, k)):
                boxes.append(self.execute_and_record(rop.GETARRAYITEM_GC, descr,
                                                     abox, ConstInt(j)))
        return boxes

    def replace_box(self, oldbox, newbox):
        for frame in self.framestack:
            boxes = frame.env
            for i in range(len(boxes)):
                if boxes[i] is oldbox:
                    boxes[i] = newbox
        boxes = self.virtualref_boxes
        for i in range(len(boxes)):
            if boxes[i] is oldbox:
                boxes[i] = newbox
        if self.staticdata.virtualizable_info is not None:
            boxes = self.virtualizable_boxes
            for i in range(len(boxes)):
                if boxes[i] is oldbox:
                    boxes[i] = newbox

    def find_biggest_function(self):
        assert not self.is_blackholing()

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

    def direct_assembler_call(self, pc, varargs, token, call_position):
        """ Generate a direct call to assembler for portal entry point.
        """
        assert not self.is_blackholing() # XXX
        num_green_args = self.staticdata.num_green_args
        args = varargs[num_green_args + 1:]
        resbox = self.history.operations[call_position].result
        rest = self.history.slice_history_at(call_position)
        if self.staticdata.virtualizable_info is not None:
            vindex = self.staticdata.virtualizable_info.index_of_virtualizable
            vbox = args[vindex - num_green_args]
            args += self.gen_load_from_other_virtualizable(vbox)
        self.history.record(rop.CALL_ASSEMBLER, args[:], resbox, descr=token)
        self.history.operations += rest

class GenerateMergePoint(Exception):
    def __init__(self, args, target_loop_token):
        assert target_loop_token is not None
        self.argboxes = args
        self.target_loop_token = target_loop_token
