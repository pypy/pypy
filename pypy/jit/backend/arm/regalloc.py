from pypy.jit.backend.llsupport.regalloc import FrameManager, \
        RegisterManager, compute_vars_longevity, TempBox, compute_loop_consts
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm.locations import imm
from pypy.jit.backend.arm.helper.regalloc import (prepare_op_by_helper_call,
                                                    prepare_op_unary_cmp,
                                                    prepare_op_ri,
                                                    prepare_cmp_op,
                                                    prepare_float_op,
                                                    _check_imm_arg)
from pypy.jit.backend.arm.jump import remap_frame_layout_mixed
from pypy.jit.backend.arm.arch import MY_COPY_OF_REGS, WORD
from pypy.jit.codewriter import longlong
from pypy.jit.metainterp.history import (Const, ConstInt, ConstFloat, ConstPtr,
                                        Box, BoxInt, BoxPtr, AbstractFailDescr,
                                        INT, REF, FLOAT, LoopToken)
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llsupport.descr import BaseFieldDescr, BaseArrayDescr, \
                                             BaseCallDescr, BaseSizeDescr, \
                                             InteriorFieldDescr
from pypy.jit.backend.llsupport import symbolic
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory
from pypy.jit.codewriter import heaptracker
from pypy.jit.codewriter.effectinfo import EffectInfo
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
        num_words = ARMFrameManager.frame_size(type)
        if type == FLOAT:
            return locations.StackLocation(loc+1, num_words=num_words, type=type)
        return locations.StackLocation(loc, num_words=num_words, type=type)

    @staticmethod
    def frame_size(type):
        if type == FLOAT:
            return  2
        return 1

def void(self, op, fcond):
    return []

class VFPRegisterManager(RegisterManager):
    all_regs = r.all_vfp_regs
    box_types = [FLOAT]
    save_around_call_regs = r.all_vfp_regs

    def convert_to_imm(self, c):
        adr = self.assembler.datablockwrapper.malloc_aligned(8, 8)
        x = c.getfloatstorage()
        rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[0] = x
        return locations.ConstFloatLoc(adr)

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def after_call(self, v):
        """ Adjust registers according to the result of the call,
        which is in variable v.
        """
        self._check_type(v)
        r = self.force_allocate_reg(v)
        return r

    def ensure_value_is_boxed(self, thing, forbidden_vars=[]):
        box = None
        loc = None
        if isinstance(thing, Const):
            assert isinstance(thing, ConstFloat)
            loc = self.get_scratch_reg(FLOAT, self.temp_boxes + forbidden_vars)
            imm = self.convert_to_imm(thing)
            self.assembler.load(loc, imm)
        else:
            loc = self.make_sure_var_in_reg(thing,
                            forbidden_vars=self.temp_boxes + forbidden_vars)
        return loc

    def get_scratch_reg(self, type=FLOAT, forbidden_vars=[], selected_reg=None):
        assert type == FLOAT # for now
        box = TempFloat()
        self.temp_boxes.append(box)
        return self.force_allocate_reg(box, forbidden_vars=forbidden_vars, selected_reg=selected_reg)


class ARMv7RegisterMananger(RegisterManager):
    all_regs              = r.all_regs
    box_types             = None       # or a list of acceptable types
    no_lower_byte_regs    = all_regs
    save_around_call_regs = r.caller_resp

    REGLOC_TO_COPY_AREA_OFS = {
        r.r2: MY_COPY_OF_REGS + 0 * WORD,
        r.r3: MY_COPY_OF_REGS + 1 * WORD,
        r.r4: MY_COPY_OF_REGS + 2 * WORD,
        r.r5: MY_COPY_OF_REGS + 3 * WORD,
        r.r6: MY_COPY_OF_REGS + 4 * WORD,
        r.r7: MY_COPY_OF_REGS + 5 * WORD,
        r.r8: MY_COPY_OF_REGS + 6 * WORD,
        r.r9: MY_COPY_OF_REGS + 7 * WORD,
        r.r10: MY_COPY_OF_REGS + 8 * WORD,
    }

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def call_result_location(self, v):
        return r.r0

    def convert_to_imm(self, c):
        if isinstance(c, ConstInt):
            return locations.ImmLocation(c.value)
        else:
            assert isinstance(c, ConstPtr)
            return locations.ImmLocation(rffi.cast(lltype.Signed, c.value))

    def ensure_value_is_boxed(self, thing, forbidden_vars=None):
        box = None
        loc = None
        if isinstance(thing, Const):
            if isinstance(thing, ConstPtr):
                tp = REF
            else:
                tp = INT
            loc = self.get_scratch_reg(tp, forbidden_vars=self.temp_boxes + forbidden_vars)
            imm = self.convert_to_imm(thing)
            self.assembler.load(loc, imm)
        else:
            loc = self.make_sure_var_in_reg(thing,
                            forbidden_vars=forbidden_vars)
        return loc

    def get_scratch_reg(self, type=INT, forbidden_vars=[], selected_reg=None):
        assert type == INT or type == REF
        box = TempBox()
        self.temp_boxes.append(box)
        return self.force_allocate_reg(box, forbidden_vars=forbidden_vars, selected_reg=selected_reg)

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
    
    def position(self):
        return self.rm.position

    def next_instruction(self):
        self.rm.next_instruction()
        self.vfprm.next_instruction()

    def _check_invariants(self):
        self.rm._check_invariants()
        self.vfprm._check_invariants()

    def stays_alive(self, v):
        if v.type == FLOAT:
            return self.vfprm.stays_alive(v)
        else:
            return self.rm.stays_alive(v)

    def call_result_location(self, v):
        if v.type == FLOAT:
            return self.vfprm.call_result_location(v)
        else:
            return self.rm.call_result_location(v)

    def after_call(self, v):
        if v.type == FLOAT:
            return self.vfprm.after_call(v)
        else:
            return self.rm.after_call(v)

    def force_allocate_reg(self, var, forbidden_vars=[], selected_reg=None,
                           need_lower_byte=False):
        if var.type == FLOAT:
            return self.vfprm.force_allocate_reg(var, forbidden_vars,
                                               selected_reg, need_lower_byte)
        else:
            return self.rm.force_allocate_reg(var, forbidden_vars,
                                              selected_reg, need_lower_byte)
    def try_allocate_reg(self, v, selected_reg=None, need_lower_byte=False):
        if v.type == FLOAT:
            return self.vfprm.try_allocate_reg(v, selected_reg, need_lower_byte)
        else:
            return self.rm.try_allocate_reg(v, selected_reg, need_lower_byte)

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

    def get_scratch_reg(self, type, forbidden_vars=[], selected_reg=None):
        if type == FLOAT:
            return self.vfprm.get_scratch_reg(type, forbidden_vars, selected_reg)
        else:
            return self.rm.get_scratch_reg(type, forbidden_vars, selected_reg)

    def free_temp_vars(self):
        self.rm.free_temp_vars()
        self.vfprm.free_temp_vars()

    def make_sure_var_in_reg(self, var, forbidden_vars=[],
                         selected_reg=None, need_lower_byte=False):
        if var.type == FLOAT:
            return self.vfprm.make_sure_var_in_reg(var, forbidden_vars,
                                         selected_reg, need_lower_byte)
        else:
            return self.rm.make_sure_var_in_reg(var, forbidden_vars,
                                        selected_reg, need_lower_byte)

    def convert_to_imm(self, value):
        if isinstance(value, ConstInt):
            return self.rm.convert_to_imm(value)
        else:
            assert isinstance(value, ConstFloat)
            return self.vfprm.convert_to_imm(value)

    def prepare_loop(self, inputargs, operations, looptoken):
        loop_consts = compute_loop_consts(inputargs, operations[-1], looptoken)
        floatlocs = [None] * len(inputargs)
        nonfloatlocs = [None] * len(inputargs)
        for i in range(len(inputargs)):
            arg = inputargs[i]
            assert not isinstance(arg, Const)
            reg = None
            loc = inputargs[i]
            if arg not in loop_consts and self.longevity[arg][1] > -1:
                reg = self.try_allocate_reg(loc)

            loc = self.loc(arg)
            if arg.type == FLOAT:
                floatlocs[i] = loc
            else:
                nonfloatlocs[i] = loc
        self.possibly_free_vars(list(inputargs))
        
        return nonfloatlocs, floatlocs

    def update_bindings(self, locs, frame_depth, inputargs):
        used = {}
        i = 0
        self.frame_manager.frame_depth = frame_depth
        for loc in locs:
            arg = inputargs[i]
            i += 1
            if loc.is_reg():
                self.rm.reg_bindings[arg] = loc
            elif loc.is_vfp_reg():
                self.vfprm.reg_bindings[arg] = loc
            else:
                assert loc.is_stack()
                self.frame_manager.frame_bindings[arg] = loc
            used[loc] = None

        # XXX combine with x86 code and move to llsupport
        self.rm.free_regs = []
        for reg in self.rm.all_regs:
            if reg not in used:
                self.rm.free_regs.append(reg)
        self.vfprm.free_regs = []
        for reg in self.vfprm.all_regs:
            if reg not in used:
                self.vfprm.free_regs.append(reg)
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))


    def force_spill_var(self, var):
        if var.type == FLOAT:
            self.vfprm.force_spill_var(var)
        else:
            self.rm.force_spill_var(var)

    def before_call(self, force_store=[], save_all_regs=False):
        self.rm.before_call(force_store, save_all_regs)
        self.vfprm.before_call(force_store, save_all_regs)
    def _ensure_value_is_boxed(self, thing, forbidden_vars=[]):
        if thing.type == FLOAT:
            return self.vfprm.ensure_value_is_boxed(thing, forbidden_vars)
        else:
            return self.rm.ensure_value_is_boxed(thing, forbidden_vars)

    def _sync_var(self, v):
        if v.type == FLOAT:
            self.vfprm._sync_var(v)
        else:
            self.rm._sync_var(v)

    def _prepare_op_int_add(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        imm_a0 = _check_imm_arg(a0)
        imm_a1 = _check_imm_arg(a1)
        if not imm_a0 and imm_a1:
            l0 = self._ensure_value_is_boxed(a0)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        elif imm_a0 and not imm_a1:
            l0 = self.make_sure_var_in_reg(a0)
            l1 = self._ensure_value_is_boxed(a1, boxes)
        else:
            l0 = self._ensure_value_is_boxed(a0)
            l1 = self._ensure_value_is_boxed(a1, boxes)
        return [l0, l1]

    def prepare_op_int_add(self, op, fcond):
        locs = self._prepare_op_int_add(op, fcond)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return locs + [res]

    def _prepare_op_int_sub(self, op, fcond):
        a0, a1 = boxes = op.getarglist()
        imm_a0 = _check_imm_arg(a0)
        imm_a1 = _check_imm_arg(a1)
        if not imm_a0 and imm_a1:
            l0 = self._ensure_value_is_boxed(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        elif imm_a0 and not imm_a1:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self._ensure_value_is_boxed(a1, boxes)
        else:
            l0 = self._ensure_value_is_boxed(a0, boxes)
            l1 = self._ensure_value_is_boxed(a1, boxes)
        return [l0, l1]

    def prepare_op_int_sub(self, op, fcond):
        locs = self._prepare_op_int_sub(op, fcond)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return locs + [res]

    def prepare_op_int_mul(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes

        reg1 = self._ensure_value_is_boxed(a0, forbidden_vars=boxes)
        reg2 = self._ensure_value_is_boxed(a1, forbidden_vars=boxes)

        self.possibly_free_vars(boxes)
        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [reg1, reg2, res]

    def prepare_guard_int_mul_ovf(self, op, guard, fcond):
        boxes = op.getarglist()
        reg1 = self._ensure_value_is_boxed(boxes[0], forbidden_vars=boxes)
        reg2 = self._ensure_value_is_boxed(boxes[1], forbidden_vars=boxes)
        res = self.force_allocate_reg(op.result)
        return self._prepare_guard(guard, [reg1, reg2, res])


    def prepare_guard_int_add_ovf(self, op, guard, fcond):
        locs = self._prepare_op_int_add(op, fcond)
        res = self.force_allocate_reg(op.result)
        locs.append(res)
        return self._prepare_guard(guard, locs)

    def prepare_guard_int_sub_ovf(self, op, guard, fcond):
        locs = self._prepare_op_int_sub(op, fcond)
        res = self.force_allocate_reg(op.result)
        locs.append(res)
        return self._prepare_guard(guard, locs)

    prepare_op_int_floordiv = prepare_op_by_helper_call('int_floordiv')
    prepare_op_int_mod = prepare_op_by_helper_call('int_mod')
    prepare_op_uint_floordiv = prepare_op_by_helper_call('unit_floordiv')

    prepare_op_int_and = prepare_op_ri('int_and')
    prepare_op_int_or = prepare_op_ri('int_or')
    prepare_op_int_xor = prepare_op_ri('int_xor')
    prepare_op_int_lshift = prepare_op_ri('int_lshift', imm_size=0x1F, allow_zero=False, commutative=False)
    prepare_op_int_rshift = prepare_op_ri('int_rshift', imm_size=0x1F, allow_zero=False, commutative=False)
    prepare_op_uint_rshift = prepare_op_ri('uint_rshift', imm_size=0x1F, allow_zero=False, commutative=False)

    prepare_op_int_lt = prepare_cmp_op('int_lt')
    prepare_op_int_le = prepare_cmp_op('int_le')
    prepare_op_int_eq = prepare_cmp_op('int_eq')
    prepare_op_int_ne = prepare_cmp_op('int_ne')
    prepare_op_int_gt = prepare_cmp_op('int_gt')
    prepare_op_int_ge = prepare_cmp_op('int_ge')

    prepare_op_uint_le = prepare_cmp_op('uint_le')
    prepare_op_uint_gt = prepare_cmp_op('uint_gt')

    prepare_op_uint_lt = prepare_cmp_op('uint_lt')
    prepare_op_uint_ge = prepare_cmp_op('uint_ge')

    prepare_op_ptr_eq = prepare_op_int_eq
    prepare_op_ptr_ne = prepare_op_int_ne

    prepare_guard_int_lt = prepare_cmp_op('guard_int_lt')
    prepare_guard_int_le = prepare_cmp_op('guard_int_le')
    prepare_guard_int_eq = prepare_cmp_op('guard_int_eq')
    prepare_guard_int_ne = prepare_cmp_op('guard_int_ne')
    prepare_guard_int_gt = prepare_cmp_op('guard_int_gt')
    prepare_guard_int_ge = prepare_cmp_op('guard_int_ge')

    prepare_guard_uint_le = prepare_cmp_op('guard_uint_le')
    prepare_guard_uint_gt = prepare_cmp_op('guard_uint_gt')

    prepare_guard_uint_lt = prepare_cmp_op('guard_uint_lt')
    prepare_guard_uint_ge = prepare_cmp_op('guard_uint_ge')

    prepare_guard_ptr_eq = prepare_guard_int_eq
    prepare_guard_ptr_ne = prepare_guard_int_ne

    prepare_op_int_add_ovf = prepare_op_int_add
    prepare_op_int_sub_ovf = prepare_op_int_sub


    prepare_op_int_is_true = prepare_op_unary_cmp('int_is_true')
    prepare_op_int_is_zero = prepare_op_unary_cmp('int_is_zero')

    prepare_guard_int_is_true = prepare_op_unary_cmp('int_is_true')
    prepare_guard_int_is_zero = prepare_op_unary_cmp('int_is_zero')

    def prepare_op_int_neg(self, op, fcond):
        l0 = self._ensure_value_is_boxed(op.getarg(0))
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        resloc = self.force_allocate_reg(op.result)
        return [l0, resloc]

    prepare_op_int_invert = prepare_op_int_neg

    def prepare_op_call(self, op, fcond):
        effectinfo = op.getdescr().get_extra_info()
        if effectinfo is not None:
            oopspecindex = effectinfo.oopspecindex
            if oopspecindex == EffectInfo.OS_MATH_SQRT:
                args = self.prepare_op_math_sqrt(op, fcond)
                self.assembler.emit_op_math_sqrt(op, args, self, fcond)
                return
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
                self.possibly_free_var(arg)
            else:
                args.append(None)
        return args

    def prepare_op_guard_true(self, op, fcond):
        l0 = self._ensure_value_is_boxed(op.getarg(0))
        args = self._prepare_guard(op, [l0])
        return args

    prepare_op_guard_false = prepare_op_guard_true
    prepare_op_guard_nonnull = prepare_op_guard_true
    prepare_op_guard_isnull = prepare_op_guard_true

    def prepare_op_guard_value(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        imm_a1 = _check_imm_arg(a1)
        l0 = self._ensure_value_is_boxed(a0, boxes)
        if not imm_a1:
            l1 = self._ensure_value_is_boxed(a1, boxes)
        else:
            l1 = self.make_sure_var_in_reg(a1, boxes)
        assert op.result is None
        arglocs = self._prepare_guard(op, [l0, l1])
        self.possibly_free_vars(op.getarglist())
        self.possibly_free_vars(op.getfailargs())
        return arglocs

    def prepare_op_guard_no_overflow(self, op, fcond):
        locs = self._prepare_guard(op)
        self.possibly_free_vars(op.getfailargs())
        return locs

    prepare_op_guard_overflow = prepare_op_guard_no_overflow
    prepare_op_guard_not_invalidated = prepare_op_guard_no_overflow


    def prepare_op_guard_exception(self, op, fcond):
        boxes = list(op.getarglist())
        arg0 = ConstInt(rffi.cast(lltype.Signed, op.getarg(0).getint()))
        loc = self._ensure_value_is_boxed(arg0)
        loc1 = self.get_scratch_reg(INT, boxes)
        if op.result in self.longevity:
            resloc = self.force_allocate_reg(op.result, boxes)
            self.possibly_free_var(op.result)
        else:
            resloc = None
        pos_exc_value = imm(self.cpu.pos_exc_value())
        pos_exception = imm(self.cpu.pos_exception())
        arglocs = self._prepare_guard(op, [loc, loc1, resloc, pos_exc_value, pos_exception])
        return arglocs

    def prepare_op_guard_no_exception(self, op, fcond):
        loc = self._ensure_value_is_boxed(
                    ConstInt(self.cpu.pos_exception()))
        arglocs = self._prepare_guard(op, [loc])
        return arglocs

    def prepare_op_guard_class(self, op, fcond):
        return self._prepare_guard_class(op, fcond)

    prepare_op_guard_nonnull_class = prepare_op_guard_class

    def _prepare_guard_class(self, op, fcond):
        assert isinstance(op.getarg(0), Box)
        boxes = list(op.getarglist())

        x = self._ensure_value_is_boxed(boxes[0], boxes)
        y = self.get_scratch_reg(REF, forbidden_vars=boxes)
        y_val = rffi.cast(lltype.Signed, op.getarg(1).getint())
        self.assembler.load(y, imm(y_val))

        offset = self.cpu.vtable_offset
        assert offset is not None
        offset_loc = self._ensure_value_is_boxed(ConstInt(offset), boxes)
        arglocs = self._prepare_guard(op, [x, y, offset_loc])

        return arglocs


    def prepare_op_jump(self, op, fcond):
        assembler = self.assembler
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        nonfloatlocs, floatlocs = descr._arm_arglocs

        # get temporary locs
        tmploc = r.ip
        box = TempFloat()
        # compute 'vfptmploc' to be all_regs[0] by spilling what is there
        vfptmp = self.vfprm.all_regs[0]
        vfptmploc = self.vfprm.force_allocate_reg(box, selected_reg=vfptmp)

        # Part about non-floats
        # XXX we don't need a copy, we only just the original list
        src_locations1 = [self.loc(op.getarg(i)) for i in range(op.numargs())
                         if op.getarg(i).type != FLOAT]
        assert tmploc not in nonfloatlocs
        dst_locations1 = [loc for loc in nonfloatlocs if loc is not None]
        # Part about floats
        src_locations2 = [self.loc(op.getarg(i)) for i in range(op.numargs())
                         if op.getarg(i).type == FLOAT]
        dst_locations2 = [loc for loc in floatlocs if loc is not None]
        remap_frame_layout_mixed(self.assembler,
                                 src_locations1, dst_locations1, tmploc,
                                 src_locations2, dst_locations2, vfptmploc)
        self.possibly_free_var(box)
        return []

    def prepare_op_setfield_gc(self, op, fcond):
        boxes = list(op.getarglist())
        a0, a1 = boxes
        ofs, size, ptr = self._unpack_fielddescr(op.getdescr())
        base_loc = self._ensure_value_is_boxed(a0, boxes)
        value_loc = self._ensure_value_is_boxed(a1, boxes)
        c_ofs = ConstInt(ofs)
        if _check_imm_arg(c_ofs):
            ofs_loc = imm(ofs)
        else:
            ofs_loc = self._ensure_value_is_boxed(c_ofs, boxes)
        return [value_loc, base_loc, ofs_loc, imm(size)]

    prepare_op_setfield_raw = prepare_op_setfield_gc

    def prepare_op_getfield_gc(self, op, fcond):
        a0 = op.getarg(0)
        ofs, size, ptr = self._unpack_fielddescr(op.getdescr())
        base_loc = self._ensure_value_is_boxed(a0)
        c_ofs = ConstInt(ofs)
        if _check_imm_arg(c_ofs):
            ofs_loc = imm(ofs)
        else:
            ofs_loc = self._ensure_value_is_boxed(c_ofs)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [base_loc, ofs_loc, res, imm(size)]

    prepare_op_getfield_raw = prepare_op_getfield_gc
    prepare_op_getfield_raw_pure = prepare_op_getfield_gc
    prepare_op_getfield_gc_pure = prepare_op_getfield_gc

    def prepare_op_getinteriorfield_gc(self, op, fcond):
        t = self._unpack_interiorfielddescr(op.getdescr())
        ofs, itemsize, fieldsize, sign = t
        args = op.getarglist()
        base_loc = self._ensure_value_is_boxed(op.getarg(0), args)
        index_loc = self._ensure_value_is_boxed(op.getarg(1), args)
        c_ofs = ConstInt(ofs)
        if _check_imm_arg(c_ofs):
            ofs_loc = imm(ofs)
        else:
            ofs_loc = self._ensure_value_is_boxed(c_ofs, args)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        result_loc = self.force_allocate_reg(op.result)
        return [base_loc, index_loc, result_loc, ofs_loc, imm(ofs), 
                                        imm(itemsize), imm(fieldsize)]

    
    def prepare_op_setinteriorfield_gc(self, op, fcond):
        t = self._unpack_interiorfielddescr(op.getdescr())
        ofs, itemsize, fieldsize, sign = t
        args = op.getarglist()
        base_loc = self._ensure_value_is_boxed(op.getarg(0), args)
        index_loc = self._ensure_value_is_boxed(op.getarg(1), args)
        value_loc = self._ensure_value_is_boxed(op.getarg(2), args)
        c_ofs = ConstInt(ofs)
        if _check_imm_arg(c_ofs):
            ofs_loc = imm(ofs)
        else:
            ofs_loc = self._ensure_value_is_boxed(c_ofs, boxes)
        return [base_loc, index_loc, value_loc, ofs_loc, imm(ofs),
                                        imm(itemsize), imm(fieldsize)]

    def prepare_op_arraylen_gc(self, op, fcond):
        arraydescr = op.getdescr()
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs = arraydescr.get_ofs_length(self.cpu.translate_support_code)
        arg = op.getarg(0)
        base_loc = self._ensure_value_is_boxed(arg)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [res, base_loc, imm(ofs)]

    def prepare_op_setarrayitem_gc(self, op, fcond):
        a0, a1, a2 = boxes = list(op.getarglist())
        _, scale, base_ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        args = op.getarglist()
        base_loc  = self._ensure_value_is_boxed(a0, args)
        ofs_loc = self._ensure_value_is_boxed(a1, args)
        value_loc = self._ensure_value_is_boxed(a2, args)
        assert _check_imm_arg(ConstInt(base_ofs))
        return [value_loc, base_loc, ofs_loc, imm(scale), imm(base_ofs)]
    prepare_op_setarrayitem_raw = prepare_op_setarrayitem_gc

    def prepare_op_getarrayitem_gc(self, op, fcond):
        a0, a1 = boxes = list(op.getarglist())
        _, scale, base_ofs, _, ptr = self._unpack_arraydescr(op.getdescr())

        base_loc  = self._ensure_value_is_boxed(a0, boxes)
        ofs_loc = self._ensure_value_is_boxed(a1, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        assert _check_imm_arg(ConstInt(base_ofs))
        return [res, base_loc, ofs_loc, imm(scale), imm(base_ofs)]

    prepare_op_getarrayitem_raw = prepare_op_getarrayitem_gc
    prepare_op_getarrayitem_gc_pure = prepare_op_getarrayitem_gc

    def prepare_op_strlen(self, op, fcond):
        args = op.getarglist()
        l0 = self._ensure_value_is_boxed(op.getarg(0))
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        ofs_box = ConstInt(ofs_length)
        imm_ofs = _check_imm_arg(ofs_box)

        if imm_ofs:
            l1 = self.make_sure_var_in_reg(ofs_box, args)
        else:
            l1, box1 = self._ensure_value_is_boxed(ofs_box, args)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()

        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, l1, res]

    def prepare_op_strgetitem(self, op, fcond):
        boxes = list(op.getarglist())
        base_loc = self._ensure_value_is_boxed(boxes[0])

        a1 = boxes[1]
        imm_a1 = _check_imm_arg(a1)
        if imm_a1:
            ofs_loc = self.make_sure_var_in_reg(a1, boxes)
        else:
            ofs_loc = self._ensure_value_is_boxed(a1, boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        assert itemsize == 1
        return [res, base_loc, ofs_loc, imm(basesize)]

    def prepare_op_strsetitem(self, op, fcond):
        boxes = list(op.getarglist())
        base_loc = self._ensure_value_is_boxed(boxes[0], boxes)
        ofs_loc = self._ensure_value_is_boxed(boxes[1], boxes)
        value_loc = self._ensure_value_is_boxed(boxes[2], boxes)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        assert itemsize == 1
        return [value_loc, base_loc, ofs_loc, imm(basesize)]

    prepare_op_copystrcontent = void
    prepare_op_copyunicodecontent = void

    def prepare_op_unicodelen(self, op, fcond):
        l0 = self._ensure_value_is_boxed(op.getarg(0))
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        ofs_box = ConstInt(ofs_length)
        imm_ofs = _check_imm_arg(ofs_box)

        if imm_ofs:
            l1 = imm(ofs_length)
        else:
            l1 = self._ensure_value_is_boxed(ofs_box, boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [l0, l1, res]

    def prepare_op_unicodegetitem(self, op, fcond):
        boxes = list(op.getarglist())
        base_loc = self._ensure_value_is_boxed(boxes[0], boxes)
        ofs_loc = self._ensure_value_is_boxed(boxes[1], boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        scale = itemsize/2
        return [res, base_loc, ofs_loc, imm(scale), imm(basesize), imm(itemsize)]

    def prepare_op_unicodesetitem(self, op, fcond):
        boxes = list(op.getarglist())
        base_loc = self._ensure_value_is_boxed(boxes[0], boxes)
        ofs_loc = self._ensure_value_is_boxed(boxes[1], boxes)
        value_loc = self._ensure_value_is_boxed(boxes[2], boxes)
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
            argloc = self._ensure_value_is_boxed(arg)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        resloc = self.force_allocate_reg(op.result)
        return [argloc, resloc]

    prepare_op_cast_ptr_to_int = prepare_op_same_as
    prepare_op_cast_int_to_ptr = prepare_op_same_as

    def prepare_op_new(self, op, fcond):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        if gc_ll_descr.can_inline_malloc(op.getdescr()):
            self.fastpath_malloc_fixedsize(op, op.getdescr())
        else:
            arglocs = self._prepare_args_for_new_op(op.getdescr())
            force_index = self.assembler.write_new_force_index()
            self.assembler._emit_call(force_index, self.assembler.malloc_func_addr,
                                    arglocs, self, fcond, result=op.result)
            self.possibly_free_vars(arglocs)
        self.possibly_free_var(op.result)
        return []

    def prepare_op_new_with_vtable(self, op, fcond):
        classint = op.getarg(0).getint()
        descrsize = heaptracker.vtable2descr(self.cpu, classint)
        if self.assembler.cpu.gc_ll_descr.can_inline_malloc(descrsize):
            self.fastpath_malloc_fixedsize(op, descrsize)
        else:
            callargs = self._prepare_args_for_new_op(descrsize)
            force_index = self.assembler.write_new_force_index()
            self.assembler._emit_call(force_index, self.assembler.malloc_func_addr,
                                        callargs, self, fcond, result=op.result)
            self.possibly_free_vars(callargs)
        self.possibly_free_var(op.result)
        return [imm(classint)]

    def prepare_op_new_array(self, op, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newarray is not None:
            # framework GC
            box_num_elem = op.getarg(0)
            if isinstance(box_num_elem, ConstInt):
                num_elem = box_num_elem.value
                if gc_ll_descr.can_inline_malloc_varsize(op.getdescr(),
                                                         num_elem):
                    self.fastpath_malloc_varsize(op, op.getdescr(), num_elem)
                    return []
            args = self.assembler.cpu.gc_ll_descr.args_for_new_array(
                op.getdescr())
            argboxes = [ConstInt(x) for x in args]
            argboxes.append(box_num_elem)
            force_index = self.assembler.write_new_force_index()
            self.assembler._emit_call(force_index, self.assembler.malloc_array_func_addr,
                                        argboxes, self, fcond, result=op.result)
            return []
        # boehm GC
        itemsize, scale, basesize, ofs_length, _ = (
            self._unpack_arraydescr(op.getdescr()))
        return self._malloc_varsize(basesize, ofs_length, itemsize, op)

    def fastpath_malloc_varsize(self, op, arraydescr, num_elem):
        assert isinstance(arraydescr, BaseArrayDescr)
        ofs_length = arraydescr.get_ofs_length(self.cpu.translate_support_code)
        basesize = arraydescr.get_base_size(self.cpu.translate_support_code)
        itemsize = arraydescr.get_item_size(self.cpu.translate_support_code)
        size = basesize + itemsize * num_elem
        self._do_fastpath_malloc(op, size, arraydescr.tid)
        # we know the resullt of the malloc call is in r0
        self.assembler.set_new_array_length(r.r0, ofs_length, num_elem)

    def fastpath_malloc_fixedsize(self, op, descr):
        assert isinstance(descr, BaseSizeDescr)
        self._do_fastpath_malloc(op, descr.size, descr.tid)

    def _do_fastpath_malloc(self, op, size, tid):
        gc_ll_descr = self.assembler.cpu.gc_ll_descr
        self.rm.force_allocate_reg(op.result, selected_reg=r.r0)
        t = TempInt()
        self.rm.force_allocate_reg(t, selected_reg=r.r1)
        self.possibly_free_var(op.result)
        self.possibly_free_var(t)

        self.assembler.malloc_cond(
            gc_ll_descr.get_nursery_free_addr(),
            gc_ll_descr.get_nursery_top_addr(),
            size, tid,
            )

    def get_mark_gc_roots(self, gcrootmap, use_copy_area=False):
        shape = gcrootmap.get_basic_shape(False)
        for v, val in self.frame_manager.frame_bindings.items():
            if (isinstance(v, BoxPtr) and self.rm.stays_alive(v)):
                assert val.is_stack()
                gcrootmap.add_frame_offset(shape, val.position*-WORD)
        for v, reg in self.rm.reg_bindings.items():
            if reg is r.r0:
                continue
            if (isinstance(v, BoxPtr) and self.rm.stays_alive(v)):
                if use_copy_area:
                    assert reg in self.rm.REGLOC_TO_COPY_AREA_OFS
                    area_offset = self.rm.REGLOC_TO_COPY_AREA_OFS[reg]
                    gcrootmap.add_frame_offset(shape, area_offset)
                else:
                    assert 0, 'sure??'
        return gcrootmap.compress_callshape(shape,
                                            self.assembler.datablockwrapper)
    def prepare_op_newstr(self, op, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newstr is not None:
            force_index = self.assembler.write_new_force_index()
            self.assembler._emit_call(force_index,
                    self.assembler.malloc_str_func_addr, [op.getarg(0)],
                    self, fcond, op.result)
            return []
        # boehm GC
        ofs_items, itemsize, ofs = symbolic.get_array_token(rstr.STR,
                            self.cpu.translate_support_code)
        assert itemsize == 1
        return self._malloc_varsize(ofs_items, ofs, itemsize, op)

    def prepare_op_newunicode(self, op, fcond):
        gc_ll_descr = self.cpu.gc_ll_descr
        if gc_ll_descr.get_funcptr_for_newunicode is not None:
            force_index = self.assembler.write_new_force_index()
            self.assembler._emit_call(force_index, self.assembler.malloc_unicode_func_addr,
                                    [op.getarg(0)], self, fcond, op.result)
            return []
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
            ofs_items_loc = self._ensure_value_is_boxed(ofs_items_box, boxes)
        vloc = self._ensure_value_is_boxed(v, [res_v])
        size = self._ensure_value_is_boxed(itemsize_box, boxes)
        self.assembler._regalloc_malloc_varsize(size, size_box,
                                vloc, vbox, ofs_items_loc, self, res_v)
        base_loc = self.make_sure_var_in_reg(res_v)

        value_loc = self._ensure_value_is_boxed(v, [res_v])
        assert value_loc.is_reg()
        assert base_loc.is_reg()
        return [value_loc, base_loc, imm(ofs_length)]

    prepare_op_debug_merge_point = void
    prepare_op_jit_debug = void

    def prepare_op_cond_call_gc_wb(self, op, fcond):
        assert op.result is None
        N = op.numargs()
        # we force all arguments in a reg (unless they are Consts),
        # because it will be needed anyway by the following setfield_gc
        # or setarrayitem_gc. It avoids loading it twice from the memory.
        arglocs = []
        args = op.getarglist()
        for i in range(N):
            loc = self._ensure_value_is_boxed(op.getarg(i), args)
            arglocs.append(loc)
        return arglocs

    prepare_op_cond_call_gc_wb_array = prepare_op_cond_call_gc_wb

    def prepare_op_force_token(self, op, fcond):
        res_loc = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [res_loc]

    def prepare_guard_call_may_force(self, op, guard_op, fcond):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self.assembler._write_fail_index(fail_index)
        args = [imm(rffi.cast(lltype.Signed, op.getarg(0).getint()))]
        for v in guard_op.getfailargs():
            if v in self.rm.reg_bindings or v in self.vfprm.reg_bindings:
                self.force_spill_var(v)
        self.assembler.emit_op_call(op, args, self, fcond, fail_index)
        locs = self._prepare_guard(guard_op)
        self.possibly_free_vars(guard_op.getfailargs())
        return locs

    def prepare_guard_call_release_gil(self, op, guard_op, fcond):
        # first, close the stack in the sense of the asmgcc GC root tracker
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            arglocs = []
            args = op.getarglist()
            for i in range(op.numargs()):
                loc = self._ensure_value_is_boxed(op.getarg(i), args)
                arglocs.append(loc)
            self.assembler.call_release_gil(gcrootmap, arglocs, fcond)
        # do the call
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        args = [imm(rffi.cast(lltype.Signed, op.getarg(0).getint()))]
        self.assembler.emit_op_call(op, args, self, fcond, fail_index)
        # then reopen the stack
        if gcrootmap:
            self.assembler.call_reacquire_gil(gcrootmap, r.r0, fcond)
        locs = self._prepare_guard(guard_op)
        return locs

    def prepare_guard_call_assembler(self, op, guard_op, fcond):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        jd = descr.outermost_jitdriver_sd
        assert jd is not None
        size = jd.portal_calldescr.get_result_size(self.cpu.translate_support_code)
        vable_index = jd.index_of_virtualizable
        if vable_index >= 0:
            self._sync_var(op.getarg(vable_index))
            vable = self.frame_manager.loc(op.getarg(vable_index))
        else:
            vable = imm(0)
        self.possibly_free_vars(guard_op.getfailargs())
        return [imm(size), vable]

    def _prepare_args_for_new_op(self, new_args):
        gc_ll_descr = self.cpu.gc_ll_descr
        args = gc_ll_descr.args_for_new(new_args)
        arglocs = []
        for i in range(len(args)):
            arg = args[i]
            t = TempInt()
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

    # from ../x86/regalloc.py:965
    def _unpack_interiorfielddescr(self, descr):
        assert isinstance(descr, InteriorFieldDescr)
        arraydescr = descr.arraydescr
        ofs = arraydescr.get_base_size(self.cpu.translate_support_code)
        itemsize = arraydescr.get_item_size(self.cpu.translate_support_code)
        fieldsize = descr.fielddescr.get_field_size(self.cpu.translate_support_code)
        sign = descr.fielddescr.is_field_signed()
        ofs += descr.fielddescr.offset
        return ofs, itemsize, fieldsize, sign

    prepare_op_float_add = prepare_float_op(name='prepare_op_float_add')
    prepare_op_float_sub = prepare_float_op(name='prepare_op_float_sub')
    prepare_op_float_mul = prepare_float_op(name='prepare_op_float_mul')
    prepare_op_float_truediv = prepare_float_op(name='prepare_op_float_truediv')
    prepare_op_float_lt = prepare_float_op(float_result=False, name='prepare_op_float_lt')
    prepare_op_float_le = prepare_float_op(float_result=False, name='prepare_op_float_le')
    prepare_op_float_eq = prepare_float_op(float_result=False, name='prepare_op_float_eq')
    prepare_op_float_ne = prepare_float_op(float_result=False, name='prepare_op_float_ne')
    prepare_op_float_gt = prepare_float_op(float_result=False, name='prepare_op_float_gt')
    prepare_op_float_ge = prepare_float_op(float_result=False, name='prepare_op_float_ge')
    prepare_op_float_neg = prepare_float_op(base=False, name='prepare_op_float_neg')
    prepare_op_float_abs = prepare_float_op(base=False, name='prepare_op_float_abs')

    prepare_guard_float_lt = prepare_float_op(guard=True, float_result=False, name='prepare_guard_float_lt')
    prepare_guard_float_le = prepare_float_op(guard=True, float_result=False, name='prepare_guard_float_le')
    prepare_guard_float_eq = prepare_float_op(guard=True, float_result=False, name='prepare_guard_float_eq')
    prepare_guard_float_ne = prepare_float_op(guard=True, float_result=False, name='prepare_guard_float_ne')
    prepare_guard_float_gt = prepare_float_op(guard=True, float_result=False, name='prepare_guard_float_gt')
    prepare_guard_float_ge = prepare_float_op(guard=True, float_result=False, name='prepare_guard_float_ge')

    def prepare_op_math_sqrt(self, op, fcond):
        loc = self._ensure_value_is_boxed(op.getarg(1))
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.vfprm.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [loc, res]

    def prepare_op_cast_float_to_int(self, op, fcond):
        loc1 = self._ensure_value_is_boxed(op.getarg(0))
        temp_loc = self.get_scratch_reg(FLOAT)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res  = self.rm.force_allocate_reg(op.result)
        return [loc1, temp_loc, res]

    def prepare_op_cast_int_to_float(self, op, fcond):
        loc1 = self._ensure_value_is_boxed(op.getarg(0))
        temp_loc = self.get_scratch_reg(FLOAT)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res  = self.vfprm.force_allocate_reg(op.result)
        return [loc1, temp_loc, res]

    def prepare_force_spill(self, op, fcond):
        self.force_spill_var(op.getarg(0))
        return []

def add_none_argument(fn):
    return lambda self, op, fcond: fn(self, op, None, fcond)

def notimplemented(self, op, fcond):
    raise NotImplementedError, op
def notimplemented_with_guard(self, op, guard_op, fcond):
    raise NotImplementedError, op

operations = [notimplemented] * (rop._LAST + 1)
operations_with_guard = [notimplemented_with_guard] * (rop._LAST + 1)

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'prepare_op_%s' % key
    if hasattr(Regalloc, methname):
        func = getattr(Regalloc, methname).im_func
        operations[value] = func

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'prepare_guard_%s' % key
    if hasattr(Regalloc, methname):
        func = getattr(Regalloc, methname).im_func
        operations_with_guard[value] = func
        operations[value] = add_none_argument(func)
