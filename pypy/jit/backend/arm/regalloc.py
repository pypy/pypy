from pypy.jit.backend.llsupport.regalloc import FrameManager, \
        RegisterManager, compute_vars_longevity, TempBox
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm.locations import imm
from pypy.jit.backend.arm.helper.regalloc import (prepare_op_by_helper_call,
                                                    prepare_op_unary_cmp,
                                                    prepare_op_ri,
                                                    prepare_cmp_op,
                                                    prepare_float_op,
                                                    _check_imm_arg)
from pypy.jit.metainterp.history import (Const, ConstInt, ConstFloat, ConstPtr,
                                        Box, BoxInt, BoxPtr, AbstractFailDescr,
                                        INT, REF, FLOAT, LoopToken)
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llsupport.descr import BaseFieldDescr, BaseArrayDescr
from pypy.jit.backend.llsupport import symbolic
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory
from pypy.jit.codewriter import heaptracker
from pypy.rlib.objectmodel import we_are_translated

class TempInt(TempBox):
    type = INT

    def __repr__(self):
        return "<TempInt at %s>" % (id(self),)

class TempPtr(TempBox):
    type = REF

    def __repr__(self):
        return "<TempPtr at %s>" % (id(self),)

class TempFloat(TempBox):
    type = FLOAT

    def __repr__(self):
        return "<TempFloat at %s>" % (id(self),)

class ARMFrameManager(FrameManager):
    def __init__(self):
        FrameManager.__init__(self)
        self.frame_depth = 1

    @staticmethod
    def frame_pos(loc, type):
        # XXX for now we only have one word stack locs
        return locations.StackLocation(loc)

def void(self, op, fcond):
    return []

class VFPRegisterManager(RegisterManager):
    all_regs = r.all_vfp_regs
    box_types = [FLOAT]
    save_around_call_regs = all_regs

    def convert_to_imm(self, c):
        adr = self.assembler.datablockwrapper.malloc_aligned(8, 8)
        rffi.cast(rffi.CArrayPtr(rffi.DOUBLE), adr)[0] = c.getfloat()
        return locations.ConstFloatLoc(adr)

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

class ARMv7RegisterMananger(RegisterManager):
    all_regs              = r.all_regs
    box_types             = None       # or a list of acceptable types
    no_lower_byte_regs    = all_regs
    save_around_call_regs = r.caller_resp

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def call_result_location(self, v):
        return r.r0

    def before_call(self, force_store=[], save_all_regs=False):
        for v, reg in self.reg_bindings.items():
            if(reg in self.save_around_call_regs and v not in force_store and
                        self.longevity[v][1] <= self.position):
                # variable dies
                del self.reg_bindings[v]
                self.free_regs.append(reg)
                continue
            if not save_all_regs and reg not in self.save_around_call_regs:
                # we don't have to
                continue
            self._sync_var(v)
            del self.reg_bindings[v]
            self.free_regs.append(reg)

    def convert_to_imm(self, c):
        if isinstance(c, ConstInt):
            return locations.ImmLocation(c.value)
        else:
            assert isinstance(c, ConstPtr)
            return locations.ImmLocation(rffi.cast(lltype.Signed, c.value))
    
class Regalloc(object):

    def __init__(self, longevity, frame_manager=None, assembler=None):
        self.cpu = assembler.cpu
        self.longevity = longevity
        self.frame_manager = frame_manager
        self.assembler = assembler
        self.vfprm = VFPRegisterManager(longevity, frame_manager, assembler)
        self.rm = ARMv7RegisterMananger(longevity, frame_manager, assembler)

    def loc(self, var):
        if var.type == FLOAT:
            return self.vfprm.loc(var)
        else:
            return self.rm.loc(var)

    def force_allocate_reg(self, var, forbidden_vars=[], selected_reg=None,
                           need_lower_byte=False):
        if var.type == FLOAT:
            return self.vfprm.force_allocate_reg(var, forbidden_vars,
                                               selected_reg, need_lower_byte)
        else:
            return self.rm.force_allocate_reg(var, forbidden_vars,
                                              selected_reg, need_lower_byte)
    def possibly_free_var(self, var):
        if var.type == FLOAT:
            self.vfprm.possibly_free_var(var)
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
                         selected_reg=None, need_lower_byte=False):
        if var.type == FLOAT:
            return self.vfprm.make_sure_var_in_reg(var, forbidden_vars,
                                         selected_reg, need_lower_byte)
        else:
            return self.rm.make_sure_var_in_reg(var, forbidden_vars,
                                        selected_reg, need_lower_byte)


    def update_bindings(self, locs, frame_depth, inputargs):
        used = {}
        i = 0
        self.frame_manager.frame_depth = frame_depth
        for loc in locs:
            arg = inputargs[i]
            i += 1
            if loc.is_reg():
                self.reg_bindings[arg] = loc
            #XXX add float
            else:
                self.frame_manager.frame_bindings[arg] = loc
            used[loc] = None

        # XXX combine with x86 code and move to llsupport
        self.free_regs = []
        for reg in self.all_regs:
            if reg not in used:
                self.free_regs.append(reg)
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))


    def force_spill_var(self, var):
        self._sync_var(var)
        try:
            loc = self.reg_bindings[var]
            del self.reg_bindings[var]
            self.free_regs.append(loc)
        except KeyError:
            if not we_are_translated():
                import pdb; pdb.set_trace()
            else:
                raise ValueError


    def _ensure_value_is_boxed(self, thing, forbidden_vars=[]):
        box = None
        loc = None
        if isinstance(thing, Const):
            if isinstance(thing, ConstInt):
                box = TempInt()
            elif isinstance(thing, ConstPtr):
                box = TempPtr()
            elif isinstance(thing, ConstFloat):
                box = TempFloat()
            else:
                box = TempBox()
            loc = self.force_allocate_reg(box,
                            forbidden_vars=forbidden_vars)
            if isinstance(thing, ConstFloat):
               imm = self.vfprm.convert_to_imm(thing) 
            else:
                imm = self.rm.convert_to_imm(thing)
            self.assembler.load(loc, imm)
        else:
            loc = self.make_sure_var_in_reg(thing,
                            forbidden_vars=forbidden_vars)
            box = thing
        return loc, box




    def prepare_op_int_add(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        imm_a0 = _check_imm_arg(a0)
        imm_a1 = _check_imm_arg(a1)
        if not imm_a0 and imm_a1:
            l0, box = self._ensure_value_is_boxed(a0)
            l1 = self.make_sure_var_in_reg(a1, [a0])
            boxes.append(box)
        elif imm_a0 and not imm_a1:
            l0 = self.make_sure_var_in_reg(a0)
            l1, box = self._ensure_value_is_boxed(a1, [a0])
            boxes.append(box)
        else:
            l0, box = self._ensure_value_is_boxed(a0)
            boxes.append(box)
            l1, box = self._ensure_value_is_boxed(a1, [box])
            boxes.append(box)
        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, l1, res]

    def prepare_op_int_sub(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        imm_a0 = _check_imm_arg(a0)
        imm_a1 = _check_imm_arg(a1)
        if not imm_a0 and imm_a1:
            l0, box = self._ensure_value_is_boxed(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, [a0])
            boxes.append(box)
        elif imm_a0 and not imm_a1:
            l0 = self.make_sure_var_in_reg(a0)
            l1, box = self._ensure_value_is_boxed(a1, boxes)
            boxes.append(box)
        else:
            l0, box = self._ensure_value_is_boxed(a0, boxes)
            boxes.append(box)
            l1, box = self._ensure_value_is_boxed(a1, boxes)
            boxes.append(box)
        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, l1, res]

    def prepare_op_int_mul(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes

        reg1, box = self._ensure_value_is_boxed(a0, forbidden_vars=boxes)
        boxes.append(box)
        reg2, box = self._ensure_value_is_boxed(a1, forbidden_vars=boxes)
        boxes.append(box)

        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [reg1, reg2, res]

    def prepare_guard_int_mul_ovf(self, op, guard, fcond):
        args = []
        boxes = list(op.getarglist())
        a0, a1 = boxes

        reg1, box = self._ensure_value_is_boxed(a0,forbidden_vars=boxes)
        boxes.append(box)
        reg2, box = self._ensure_value_is_boxed(a1,forbidden_vars=boxes)
        boxes.append(box)
        res = self.force_allocate_reg(op.result, boxes)

        args.append(reg1)
        args.append(reg2)
        args.append(res)
        args = self._prepare_guard(guard, args)
        self.possibly_free_vars(boxes)
        self.possibly_free_var(op.result)
        return args


    prepare_op_int_floordiv = prepare_op_by_helper_call()
    prepare_op_int_mod = prepare_op_by_helper_call()
    prepare_op_uint_floordiv = prepare_op_by_helper_call()

    prepare_op_int_and = prepare_op_ri()
    prepare_op_int_or = prepare_op_ri()
    prepare_op_int_xor = prepare_op_ri()
    prepare_op_int_lshift = prepare_op_ri(imm_size=0x1F, allow_zero=False, commutative=False)
    prepare_op_int_rshift = prepare_op_ri(imm_size=0x1F, allow_zero=False, commutative=False)
    prepare_op_uint_rshift = prepare_op_ri(imm_size=0x1F, allow_zero=False, commutative=False)

    prepare_op_int_lt = prepare_cmp_op()
    prepare_op_int_le = prepare_cmp_op()
    prepare_op_int_eq = prepare_cmp_op()
    prepare_op_int_ne = prepare_cmp_op()
    prepare_op_int_gt = prepare_cmp_op()
    prepare_op_int_ge = prepare_cmp_op()

    prepare_op_uint_le = prepare_cmp_op()
    prepare_op_uint_gt = prepare_cmp_op()

    prepare_op_uint_lt = prepare_cmp_op(inverse=True)
    prepare_op_uint_ge = prepare_cmp_op(inverse=True)

    prepare_op_int_add_ovf = prepare_op_int_add
    prepare_op_int_sub_ovf = prepare_op_int_sub

    prepare_op_ptr_eq = prepare_op_int_eq
    prepare_op_ptr_ne = prepare_op_int_ne

    prepare_op_int_is_true = prepare_op_unary_cmp()
    prepare_op_int_is_zero = prepare_op_unary_cmp()

    def prepare_op_int_neg(self, op, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0))
        self.possibly_free_var(box)
        resloc = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, resloc]

    prepare_op_int_invert = prepare_op_int_neg

    def prepare_op_call(self, op, fcond):
        args = [imm(rffi.cast(lltype.Signed, op.getarg(0).getint()))]
        return args

    def _prepare_guard(self, op, args=None):
        if args is None:
            args = []
        args.append(imm(self.frame_manager.frame_depth))
        for arg in op.getfailargs():
            if arg:
                args.append(self.loc(arg))
            else:
                args.append(None)
        return args

    def prepare_op_finish(self, op, fcond):
        args = [imm(self.frame_manager.frame_depth)]
        for i in range(op.numargs()):
            arg = op.getarg(i)
            if arg:
                args.append(self.loc(arg))
            else:
                args.append(None)
        return args

    def prepare_op_guard_true(self, op, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0))
        args = self._prepare_guard(op, [l0])
        self.possibly_free_var(box)
        return args

    prepare_op_guard_false = prepare_op_guard_true
    prepare_op_guard_nonnull = prepare_op_guard_true
    prepare_op_guard_isnull = prepare_op_guard_true

    def prepare_op_guard_value(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        imm_a1 = _check_imm_arg(a1)
        l0, box = self._ensure_value_is_boxed(a0, boxes)
        boxes.append(box)
        if not imm_a1:
            l1, box = self._ensure_value_is_boxed(a1,boxes)
            boxes.append(box)
        else:
            l1 = self.make_sure_var_in_reg(a1)
        assert op.result is None
        arglocs = self._prepare_guard(op, [l0, l1])
        self.possibly_free_vars(boxes)
        return arglocs

    def prepare_op_guard_no_overflow(self, op, fcond):
        return  self._prepare_guard(op)

    prepare_op_guard_overflow = prepare_op_guard_no_overflow

    def prepare_op_guard_exception(self, op, fcond):
        boxes = list(op.getarglist())
        arg0 = ConstInt(rffi.cast(lltype.Signed, op.getarg(0).getint()))
        loc, box = self._ensure_value_is_boxed(arg0)
        boxes.append(box)
        box = TempBox()
        loc1 = self.force_allocate_reg(box, boxes)
        boxes.append(box)
        if op.result in self.longevity:
            resloc = self.force_allocate_reg(op.result, boxes)
            boxes.append(op.result)
        else:
            resloc = None
        pos_exc_value = imm(self.cpu.pos_exc_value())
        pos_exception = imm(self.cpu.pos_exception())
        arglocs = self._prepare_guard(op, [loc, loc1, resloc, pos_exc_value, pos_exception])
        self.possibly_free_vars(boxes)
        return arglocs

    def prepare_op_guard_no_exception(self, op, fcond):
        loc, box = self._ensure_value_is_boxed(
                    ConstInt(self.cpu.pos_exception()))
        arglocs = self._prepare_guard(op, [loc])
        self.possibly_free_var(box)
        return arglocs

    def prepare_op_guard_class(self, op, fcond):
        return self._prepare_guard_class(op, fcond)

    prepare_op_guard_nonnull_class = prepare_op_guard_class

    def _prepare_guard_class(self, op, fcond):
        assert isinstance(op.getarg(0), Box)
        boxes = list(op.getarglist())

        x, x_box = self._ensure_value_is_boxed(boxes[0], boxes)
        boxes.append(x_box)

        t = TempBox()
        y = self.force_allocate_reg(t, boxes)
        boxes.append(t)
        y_val = rffi.cast(lltype.Signed, op.getarg(1).getint())
        self.assembler.load(y, imm(y_val))

        offset = self.cpu.vtable_offset
        offset_loc, offset_box = self._ensure_value_is_boxed(ConstInt(offset), boxes)
        boxes.append(offset_box)
        arglocs = self._prepare_guard(op, [x, y, offset_loc])
        self.possibly_free_vars(boxes)

        return arglocs


    def prepare_op_jump(self, op, fcond):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        return [self.loc(op.getarg(i)) for i in range(op.numargs())]


    def prepare_op_setfield_gc(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        ofs, size, ptr = self._unpack_fielddescr(op.getdescr())
        base_loc, base_box = self._ensure_value_is_boxed(a0, boxes)
        boxes.append(base_box)
        value_loc, value_box = self._ensure_value_is_boxed(a1, boxes)
        boxes.append(value_box)
        self.possibly_free_vars(boxes)
        return [value_loc, base_loc, imm(ofs), imm(size)]

    prepare_op_setfield_raw = prepare_op_setfield_gc

    def prepare_op_getfield_gc(self, op, fcond):
        a0 = op.getarg(0)
        ofs, size, ptr = self._unpack_fielddescr(op.getdescr())
        base_loc, base_box = self._ensure_value_is_boxed(a0)
        self.possibly_free_var(a0)
        self.possibly_free_var(base_box)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [base_loc, imm(ofs), res, imm(size)]

    prepare_op_getfield_raw = prepare_op_getfield_gc
    prepare_op_getfield_raw_pure = prepare_op_getfield_gc
    prepare_op_getfield_gc_pure = prepare_op_getfield_gc

    def prepare_op_arraylen_gc(self, op, fcond):
        arraydescr = op.getdescr()
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_ofs_length(self.cpu.translate_support_code)
        arg = op.getarg(0)
        base_loc, base_box = self._ensure_value_is_boxed(arg)
        self.possibly_free_vars([arg, base_box])

        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [res, base_loc, imm(ofs)]

    def prepare_op_setarrayitem_gc(self, op, fcond):
        a0, a1, a2 = boxes = list(op.getarglist())
        _, scale, ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc, base_box  = self._ensure_value_is_boxed(a0, boxes)
        boxes.append(base_box)
        ofs_loc, ofs_box = self._ensure_value_is_boxed(a1, boxes)
        boxes.append(ofs_box)
        #XXX check if imm would be fine here
        value_loc, value_box = self._ensure_value_is_boxed(a2, boxes)
        boxes.append(value_box)
        self.possibly_free_vars(boxes)
        return [value_loc, base_loc, ofs_loc, imm(scale), imm(ofs)]
    prepare_op_setarrayitem_raw = prepare_op_setarrayitem_gc

    def prepare_op_getarrayitem_gc(self, op, fcond):
        a0, a1 = boxes = list(op.getarglist())
        _, scale, ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc, base_box  = self._ensure_value_is_boxed(a0, boxes)
        boxes.append(base_box)
        ofs_loc, ofs_box = self._ensure_value_is_boxed(a1, boxes)
        boxes.append(ofs_box)
        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [res, base_loc, ofs_loc, imm(scale), imm(ofs)]

    prepare_op_getarrayitem_raw = prepare_op_getarrayitem_gc
    prepare_op_getarrayitem_gc_pure = prepare_op_getarrayitem_gc

    def prepare_op_strlen(self, op, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0))
        boxes = [box]


        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        ofs_box = ConstInt(ofs_length)
        imm_ofs = _check_imm_arg(ofs_box)

        if imm_ofs:
            l1 = self.make_sure_var_in_reg(ofs_box, boxes)
        else:
            l1, box1 = self._ensure_value_is_boxed(ofs_box, boxes)
            boxes.append(box1)

        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, l1, res]

    def prepare_op_strgetitem(self, op, fcond):
        boxes = list(op.getarglist())
        base_loc, box = self._ensure_value_is_boxed(boxes[0])
        boxes.append(box)

        a1 = boxes[1]
        imm_a1 = _check_imm_arg(a1)
        if imm_a1:
            ofs_loc = self.make_sure_var_in_reg(a1, boxes)
        else:
            ofs_loc, box = self._ensure_value_is_boxed(a1, boxes)
            boxes.append(box)

        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        assert itemsize == 1
        return [res, base_loc, ofs_loc, imm(basesize)]

    def prepare_op_strsetitem(self, op, fcond):
        boxes = list(op.getarglist())

        base_loc, box = self._ensure_value_is_boxed(boxes[0], boxes)
        boxes.append(box)

        ofs_loc, box = self._ensure_value_is_boxed(boxes[1], boxes)
        boxes.append(box)

        value_loc, box = self._ensure_value_is_boxed(boxes[2], boxes)
        boxes.append(box)

        self.possibly_free_vars(boxes)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        assert itemsize == 1
        return [value_loc, base_loc, ofs_loc, imm(basesize)]

    prepare_op_copystrcontent = void
    prepare_op_copyunicodecontent = void

    def prepare_op_unicodelen(self, op, fcond):
        l0, box = self._ensure_value_is_boxed(op.getarg(0))
        boxes = [box]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        ofs_box = ConstInt(ofs_length)
        imm_ofs = _check_imm_arg(ofs_box)

        if imm_ofs:
            l1 = imm(ofs_length)
        else:
            l1, box1 = self._ensure_value_is_boxed(ofs_box, boxes)
            boxes.append(box1)

        self.possibly_free_vars(boxes)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, l1, res]

    def prepare_op_unicodegetitem(self, op, fcond):
        boxes = list(op.getarglist())
        base_loc, box = self._ensure_value_is_boxed(boxes[0], boxes)
        boxes.append(box)
        ofs_loc, box = self._ensure_value_is_boxed(boxes[1], boxes)
        boxes.append(box)
        self.possibly_free_vars(boxes)

        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        scale = itemsize/2
        return [res, base_loc, ofs_loc, imm(scale), imm(basesize), imm(itemsize)]

    def prepare_op_unicodesetitem(self, op, fcond):
        boxes = list(op.getarglist())
        base_loc, box = self._ensure_value_is_boxed(boxes[0], boxes)
        boxes.append(box)
        ofs_loc, box = self._ensure_value_is_boxed(boxes[1], boxes)
        boxes.append(box)
        value_loc, box = self._ensure_value_is_boxed(boxes[2], boxes)
        boxes.append(box)

        self.possibly_free_vars(boxes)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        scale = itemsize/2
        return [value_loc, base_loc, ofs_loc, imm(scale), imm(basesize), imm(itemsize)]

    def prepare_op_same_as(self, op, fcond):
        arg = op.getarg(0)
        imm_arg = _check_imm_arg(arg)
        if imm_arg:
            argloc = self.make_sure_var_in_reg(arg)
        else:
            argloc, box = self._ensure_value_is_boxed(arg)
            self.possibly_free_var(box)
        self.possibly_free_vars_for_op(op)

        resloc = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [argloc, resloc]

    def prepare_op_new(self, op, fcond):
        arglocs = self._prepare_args_for_new_op(op.getdescr())
        self.assembler._emit_call(self.assembler.malloc_func_addr,
                                arglocs, self, result=op.result)
        self.possibly_free_vars(arglocs)
        self.possibly_free_var(op.result)
        return []

    def prepare_op_new_with_vtable(self, op, fcond):
        classint = op.getarg(0).getint()
        descrsize = heaptracker.vtable2descr(self.cpu, classint)
        callargs = self._prepare_args_for_new_op(descrsize)
        self.assembler._emit_call(self.assembler.malloc_func_addr,
                                    callargs, self, result=op.result)
        self.possibly_free_vars(callargs)
        self.possibly_free_var(op.result)
        return [imm(classint)]

    def prepare_op_new_array(self, op, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newarray is not None:
            raise NotImplementedError
        # boehm GC
        itemsize, scale, basesize, ofs_length, _ = (
            self._unpack_arraydescr(op.getdescr()))
        return self._malloc_varsize(basesize, ofs_length, itemsize, op)

    def prepare_op_newstr(self, op, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newstr is not None:
            raise NotImplementedError
        # boehm GC
        ofs_items, itemsize, ofs = symbolic.get_array_token(rstr.STR,
                            self.cpu.translate_support_code)
        assert itemsize == 1
        return self._malloc_varsize(ofs_items, ofs, itemsize, op)

    def prepare_op_newunicode(self, op, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newunicode is not None:
            raise NotImplementedError
        # boehm GC
        ofs_items, _, ofs = symbolic.get_array_token(rstr.UNICODE,
                            self.cpu.translate_support_code)
        _, itemsize, _ = symbolic.get_array_token(rstr.UNICODE,
                            self.cpu.translate_support_code)
        return self._malloc_varsize(ofs_items, ofs, itemsize, op)

    def _malloc_varsize(self, ofs_items, ofs_length, itemsize, op):
        v = op.getarg(0)
        res_v = op.result
        boxes = [v, res_v]
        itemsize_box = ConstInt(itemsize)
        ofs_items_box = ConstInt(ofs_items)
        if _check_imm_arg(ofs_items_box):
            ofs_items_loc = self.convert_to_imm(ofs_items_box)
        else:
            ofs_items_loc, ofs_items_box = self._ensure_value_is_boxed(ofs_items_box, boxes)
            boxes.append(ofs_items_box)
        vloc, v = self._ensure_value_is_boxed(v, [res_v])
        boxes.append(v)
        size, size_box = self._ensure_value_is_boxed(itemsize_box, boxes)
        boxes.append(size_box)
        self.assembler._regalloc_malloc_varsize(size, size_box,
                                vloc, ofs_items_loc, self, res_v)
        base_loc = self.make_sure_var_in_reg(res_v)
        value_loc = self.make_sure_var_in_reg(v)
        self.possibly_free_vars(boxes)
        assert value_loc.is_reg()
        assert base_loc.is_reg()
        return [value_loc, base_loc, imm(ofs_length)]

    prepare_op_cond_call_gc_wb = void
    prepare_op_debug_merge_point = void
    prepare_op_jit_debug = void

    def prepare_op_force_token(self, op, fcond):
        res_loc = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [res_loc]

    def prepare_guard_call_may_force(self, op, guard_op, fcond):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self.assembler._write_fail_index(fail_index)
        args = [imm(rffi.cast(lltype.Signed, op.getarg(0).getint()))]
        # force all reg values to be spilled when calling
        self.assembler.emit_op_call(op, args, self, fcond, spill_all_regs=True)

        return self._prepare_guard(guard_op)

    def prepare_guard_call_assembler(self, op, guard_op, fcond):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self.assembler._write_fail_index(fail_index)
        return []

    def _prepare_args_for_new_op(self, new_args):
        gc_ll_descr = self.cpu.gc_ll_descr
        args = gc_ll_descr.args_for_new(new_args)
        arglocs = []
        for i in range(len(args)):
            arg = args[i]
            t = TempBox()
            l = self.force_allocate_reg(t, selected_reg=r.all_regs[i])
            self.assembler.load(l, imm(arg))
            arglocs.append(t)
        return arglocs

    # from ../x86/regalloc.py:791
    def _unpack_fielddescr(self, fielddescr):
        assert isinstance(fielddescr, BaseFieldDescr)
        ofs = fielddescr.offset
        size = fielddescr.get_field_size(self.cpu.translate_support_code)
        ptr = fielddescr.is_pointer_field()
        return ofs, size, ptr

    # from ../x86/regalloc.py:779
    def _unpack_arraydescr(self, arraydescr):
        assert isinstance(arraydescr, BaseArrayDescr)
        cpu = self.cpu
        ofs_length = arraydescr.get_ofs_length(cpu.translate_support_code)
        ofs = arraydescr.get_base_size(cpu.translate_support_code)
        size = arraydescr.get_item_size(cpu.translate_support_code)
        ptr = arraydescr.is_array_of_pointers()
        scale = 0
        while (1 << scale) < size:
            scale += 1
        assert (1 << scale) == size
        return size, scale, ofs, ofs_length, ptr


    prepare_op_float_add = prepare_float_op()
    prepare_op_float_sub = prepare_float_op()
    prepare_op_float_mul = prepare_float_op()
    prepare_op_float_truediv = prepare_float_op()

def make_operation_list():
    def notimplemented(self, op, fcond):
        raise NotImplementedError, op

    operations = [None] * (rop._LAST+1)
    for key, value in rop.__dict__.items():
        key = key.lower()
        if key.startswith('_'):
            continue
        methname = 'prepare_op_%s' % key
        if hasattr(Regalloc, methname):
            func = getattr(Regalloc, methname).im_func
        else:
            func = notimplemented
        operations[value] = func
    return operations

def make_guard_operation_list():
    def notimplemented(self, op, guard_op, fcond):
        raise NotImplementedError, op
    guard_operations = [notimplemented] * rop._LAST
    for key, value in rop.__dict__.items():
        key = key.lower()
        if key.startswith('_'):
            continue
        methname = 'prepare_guard_%s' % key
        if hasattr(Regalloc, methname):
            func = getattr(Regalloc, methname).im_func
            guard_operations[value] = func
    return guard_operations

Regalloc.operations = make_operation_list()
Regalloc.operations_with_guard = make_guard_operation_list()
