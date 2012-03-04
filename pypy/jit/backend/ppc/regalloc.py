from pypy.jit.backend.llsupport.regalloc import (RegisterManager, FrameManager,
                                                 TempBox, compute_vars_longevity)
from pypy.jit.backend.ppc.arch import (WORD, MY_COPY_OF_REGS)
from pypy.jit.backend.ppc.jump import remap_frame_layout
from pypy.jit.backend.ppc.locations import imm
from pypy.jit.backend.ppc.helper.regalloc import (_check_imm_arg,
                                                  prepare_cmp_op,
                                                  prepare_unary_int_op,
                                                  prepare_binary_int_op,
                                                  prepare_binary_int_op_with_imm,
                                                  prepare_unary_cmp)
from pypy.jit.metainterp.history import (Const, ConstInt, ConstPtr,
                                         Box, BoxPtr,
                                         INT, REF, FLOAT)
from pypy.jit.metainterp.history import JitCellToken, TargetToken
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.ppc import locations
from pypy.rpython.lltypesystem import rffi, lltype, rstr
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.backend.llsupport.descr import ArrayDescr
import pypy.jit.backend.ppc.register as r
from pypy.jit.backend.llsupport.descr import unpack_arraydescr
from pypy.jit.backend.llsupport.descr import unpack_fielddescr
from pypy.jit.backend.llsupport.descr import unpack_interiorfielddescr

# xxx hack: set a default value for TargetToken._arm_loop_code.  If 0, we know
# that it is a LABEL that was not compiled yet.
TargetToken._ppc_loop_code = 0

class TempInt(TempBox):
    type = INT

    def __repr__(self):
        return "<TempInt at %s>" % (id(self),)

class TempPtr(TempBox):
    type = REF

    def __repr__(self):
        return "<TempPtr at %s>" % (id(self),)

class PPCRegisterManager(RegisterManager):
    all_regs              = r.MANAGED_REGS
    box_types             = None       # or a list of acceptable types
    no_lower_byte_regs    = all_regs
    save_around_call_regs = r.VOLATILES

    REGLOC_TO_COPY_AREA_OFS = {
        r.r5:   MY_COPY_OF_REGS + 0 * WORD,
        r.r6:   MY_COPY_OF_REGS + 1 * WORD,
        r.r7:   MY_COPY_OF_REGS + 2 * WORD,
        r.r8:   MY_COPY_OF_REGS + 3 * WORD,
        r.r9:   MY_COPY_OF_REGS + 4 * WORD,
        r.r10:  MY_COPY_OF_REGS + 5 * WORD,
        r.r11:  MY_COPY_OF_REGS + 6 * WORD,
        r.r12:  MY_COPY_OF_REGS + 7 * WORD,
        r.r14:  MY_COPY_OF_REGS + 8 * WORD,
        r.r15:  MY_COPY_OF_REGS + 9 * WORD,
        r.r16:  MY_COPY_OF_REGS + 10 * WORD,
        r.r17:  MY_COPY_OF_REGS + 11 * WORD,
        r.r18:  MY_COPY_OF_REGS + 12 * WORD,
        r.r19:  MY_COPY_OF_REGS + 13 * WORD,
        r.r20:  MY_COPY_OF_REGS + 14 * WORD,
        r.r21:  MY_COPY_OF_REGS + 15 * WORD,
        r.r22:  MY_COPY_OF_REGS + 16 * WORD,
        r.r23:  MY_COPY_OF_REGS + 17 * WORD,
        r.r24:  MY_COPY_OF_REGS + 18 * WORD,
        r.r25:  MY_COPY_OF_REGS + 19 * WORD,
        r.r26:  MY_COPY_OF_REGS + 20 * WORD,
        r.r27:  MY_COPY_OF_REGS + 21 * WORD,
        r.r28:  MY_COPY_OF_REGS + 22 * WORD,
        r.r29:  MY_COPY_OF_REGS + 23 * WORD,
        r.r30:  MY_COPY_OF_REGS + 24 * WORD,
    }

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def call_result_location(self, v):
        return r.r3

    def convert_to_imm(self, c):
        if isinstance(c, ConstInt):
            val = rffi.cast(lltype.Signed, c.value)
            return locations.ImmLocation(val)
        else:
            assert isinstance(c, ConstPtr)
            return locations.ImmLocation(rffi.cast(lltype.Signed, c.value))

    def ensure_value_is_boxed(self, thing, forbidden_vars=None):
        loc = None
        if isinstance(thing, Const):
            if isinstance(thing, ConstPtr):
                tp = REF
            else:
                tp = INT
            loc = self.get_scratch_reg(tp, forbidden_vars=self.temp_boxes
                                                            + forbidden_vars)
            immvalue = self.convert_to_imm(thing)
            self.assembler.load(loc, immvalue)
        else:
            loc = self.make_sure_var_in_reg(thing,
                            forbidden_vars=self.temp_boxes + forbidden_vars)
        return loc

    def allocate_scratch_reg(self, type=INT, selected_reg=None, forbidden_vars=None):
        """Allocate a scratch register, possibly spilling a managed register.
        This register is freed after emitting the current operation and can not
        be spilled"""
        box = TempBox()
        reg = self.force_allocate_reg(box,
                            selected_reg=selected_reg,
                            forbidden_vars=forbidden_vars)
        return reg, box

    def get_scratch_reg(self, type=INT, forbidden_vars=[], selected_reg=None):
        assert type == INT or type == REF
        box = TempBox()
        self.temp_boxes.append(box)
        reg = self.force_allocate_reg(box, forbidden_vars=forbidden_vars,
                                                    selected_reg=selected_reg)
        return reg

class PPCFrameManager(FrameManager):
    def __init__(self):
        FrameManager.__init__(self)
        self.used = []

    @staticmethod
    def frame_pos(loc, type):
        num_words = PPCFrameManager.frame_size(type)
        if type == FLOAT:
            assert 0, "not implemented yet"
        return locations.StackLocation(loc, num_words=num_words, type=type)

    @staticmethod
    def frame_size(type):
        if type == FLOAT:
            assert 0, "TODO"
        return 1

    @staticmethod
    def get_loc_index(loc):
        assert loc.is_stack()
        if loc.type == FLOAT:
            assert 0, "not implemented yet"
        return loc.position

class Regalloc(object):

    def __init__(self, frame_manager=None, assembler=None):
        self.cpu = assembler.cpu
        self.frame_manager = frame_manager
        self.assembler = assembler
        self.jump_target_descr = None
        self.final_jump_op = None

    def _prepare(self,  inputargs, operations):
        longevity, last_real_usage = compute_vars_longevity(
                                                    inputargs, operations)
        self.longevity = longevity
        self.last_real_usage = last_real_usage
        fm = self.frame_manager
        asm = self.assembler
        self.rm = PPCRegisterManager(longevity, fm, asm)

    def prepare_loop(self, inputargs, operations):
        self._prepare(inputargs, operations)
        self._set_initial_bindings(inputargs)
        self.possibly_free_vars(inputargs)

    def prepare_bridge(self, inputargs, arglocs, ops):
        self._prepare(inputargs, ops)
        self._update_bindings(arglocs, inputargs)

    def _set_initial_bindings(self, inputargs):
        arg_index = 0
        count = 0
        n_register_args = len(r.PARAM_REGS)
        cur_frame_pos = -self.assembler.OFFSET_STACK_ARGS // WORD + 1
        for box in inputargs:
            assert isinstance(box, Box)
            # handle inputargs in argument registers
            if box.type == FLOAT and arg_index % 2 != 0:
                assert 0, "not implemented yet"
            if arg_index < n_register_args:
                if box.type == FLOAT:
                    assert 0, "not implemented yet"
                else:
                    loc = r.PARAM_REGS[arg_index]
                    self.try_allocate_reg(box, selected_reg=loc)
                    arg_index += 1
            else:
                # treat stack args as stack locations with a negative offset
                if box.type == FLOAT:
                    assert 0, "not implemented yet"
                else:
                    cur_frame_pos -= 1
                    count += 1
                loc = self.frame_manager.frame_pos(cur_frame_pos, box.type)
                self.frame_manager.set_binding(box, loc)

    def _update_bindings(self, locs, inputargs):
        used = {}
        i = 0
        for loc in locs:
            arg = inputargs[i]
            i += 1
            if loc.is_reg():
                self.rm.reg_bindings[arg] = loc
            elif loc.is_vfp_reg():
                assert 0, "not supported"
            else:
                assert loc.is_stack()
                self.frame_manager.set_binding(arg, loc)
            used[loc] = None

        # XXX combine with x86 code and move to llsupport
        self.rm.free_regs = []
        for reg in self.rm.all_regs:
            if reg not in used:
                self.rm.free_regs.append(reg)
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))

    def possibly_free_var(self, var):
        self.rm.possibly_free_var(var)

    def possibly_free_vars(self, vars):
        for var in vars:
            self.possibly_free_var(var)

    def possibly_free_vars_for_op(self, op):
        for i in range(op.numargs()):
            var = op.getarg(i)
            if var is not None:
                self.possibly_free_var(var)

    def try_allocate_reg(self, v, selected_reg=None, need_lower_byte=False):
        return self.rm.try_allocate_reg(v, selected_reg, need_lower_byte)

    def force_allocate_reg(self, var, forbidden_vars=[], selected_reg=None, 
            need_lower_byte=False):
        return self.rm.force_allocate_reg(var, forbidden_vars, selected_reg,
                need_lower_byte)

    def allocate_scratch_reg(self, type=INT, forbidden_vars=[], selected_reg=None):
        assert type == INT # XXX extend this once floats are supported
        return self.rm.allocate_scratch_reg(type=type,
                        forbidden_vars=forbidden_vars,
                        selected_reg=selected_reg)

    def _check_invariants(self):
        self.rm._check_invariants()

    def loc(self, var):
        if var.type == FLOAT:
            assert 0, "not implemented yet"
        return self.rm.loc(var)

    def position(self):
        return self.rm.position

    def next_instruction(self):
        self.rm.next_instruction()

    def force_spill_var(self, var):
        if var.type == FLOAT:
            assert 0, "not implemented yet"
        else:
            self.rm.force_spill_var(var)

    def before_call(self, force_store=[], save_all_regs=False):
        self.rm.before_call(force_store, save_all_regs)

    def after_call(self, v):
        if v.type == FLOAT:
            assert 0, "not implemented yet"
        else:
            return self.rm.after_call(v)

    def call_result_location(self, v):
        if v.type == FLOAT:
            assert 0, "not implemented yet"
        else:
            return self.rm.call_result_location(v)

    def _ensure_value_is_boxed(self, thing, forbidden_vars=[]):
        if thing.type == FLOAT:
            assert 0, "not implemented yet"
        else:
            return self.rm.ensure_value_is_boxed(thing, forbidden_vars)

    def get_scratch_reg(self, type, forbidden_vars=[], selected_reg=None):
        if type == FLOAT:
            assert 0, "not implemented yet"
        else:
            return self.rm.get_scratch_reg(type, forbidden_vars, selected_reg)

    def free_temp_vars(self):
        self.rm.free_temp_vars()

    def make_sure_var_in_reg(self, var, forbidden_vars=[],
                             selected_reg=None, need_lower_byte=False):
        if var.type == FLOAT:
            assert 0, "not implemented yet"
        else:
           return self.rm.make_sure_var_in_reg(var, forbidden_vars,
                    selected_reg, need_lower_byte)

    def convert_to_imm(self, value):
        if isinstance(value, ConstInt):
            return self.rm.convert_to_imm(value)
        else:
            assert 0, "not implemented yet"

    def _sync_var(self, v):
        if v.type == FLOAT:
            assert 0, "not implemented yet"
        else:
            self.rm._sync_var(v)

    # ******************************************************
    # *         P R E P A R E  O P E R A T I O N S         * 
    # ******************************************************


    def void(self, op):
        return []

    prepare_int_add = prepare_binary_int_op_with_imm()
    prepare_int_sub = prepare_binary_int_op_with_imm()
    prepare_int_floordiv = prepare_binary_int_op_with_imm()

    prepare_int_mul = prepare_binary_int_op()
    prepare_int_mod = prepare_binary_int_op()
    prepare_int_and = prepare_binary_int_op()
    prepare_int_or = prepare_binary_int_op()
    prepare_int_xor = prepare_binary_int_op()
    prepare_int_lshift = prepare_binary_int_op()
    prepare_int_rshift = prepare_binary_int_op()
    prepare_uint_rshift = prepare_binary_int_op()
    prepare_uint_floordiv = prepare_binary_int_op()

    prepare_int_add_ovf = prepare_binary_int_op()
    prepare_int_sub_ovf = prepare_binary_int_op()
    prepare_int_mul_ovf = prepare_binary_int_op()

    prepare_int_neg = prepare_unary_int_op()
    prepare_int_invert = prepare_unary_int_op()

    prepare_int_le = prepare_cmp_op()
    prepare_int_lt = prepare_cmp_op()
    prepare_int_ge = prepare_cmp_op()
    prepare_int_gt = prepare_cmp_op()
    prepare_int_eq = prepare_cmp_op()
    prepare_int_ne = prepare_cmp_op()

    prepare_ptr_eq = prepare_int_eq
    prepare_ptr_ne = prepare_int_ne

    prepare_instance_ptr_eq = prepare_ptr_eq
    prepare_instance_ptr_ne = prepare_ptr_ne

    prepare_uint_lt = prepare_cmp_op()
    prepare_uint_le = prepare_cmp_op()
    prepare_uint_gt = prepare_cmp_op()
    prepare_uint_ge = prepare_cmp_op()

    prepare_int_is_true = prepare_unary_cmp()
    prepare_int_is_zero = prepare_unary_cmp()

    def prepare_finish(self, op):
        args = [None] * (op.numargs() + 1)
        for i in range(op.numargs()):
            arg = op.getarg(i)
            if arg:
                args[i] = self.loc(arg)
                self.possibly_free_var(arg)
        n = self.cpu.get_fail_descr_number(op.getdescr())
        args[-1] = imm(n)
        return args

    def prepare_call_malloc_gc(self, op):
        args = [imm(rffi.cast(lltype.Signed, op.getarg(0).getint()))]
        return args

    def _prepare_guard(self, op, args=None):
        if args is None:
            args = []
        args.append(imm(len(self.frame_manager.used)))
        for arg in op.getfailargs():
            if arg:
                args.append(self.loc(arg))
            else:
                args.append(None)
        return args
    
    def prepare_guard_true(self, op):
        l0 = self._ensure_value_is_boxed(op.getarg(0))
        args = self._prepare_guard(op, [l0])
        return args

    prepare_guard_false = prepare_guard_true
    prepare_guard_nonnull = prepare_guard_true
    prepare_guard_isnull = prepare_guard_true

    def prepare_guard_no_overflow(self, op):
        locs = self._prepare_guard(op)
        self.possibly_free_vars(op.getfailargs())
        return locs

    prepare_guard_overflow = prepare_guard_no_overflow
    prepare_guard_not_invalidated = prepare_guard_no_overflow

    def prepare_guard_exception(self, op):
        boxes = op.getarglist()
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
        arglocs = self._prepare_guard(op,
                    [loc, loc1, resloc, pos_exc_value, pos_exception])
        return arglocs

    def prepare_guard_no_exception(self, op):
        loc = self._ensure_value_is_boxed(
                    ConstInt(self.cpu.pos_exception()))
        arglocs = self._prepare_guard(op, [loc])
        return arglocs

    def prepare_guard_value(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        l0 = self._ensure_value_is_boxed(a0, boxes)
        l1 = self._ensure_value_is_boxed(a1, boxes)
        assert op.result is None
        arglocs = self._prepare_guard(op, [l0, l1])
        self.possibly_free_vars(op.getarglist())
        self.possibly_free_vars(op.getfailargs())
        return arglocs

    def prepare_guard_class(self, op):
        assert isinstance(op.getarg(0), Box)
        boxes = op.getarglist()

        x = self._ensure_value_is_boxed(boxes[0], boxes)
        y = self.get_scratch_reg(INT, forbidden_vars=boxes)
        y_val = rffi.cast(lltype.Signed, op.getarg(1).getint())
        self.assembler.load(y, imm(y_val))

        offset = self.cpu.vtable_offset
        assert offset is not None
        assert _check_imm_arg(offset)
        offset_loc = imm(offset)
        arglocs = self._prepare_guard(op, [x, y, offset_loc])

        return arglocs

    prepare_guard_nonnull_class = prepare_guard_class

    def compute_hint_frame_locations(self, operations):
        # optimization only: fill in the 'hint_frame_locations' dictionary
        # of rm and xrm based on the JUMP at the end of the loop, by looking
        # at where we would like the boxes to be after the jump.
        op = operations[-1]
        if op.getopnum() != rop.JUMP:
            return
        self.final_jump_op = op
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        if descr._ppc_loop_code != 0:
            # if the target LABEL was already compiled, i.e. if it belongs
            # to some already-compiled piece of code
            self._compute_hint_frame_locations_from_descr(descr)
        #else:
        #   The loop ends in a JUMP going back to a LABEL in the same loop.
        #   We cannot fill 'hint_frame_locations' immediately, but we can
        #   wait until the corresponding prepare_op_label() to know where the
        #   we would like the boxes to be after the jump.

    def _compute_hint_frame_locations_from_descr(self, descr):
        arglocs = self.assembler.target_arglocs(descr)
        jump_op = self.final_jump_op
        assert len(arglocs) == jump_op.numargs()
        for i in range(jump_op.numargs()):
            box = jump_op.getarg(i)
            if isinstance(box, Box):
                loc = arglocs[i]
                if loc is not None and loc.is_stack():
                    self.frame_manager.hint_frame_locations[box] = loc

    def prepare_guard_call_release_gil(self, op, guard_op):
        # first, close the stack in the sense of the asmgcc GC root tracker
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            arglocs = []
            args = op.getarglist()
            for i in range(op.numargs()):
                loc = self._ensure_value_is_boxed(op.getarg(i), args)
                arglocs.append(loc)
            self.assembler.call_release_gil(gcrootmap, arglocs)
        # do the call
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self.assembler._write_fail_index(fail_index)
        args = [imm(rffi.cast(lltype.Signed, op.getarg(0).getint()))]
        self.assembler.emit_call(op, args, self, fail_index)
        # then reopen the stack
        if gcrootmap:
            if op.result:
                result_loc = self.call_result_location(op.result)
            else:
                result_loc = None
            self.assembler.call_reacquire_gil(gcrootmap, result_loc)
        locs = self._prepare_guard(guard_op)
        self.possibly_free_vars(guard_op.getfailargs())
        return locs

    def prepare_jump(self, op):
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        self.jump_target_descr = descr
        arglocs = self.assembler.target_arglocs(descr)

        # get temporary locs
        tmploc = r.SCRATCH

        # Part about non-floats
        src_locations1 = []
        dst_locations1 = []

        # Build the four lists
        for i in range(op.numargs()):
            box = op.getarg(i)
            src_loc = self.loc(box)
            dst_loc = arglocs[i]
            if box.type != FLOAT:
                src_locations1.append(src_loc)
                dst_locations1.append(dst_loc)
            else:
                assert 0, "not implemented yet"

        remap_frame_layout(self.assembler, src_locations1,
                dst_locations1, tmploc)
        return []

    def prepare_setfield_gc(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        ofs, size, sign = unpack_fielddescr(op.getdescr())
        base_loc = self._ensure_value_is_boxed(a0, boxes)
        value_loc = self._ensure_value_is_boxed(a1, boxes)
        if _check_imm_arg(ofs):
            ofs_loc = imm(ofs)
        else:
            ofs_loc = self.get_scratch_reg(INT, boxes)
            self.assembler.load(ofs_loc, imm(ofs))
        return [value_loc, base_loc, ofs_loc, imm(size)]

    prepare_setfield_raw = prepare_setfield_gc

    def prepare_getfield_gc(self, op):
        a0 = op.getarg(0)
        ofs, size, sign = unpack_fielddescr(op.getdescr())
        base_loc = self._ensure_value_is_boxed(a0)
        immofs = imm(ofs)
        if _check_imm_arg(ofs):
            ofs_loc = immofs
        else:
            ofs_loc = self.get_scratch_reg(INT, [a0])
            self.assembler.load(ofs_loc, immofs)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [base_loc, ofs_loc, res, imm(size)]

    prepare_getfield_raw = prepare_getfield_gc
    prepare_getfield_raw_pure = prepare_getfield_gc
    prepare_getfield_gc_pure = prepare_getfield_gc

    def prepare_getinteriorfield_gc(self, op):
        t = unpack_interiorfielddescr(op.getdescr())
        ofs, itemsize, fieldsize, sign = t
        args = op.getarglist()
        base_loc = self._ensure_value_is_boxed(op.getarg(0), args)
        index_loc = self._ensure_value_is_boxed(op.getarg(1), args)
        if _check_imm_arg(ofs):
            ofs_loc = imm(ofs)
        else:
            ofs_loc = self._ensure_value_is_boxed(ConstInt(ofs), args)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        result_loc = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [base_loc, index_loc, result_loc, ofs_loc, imm(ofs),
                                    imm(itemsize), imm(fieldsize)]
    prepare_getinteriorfield_raw = prepare_getinteriorfield_gc

    def prepare_setinteriorfield_gc(self, op):
        t = unpack_interiorfielddescr(op.getdescr())
        ofs, itemsize, fieldsize, sign = t
        args = op.getarglist()
        base_loc = self._ensure_value_is_boxed(op.getarg(0), args)
        index_loc = self._ensure_value_is_boxed(op.getarg(1), args)
        value_loc = self._ensure_value_is_boxed(op.getarg(2), args)
        if _check_imm_arg(ofs):
            ofs_loc = imm(ofs)
        else:
            ofs_loc = self._ensure_value_is_boxed(ConstInt(ofs), args)
        return [base_loc, index_loc, value_loc, ofs_loc, imm(ofs),
                                        imm(itemsize), imm(fieldsize)]
    prepare_setinteriorfield_raw = prepare_setinteriorfield_gc

    def prepare_arraylen_gc(self, op):
        arraydescr = op.getdescr()
        assert isinstance(arraydescr, ArrayDescr)
        ofs = arraydescr.lendescr.offset
        arg = op.getarg(0)
        base_loc = self._ensure_value_is_boxed(arg)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [res, base_loc, imm(ofs)]

    def prepare_setarrayitem_gc(self, op):
        size, ofs, _ = unpack_arraydescr(op.getdescr())
        scale = get_scale(size)
        args = op.getarglist()
        base_loc = self._ensure_value_is_boxed(args[0], args)
        ofs_loc = self._ensure_value_is_boxed(args[1], args)
        value_loc = self._ensure_value_is_boxed(args[2], args)
        scratch_loc = self.rm.get_scratch_reg(INT, args)
        assert _check_imm_arg(ofs)
        return [value_loc, base_loc, ofs_loc, scratch_loc, imm(scale), imm(ofs)]
    prepare_setarrayitem_raw = prepare_setarrayitem_gc

    def prepare_getarrayitem_gc(self, op):
        boxes = op.getarglist()
        size, ofs, _ = unpack_arraydescr(op.getdescr())
        scale = get_scale(size)
        base_loc = self._ensure_value_is_boxed(boxes[0], boxes)
        ofs_loc = self._ensure_value_is_boxed(boxes[1], boxes)
        scratch_loc = self.rm.get_scratch_reg(INT, boxes)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        assert _check_imm_arg(ofs)
        return [res, base_loc, ofs_loc, scratch_loc, imm(scale), imm(ofs)]

    prepare_getarrayitem_raw = prepare_getarrayitem_gc
    prepare_getarrayitem_gc_pure = prepare_getarrayitem_gc

    def prepare_strlen(self, op):
        args = op.getarglist()
        l0 = self._ensure_value_is_boxed(op.getarg(0))
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        immofs = imm(ofs_length)
        if _check_imm_arg(ofs_length):
            l1 = immofs
        else:
            l1 = self.get_scratch_reg(INT, args)
            self.assembler.load(l1, immofs)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()

        res = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [l0, l1, res]

    def prepare_strgetitem(self, op):
        boxes = op.getarglist()
        base_loc = self._ensure_value_is_boxed(boxes[0])

        a1 = boxes[1]
        ofs_loc = self._ensure_value_is_boxed(a1, boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        assert itemsize == 1
        return [res, base_loc, ofs_loc, imm(basesize)]

    def prepare_strsetitem(self, op):
        boxes = op.getarglist()
        base_loc = self._ensure_value_is_boxed(boxes[0], boxes)
        ofs_loc = self._ensure_value_is_boxed(boxes[1], boxes)
        value_loc = self._ensure_value_is_boxed(boxes[2], boxes)
        temp_loc = self.get_scratch_reg(INT, boxes)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                         self.cpu.translate_support_code)
        assert itemsize == 1
        return [value_loc, base_loc, ofs_loc, temp_loc, imm(basesize)]

    prepare_copystrcontent = void
    prepare_copyunicodecontent = void

    def prepare_unicodelen(self, op):
        l0 = self._ensure_value_is_boxed(op.getarg(0))
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        immofs = imm(ofs_length)
        if _check_imm_arg(ofs_length):
            l1 = immofs
        else:
            l1 = self.get_scratch_reg(INT, [op.getarg(0)])
            self.assembler.load(l1, immofs)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)
        return [l0, l1, res]

    def prepare_unicodegetitem(self, op):
        boxes = op.getarglist()
        base_loc = self._ensure_value_is_boxed(boxes[0], boxes)
        ofs_loc = self._ensure_value_is_boxed(boxes[1], boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        res = self.force_allocate_reg(op.result)

        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        scale = itemsize / 2
        return [res, base_loc, ofs_loc,
            imm(scale), imm(basesize), imm(itemsize)]

    def prepare_unicodesetitem(self, op):
        boxes = op.getarglist()
        base_loc = self._ensure_value_is_boxed(boxes[0], boxes)
        ofs_loc = self._ensure_value_is_boxed(boxes[1], boxes)
        value_loc = self._ensure_value_is_boxed(boxes[2], boxes)
        temp_loc = self.get_scratch_reg(INT, boxes)
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                         self.cpu.translate_support_code)
        scale = itemsize / 2
        return [value_loc, base_loc, ofs_loc, temp_loc,
            imm(scale), imm(basesize), imm(itemsize)]

    def prepare_same_as(self, op):
        arg = op.getarg(0)
        argloc = self._ensure_value_is_boxed(arg)
        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        resloc = self.force_allocate_reg(op.result)
        return [argloc, resloc]

    prepare_cast_ptr_to_int = prepare_same_as
    prepare_cast_int_to_ptr = prepare_same_as

    def prepare_call(self, op):
        effectinfo = op.getdescr().get_extra_info()
        if effectinfo is not None:
	    # XXX TODO
            #oopspecindex = effectinfo.oopspecindex
            #if oopspecindex == EffectInfo.OS_MATH_SQRT:
            #    args = self.prepare_op_math_sqrt(op, fcond)
            #    self.assembler.emit_op_math_sqrt(op, args, self, fcond)
            #    return
            pass
        args = [imm(rffi.cast(lltype.Signed, op.getarg(0).getint()))]
        return args

    def prepare_call_malloc_nursery(self, op):
        size_box = op.getarg(0)
        assert isinstance(size_box, ConstInt)
        size = size_box.getint()

        self.rm.force_allocate_reg(op.result, selected_reg=r.r3)
        t = TempInt()
        self.rm.force_allocate_reg(t, selected_reg=r.r4)
        self.possibly_free_var(op.result)
        self.possibly_free_var(t)
        return [imm(size)]

    def get_mark_gc_roots(self, gcrootmap, use_copy_area=False):
        shape = gcrootmap.get_basic_shape(False)
        for v, val in self.frame_manager.bindings.items():
            if (isinstance(v, BoxPtr) and self.rm.stays_alive(v)):
                assert val.is_stack()
                gcrootmap.add_frame_offset(shape, val.position * -WORD)
        for v, reg in self.rm.reg_bindings.items():
            if reg is r.r3:
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

    prepare_debug_merge_point = void
    prepare_jit_debug = void
    prepare_keepalive = void

    def prepare_cond_call_gc_wb(self, op):
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

    prepare_cond_call_gc_wb_array = prepare_cond_call_gc_wb

    def prepare_force_token(self, op):
        res_loc = self.force_allocate_reg(op.result)
        self.possibly_free_var(op.result)
        return [res_loc]

    def prepare_label(self, op):
        # XXX big refactoring needed?
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        inputargs = op.getarglist()
        arglocs = [None] * len(inputargs)
        #
        # we use force_spill() on the boxes that are not going to be really
        # used any more in the loop, but that are kept alive anyway
        # by being in a next LABEL's or a JUMP's argument or fail_args
        # of some guard
        position = self.rm.position
        for arg in inputargs:
            assert isinstance(arg, Box)
            if self.last_real_usage.get(arg, -1) <= position:
                self.force_spill_var(arg)

        #
        for i in range(len(inputargs)):
            arg = inputargs[i]
            assert isinstance(arg, Box)
            loc = self.loc(arg)
            arglocs[i] = loc
            if loc.is_reg():
                self.frame_manager.mark_as_free(arg)
        #
        descr._ppc_arglocs = arglocs
        descr._ppc_loop_code = self.assembler.mc.currpos()
        descr._ppc_clt = self.assembler.current_clt
        self.assembler.target_tokens_currently_compiling[descr] = None
        self.possibly_free_vars_for_op(op)
        #
        # if the LABEL's descr is precisely the target of the JUMP at the
        # end of the same loop, i.e. if what we are compiling is a single
        # loop that ends up jumping to this LABEL, then we can now provide
        # the hints about the expected position of the spilled variables.
        jump_op = self.final_jump_op
        if jump_op is not None and jump_op.getdescr() is descr:
            self._compute_hint_frame_locations_from_descr(descr)

    def prepare_guard_call_may_force(self, op, guard_op):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self.assembler._write_fail_index(fail_index)
        args = [imm(rffi.cast(lltype.Signed, op.getarg(0).getint()))]
        for v in guard_op.getfailargs():
            if v in self.rm.reg_bindings:
                self.force_spill_var(v)
        self.assembler.emit_call(op, args, self, fail_index)
        locs = self._prepare_guard(guard_op)
        self.possibly_free_vars(guard_op.getfailargs())
        return locs

    def prepare_guard_call_assembler(self, op, guard_op):
        descr = op.getdescr()
        assert isinstance(descr, JitCellToken)
        jd = descr.outermost_jitdriver_sd
        assert jd is not None
        #size = jd.portal_calldescr.get_result_size(self.cpu.translate_support_code)
        size = jd.portal_calldescr.get_result_size()
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
            l = self.force_allocate_reg(t, selected_reg=r.MANAGED_REGS[i])
            self.assembler.load(l, imm(arg))
            arglocs.append(t)
        return arglocs

    def prepare_force_spill(self, op):
        self.force_spill_var(op.getarg(0))
        return []

def add_none_argument(fn):
    return lambda self, op: fn(self, op, None)

def notimplemented(self, op):
    print "[PPC/regalloc] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

def notimplemented_with_guard(self, op, guard_op):
    print "[PPC/regalloc] %s with guard %s not implemented" % \
            (op.getopname(), guard_op.getopname())
    raise NotImplementedError(op)



operations = [notimplemented] * (rop._LAST + 1)
operations_with_guard = [notimplemented_with_guard] * (rop._LAST + 1)

def get_scale(size):
    scale = 0
    while (1 << scale) < size:
        scale += 1
    assert (1 << scale) == size
    return scale

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'prepare_%s' % key
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

Regalloc.operations = operations
Regalloc.operations_with_guard = operations_with_guard
