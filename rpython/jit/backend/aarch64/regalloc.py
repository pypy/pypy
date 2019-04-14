
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.aarch64 import locations
from rpython.jit.backend.arm import conditions as c
from rpython.jit.backend.aarch64.arch import WORD, JITFRAME_FIXED_SIZE

from rpython.jit.metainterp.history import (Const, ConstInt, ConstFloat,
                                            ConstPtr,
                                            INT, REF, FLOAT)
from rpython.jit.metainterp.history import TargetToken
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.backend.llsupport.regalloc import FrameManager, \
        RegisterManager, TempVar, compute_vars_longevity, BaseRegalloc, \
        get_scale
from rpython.rtyper.lltypesystem import lltype, rffi, rstr, llmemory
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.arm.jump import remap_frame_layout_mixed
from rpython.jit.backend.aarch64.locations import imm
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap



class TempInt(TempVar):
    type = INT

    def __repr__(self):
        return "<TempInt at %s>" % (id(self),)


class TempPtr(TempVar):
    type = REF

    def __repr__(self):
        return "<TempPtr at %s>" % (id(self),)


class TempFloat(TempVar):
    type = FLOAT

    def __repr__(self):
        return "<TempFloat at %s>" % (id(self),)


class ARMFrameManager(FrameManager):

    def __init__(self, base_ofs):
        FrameManager.__init__(self)
        self.base_ofs = base_ofs

    def frame_pos(self, i, box_type):
        return locations.StackLocation(i, locations.get_fp_offset(self.base_ofs, i), box_type)

    @staticmethod
    def frame_size(type):
        return 1

    @staticmethod
    def get_loc_index(loc):
        assert loc.is_stack()
        return loc.position

class ARMRegisterManager(RegisterManager):
    def return_constant(self, v, forbidden_vars=[], selected_reg=None):
        self._check_type(v)
        if isinstance(v, Const):
            if isinstance(v, ConstPtr):
                tp = REF
            elif isinstance(v, ConstFloat):
                tp = FLOAT
            else:
                tp = INT
            loc = self.get_scratch_reg(tp,
                    self.temp_boxes + forbidden_vars,
                    selected_reg=selected_reg)
            immvalue = self.convert_to_imm(v)
            self.assembler.load(loc, immvalue)
            return loc
        else:
            return RegisterManager.return_constant(self, v,
                                    forbidden_vars, selected_reg)


class VFPRegisterManager(ARMRegisterManager):
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
        reg = self.force_allocate_reg(v, selected_reg=r.d0)
        return reg

    def get_scratch_reg(self, type=FLOAT, forbidden_vars=[], selected_reg=None):
        assert type == FLOAT  # for now
        box = TempFloat()
        self.temp_boxes.append(box)
        reg = self.force_allocate_reg(box, forbidden_vars=forbidden_vars,
                                                    selected_reg=selected_reg)
        return reg


class CoreRegisterManager(ARMRegisterManager):
    all_regs = r.all_regs
    box_types = None       # or a list of acceptable types
    no_lower_byte_regs = all_regs
    save_around_call_regs = r.caller_resp
    frame_reg = r.fp

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def call_result_location(self, v):
        return r.r0

    def convert_to_imm(self, c):
        if isinstance(c, ConstInt):
            val = rffi.cast(lltype.Signed, c.value)
            return locations.ImmLocation(val)
        else:
            assert isinstance(c, ConstPtr)
            return locations.ImmLocation(rffi.cast(lltype.Signed, c.value))
        assert 0

    def get_scratch_reg(self, type=INT, forbidden_vars=[], selected_reg=None):
        assert type == INT or type == REF
        box = None
        if type == INT:
            box = TempInt()
        else:
            box = TempPtr()
        self.temp_boxes.append(box)
        reg = self.force_allocate_reg(box, forbidden_vars=forbidden_vars,
                                                    selected_reg=selected_reg)
        return reg

    def get_free_reg(self):
        free_regs = self.free_regs
        for i in range(len(free_regs) - 1, -1, -1):
            if free_regs[i] in self.save_around_call_regs:
                continue
            return free_regs[i]

DEFAULT_IMM_SIZE = 4096

def check_imm_arg(arg, size=DEFAULT_IMM_SIZE, allow_zero=True):
    i = arg
    if allow_zero:
        lower_bound = i >= 0
    else:
        lower_bound = i > 0
    return i <= size and lower_bound

def check_imm_box(arg, size=DEFAULT_IMM_SIZE, allow_zero=True):
    if isinstance(arg, ConstInt):
        return check_imm_arg(arg.getint(), size, allow_zero)
    return False


class Regalloc(BaseRegalloc):

    def __init__(self, assembler):
        self.cpu = assembler.cpu
        self.assembler = assembler
        self.frame_manager = None
        self.jump_target_descr = None
        self.final_jump_op = None

    def _prepare(self, inputargs, operations, allgcrefs):
        cpu = self.cpu
        self.fm = ARMFrameManager(cpu.get_baseofs_of_frame_field())
        self.frame_manager = self.fm
        operations = cpu.gc_ll_descr.rewrite_assembler(cpu, operations,
                                                       allgcrefs)
        # compute longevity of variables
        longevity, last_real_usage = compute_vars_longevity(inputargs, operations)
        self.longevity = longevity
        self.last_real_usage = last_real_usage
        fm = self.frame_manager
        asm = self.assembler
        self.vfprm = VFPRegisterManager(longevity, fm, asm)
        self.rm = CoreRegisterManager(longevity, fm, asm)
        return operations

    def prepare_loop(self, inputargs, operations, looptoken, allgcrefs):
        operations = self._prepare(inputargs, operations, allgcrefs)
        self._set_initial_bindings(inputargs, looptoken)
        self.possibly_free_vars(list(inputargs))
        return operations

    def loc(self, var):
        if var.type == FLOAT:
            return self.vfprm.loc(var)
        else:
            return self.rm.loc(var)

    def possibly_free_var(self, var):
        if var.type == FLOAT:
            self.vfprm.possibly_free_var(var)
        else:
            self.rm.possibly_free_var(var)

    def possibly_free_vars_for_op(self, op):
        for i in range(op.numargs()):
            var = op.getarg(i)
            if var is not None:  # xxx kludgy
                self.possibly_free_var(var)

    def possibly_free_vars(self, vars):
        for var in vars:
            if var is not None:  # xxx kludgy
                self.possibly_free_var(var)

    def get_scratch_reg(self, type, forbidden_vars=[], selected_reg=None):
        if type == FLOAT:
            return self.vfprm.get_scratch_reg(type, forbidden_vars,
                                                                selected_reg)
        else:
            return self.rm.get_scratch_reg(type, forbidden_vars, selected_reg)

    def get_free_reg(self):
        return self.rm.get_free_reg()

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
        if descr._ll_loop_code != 0:
            # if the target LABEL was already compiled, i.e. if it belongs
            # to some already-compiled piece of code
            self._compute_hint_frame_locations_from_descr(descr)
        #else:
        #   The loop ends in a JUMP going back to a LABEL in the same loop.
        #   We cannot fill 'hint_frame_locations' immediately, but we can
        #   wait until the corresponding prepare_op_label() to know where the
        #   we would like the boxes to be after the jump.

    def _compute_hint_frame_locations_from_descr(self, descr):
        arglocs = descr._arm_arglocs
        jump_op = self.final_jump_op
        assert len(arglocs) == jump_op.numargs()
        for i in range(jump_op.numargs()):
            box = jump_op.getarg(i)
            if not isinstance(box, Const):
                loc = arglocs[i]
                if loc is not None and loc.is_stack():
                    self.frame_manager.hint_frame_pos[box] = (
                        self.fm.get_loc_index(loc))

    def position(self):
        return self.rm.position

    def next_instruction(self):
        self.rm.next_instruction()
        self.vfprm.next_instruction()

    def prepare_op_increment_debug_counter(self, op):
        boxes = op.getarglist()
        a0, = boxes
        base_loc = self.make_sure_var_in_reg(a0, boxes)
        value_loc = self.get_scratch_reg(INT, boxes)
        self.free_temp_vars()
        return [base_loc, value_loc]

    def prepare_int_ri(self, op, res_in_cc):
        boxes = op.getarglist()
        a0, a1 = boxes
        imm_a0 = check_imm_box(a0)
        imm_a1 = check_imm_box(a1)
        if not imm_a0 and imm_a1:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.convert_to_imm(a1)
        elif imm_a0 and not imm_a1:
            l1 = self.convert_to_imm(a0)
            l0 = self.make_sure_var_in_reg(a1, boxes)
        else:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op)
        # note that we always allocate res, even if res_in_cc is True,
        # that only means overflow is in CC
        return [l0, l1, res]

    def prepare_op_int_add(self, op):
        return self.prepare_int_ri(op, False)

    def prepare_op_int_sub(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes
        imm_a1 = check_imm_box(a1)
        if imm_a1:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.convert_to_imm(a1)
        else:
            l0 = self.make_sure_var_in_reg(a0, boxes)
            l1 = self.make_sure_var_in_reg(a1, boxes)
        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op)
        return [l0, l1, res]

    def prepare_comp_op_int_sub_ovf(self, op, res_in_cc):
        # ignore res_in_cc
        return self.prepare_op_int_sub(op)

    def prepare_op_int_mul(self, op):
        boxes = op.getarglist()
        a0, a1 = boxes

        reg1 = self.make_sure_var_in_reg(a0, forbidden_vars=boxes)
        reg2 = self.make_sure_var_in_reg(a1, forbidden_vars=boxes)

        self.possibly_free_vars(boxes)
        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op)
        self.possibly_free_var(op)
        return [reg1, reg2, res]

    def prepare_comp_op_int_mul_ovf(self, op, res_in_cc):
        return self.prepare_op_int_mul(op)

    # some of those have forms of imm that they accept, but they're rather
    # obscure. Can be future optimization
    prepare_op_int_and = prepare_op_int_mul
    prepare_op_int_or = prepare_op_int_mul
    prepare_op_int_xor = prepare_op_int_mul
    prepare_op_int_lshift = prepare_op_int_mul
    prepare_op_int_rshift = prepare_op_int_mul
    prepare_op_uint_rshift = prepare_op_int_mul
    prepare_op_uint_mul_high = prepare_op_int_mul

    def prepare_int_cmp(self, op, res_in_cc):
        boxes = op.getarglist()
        arg0, arg1 = boxes
        imm_a1 = check_imm_box(arg1)

        l0 = self.make_sure_var_in_reg(arg0, forbidden_vars=boxes)
        if imm_a1:
            l1 = self.convert_to_imm(arg1)
        else:
            l1 = self.make_sure_var_in_reg(arg1, forbidden_vars=boxes)

        self.possibly_free_vars_for_op(op)
        self.free_temp_vars()
        if not res_in_cc:
            res = self.force_allocate_reg(op)
            return [l0, l1, res]
        return [l0, l1]

    prepare_comp_op_int_lt = prepare_int_cmp
    prepare_comp_op_int_le = prepare_int_cmp
    prepare_comp_op_int_eq = prepare_int_cmp

    def prepare_op_int_le(self, op):
        return self.prepare_int_cmp(op, False)

    prepare_op_int_lt = prepare_op_int_le
    prepare_op_int_gt = prepare_op_int_le
    prepare_op_int_ge = prepare_op_int_le
    prepare_op_int_eq = prepare_op_int_le
    prepare_op_int_ne = prepare_op_int_le
    prepare_op_uint_lt = prepare_op_int_le
    prepare_op_uint_le = prepare_op_int_le
    prepare_op_uint_gt = prepare_op_int_le
    prepare_op_uint_ge = prepare_op_int_le

    def prepare_unary(self, op):
        a0 = op.getarg(0)
        assert not isinstance(a0, Const)
        reg = self.make_sure_var_in_reg(a0)
        self.possibly_free_vars_for_op(op)
        res = self.force_allocate_reg(op)
        return [reg, res]

    prepare_op_int_is_true = prepare_unary
    prepare_op_int_is_zero = prepare_unary
    prepare_op_int_neg = prepare_unary
    prepare_op_int_invert = prepare_unary

    def prepare_op_label(self, op):
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
            assert not isinstance(arg, Const)
            if self.last_real_usage.get(arg, -1) <= position:
                self.force_spill_var(arg)

        #
        for i in range(len(inputargs)):
            arg = inputargs[i]
            assert not isinstance(arg, Const)
            loc = self.loc(arg)
            arglocs[i] = loc
            if loc.is_core_reg() or loc.is_vfp_reg():
                self.frame_manager.mark_as_free(arg)
        #
        descr._arm_arglocs = arglocs
        descr._ll_loop_code = self.assembler.mc.currpos()
        descr._arm_clt = self.assembler.current_clt
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
        return []

    def prepare_op_finish(self, op):
        # the frame is in fp, but we have to point where in the frame is
        # the potential argument to FINISH
        if op.numargs() == 1:
            loc = self.make_sure_var_in_reg(op.getarg(0))
            locs = [loc]
        else:
            locs = []
        return locs

    def guard_impl(self, op, prevop):
        fcond = self.assembler.dispatch_comparison(prevop)
        # result is in CC
        return self._guard_impl(op), fcond

    def _guard_impl(self, op):
        arglocs = [None] * (len(op.getfailargs()) + 1)
        arglocs[0] = imm(self.frame_manager.get_frame_depth())
        failargs = op.getfailargs()
        for i in range(len(failargs)):
            if failargs[i]:
                arglocs[i + 1] = self.loc(failargs[i])
        return arglocs

    prepare_guard_op_guard_true = guard_impl
    prepare_guard_op_guard_false = guard_impl

    def prepare_guard_op_guard_overflow(self, guard_op, prev_op):
        self.assembler.dispatch_comparison(prev_op)
        # result in CC
        if prev_op.opnum == rop.INT_MUL_OVF:
            return self._guard_impl(guard_op), c.GT
        return self._guard_impl(guard_op), c.VC
    prepare_guard_op_guard_no_overflow = prepare_guard_op_guard_overflow

    prepare_op_guard_true = _guard_impl
    prepare_op_guard_false = _guard_impl

    prepare_op_nursery_ptr_increment = prepare_op_int_add
    prepare_comp_op_int_add_ovf = prepare_int_ri

    def prepare_op_jump(self, op):
        assert self.jump_target_descr is None
        descr = op.getdescr()
        assert isinstance(descr, TargetToken)
        self.jump_target_descr = descr
        arglocs = descr._arm_arglocs

        # get temporary locs
        tmploc = r.ip0
        vfptmploc = None # XXX r.vfp_ip

        # Part about non-floats
        src_locations1 = []
        dst_locations1 = []
        # Part about floats
        src_locations2 = []
        dst_locations2 = []

        # Build the four lists
        for i in range(op.numargs()):
            box = op.getarg(i)
            src_loc = self.loc(box)
            dst_loc = arglocs[i]
            if box.type != FLOAT:
                src_locations1.append(src_loc)
                dst_locations1.append(dst_loc)
            else:
                src_locations2.append(src_loc)
                dst_locations2.append(dst_loc)
        self.assembler.check_frame_before_jump(self.jump_target_descr)
        remap_frame_layout_mixed(self.assembler,
                                 src_locations1, dst_locations1, tmploc,
                                 src_locations2, dst_locations2, vfptmploc)
        return []

    def force_allocate_reg(self, var, forbidden_vars=[], selected_reg=None):
        if var.type == FLOAT:
            return self.vfprm.force_allocate_reg(var, forbidden_vars,
                                                 selected_reg)
        else:
            return self.rm.force_allocate_reg(var, forbidden_vars,
                                              selected_reg)

    def _check_invariants(self):
        self.rm._check_invariants()
        self.vfprm._check_invariants()

    def prepare_bridge(self, inputargs, arglocs, operations, allgcrefs,
                       frame_info):
        operations = self._prepare(inputargs, operations, allgcrefs)
        self._update_bindings(arglocs, inputargs)
        return operations

    def _update_bindings(self, locs, inputargs):
        used = {}
        i = 0
        for loc in locs:
            if loc is None:
                loc = r.fp
            arg = inputargs[i]
            i += 1
            if loc.is_core_reg():
                self.rm.reg_bindings[arg] = loc
                used[loc] = None
            elif loc.is_vfp_reg():
                self.vfprm.reg_bindings[arg] = loc
                used[loc] = None
            else:
                assert loc.is_stack()
                self.frame_manager.bind(arg, loc)

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
        self.fm.finish_binding()
        self._check_invariants()

    def get_gcmap(self, forbidden_regs=[], noregs=False):
        frame_depth = self.fm.get_frame_depth()
        gcmap = allocate_gcmap(self.assembler,
                        frame_depth, JITFRAME_FIXED_SIZE)
        for box, loc in self.rm.reg_bindings.iteritems():
            if loc in forbidden_regs:
                continue
            if box.type == REF and self.rm.is_still_alive(box):
                assert not noregs
                assert loc.is_core_reg()
                val = loc.value
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        for box, loc in self.fm.bindings.iteritems():
            if box.type == REF and self.rm.is_still_alive(box):
                assert loc.is_stack()
                val = loc.position + JITFRAME_FIXED_SIZE
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        return gcmap

    def get_final_frame_depth(self):
        return self.frame_manager.get_frame_depth()


def notimplemented(self, op):
    print "[ARM64/regalloc] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

def notimplemented_guard_op(self, op, prevop):
    print "[ARM64/regalloc] %s not implemented" % op.getopname()
    raise NotImplementedError(op)    

def notimplemented_comp_op(self, op, res_in_cc):
    print "[ARM64/regalloc] %s not implemented" % op.getopname()
    raise NotImplementedError(op)    

operations = [notimplemented] * (rop._LAST + 1)
guard_operations = [notimplemented_guard_op] * (rop._LAST + 1)
comp_operations = [notimplemented_comp_op] * (rop._LAST + 1)


for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'prepare_op_%s' % key
    if hasattr(Regalloc, methname):
        func = getattr(Regalloc, methname).im_func
        operations[value] = func
    methname = 'prepare_guard_op_%s' % key
    if hasattr(Regalloc, methname):
        func = getattr(Regalloc, methname).im_func
        guard_operations[value] = func
    methname = 'prepare_comp_op_%s' % key
    if hasattr(Regalloc, methname):
        func = getattr(Regalloc, methname).im_func
        comp_operations[value] = func
    