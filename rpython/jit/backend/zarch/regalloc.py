from rpython.jit.backend.llsupport.regalloc import (RegisterManager, FrameManager,
                                                    TempVar, compute_vars_longevity,
                                                    BaseRegalloc)
from rpython.jit.backend.zarch.arch import WORD
from rpython.jit.codewriter import longlong
from rpython.jit.backend.zarch.locations import imm, get_fp_offset
from rpython.jit.metainterp.history import (Const, ConstInt, ConstFloat, ConstPtr,
                                            INT, REF, FLOAT, VOID)
from rpython.jit.metainterp.history import JitCellToken, TargetToken
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.backend.zarch import locations
from rpython.rtyper.lltypesystem import rffi, lltype, rstr, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import cast_instance_to_gcref
from rpython.jit.backend.llsupport import symbolic
from rpython.jit.backend.llsupport.descr import ArrayDescr
import rpython.jit.backend.zarch.registers as r
import rpython.jit.backend.zarch.conditions as c
from rpython.jit.backend.llsupport.descr import unpack_arraydescr
from rpython.jit.backend.llsupport.descr import unpack_fielddescr
from rpython.jit.backend.llsupport.descr import unpack_interiorfielddescr
from rpython.jit.backend.llsupport.gcmap import allocate_gcmap
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.debug import debug_print
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.rlib import rgc
from rpython.rlib.rarithmetic import r_uint

LIMIT_LOOP_BREAK = 15000      # should be much smaller than 32 KB


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


class FPRegisterManager(RegisterManager):
    all_regs              = r.MANAGED_FP_REGS
    box_types             = [FLOAT]
    save_around_call_regs = r.VOLATILES_FLOAT
    assert set(save_around_call_regs).issubset(all_regs)

    def convert_to_adr(self, c):
        assert isinstance(c, ConstFloat)
        adr = self.assembler.datablockwrapper.malloc_aligned(8, 8)
        x = c.getfloatstorage()
        rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[0] = x
        return adr

    def convert_to_imm(self, c):
        adr = self.convert_to_adr(c)
        return locations.ConstFloatLoc(adr)

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def call_result_location(self, v):
        return r.f1

    def ensure_reg(self, box):
        if isinstance(box, Const):
            loc = self.get_scratch_reg()
            immadrvalue = self.convert_to_adr(box)
            mc = self.assembler.mc
            mc.load_imm(r.SCRATCH, immadrvalue)
            mc.lfdx(loc.value, 0, r.SCRATCH.value)
        else:
            assert box in self.temp_boxes
            loc = self.make_sure_var_in_reg(box,
                    forbidden_vars=self.temp_boxes)
        return loc

    def get_scratch_reg(self):
        box = TempFloat()
        reg = self.force_allocate_reg(box, forbidden_vars=self.temp_boxes)
        self.temp_boxes.append(box)
        return reg


class ZARCHRegisterManager(RegisterManager):
    all_regs              = r.MANAGED_REGS
    box_types             = None       # or a list of acceptable types
    no_lower_byte_regs    = all_regs
    save_around_call_regs = r.VOLATILES
    frame_reg             = r.SPP
    assert set(save_around_call_regs).issubset(all_regs)

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def call_result_location(self, v):
        return r.r2

    def convert_to_int(self, c):
        if isinstance(c, ConstInt):
            return rffi.cast(lltype.Signed, c.value)
        else:
            assert isinstance(c, ConstPtr)
            return rffi.cast(lltype.Signed, c.value)

    def convert_to_imm(self, c):
        val = self.convert_to_int(c)
        return locations.ImmLocation(val)

    def ensure_reg(self, box):
        if isinstance(box, Const):
            loc = self.get_scratch_reg()
            immvalue = self.convert_to_int(box)
            self.assembler.mc.load_imm(loc, immvalue)
        else:
            assert box in self.temp_boxes
            loc = self.make_sure_var_in_reg(box,
                    forbidden_vars=self.temp_boxes)
        return loc

    def get_scratch_reg(self):
        box = TempVar()
        reg = self.force_allocate_reg(box, forbidden_vars=self.temp_boxes)
        self.temp_boxes.append(box)
        return reg


class ZARCHFrameManager(FrameManager):
    def __init__(self, base_ofs):
        FrameManager.__init__(self)
        self.used = []
        self.base_ofs = base_ofs

    def frame_pos(self, loc, box_type):
        #return locations.StackLocation(loc, get_fp_offset(self.base_ofs, loc), box_type)
        return locations.StackLocation(loc, get_fp_offset(self.base_ofs, loc), box_type)

    @staticmethod
    def frame_size(type):
        return 1

    @staticmethod
    def get_loc_index(loc):
        assert isinstance(loc, locations.StackLocation)
        return loc.position


class Regalloc(BaseRegalloc):

    def __init__(self, assembler=None):
        self.cpu = assembler.cpu
        self.assembler = assembler
        self.jump_target_descr = None
        self.final_jump_op = None

    def _prepare(self,  inputargs, operations, allgcrefs):
        cpu = self.assembler.cpu
        self.fm = ZARCHFrameManager(cpu.get_baseofs_of_frame_field())
        operations = cpu.gc_ll_descr.rewrite_assembler(cpu, operations,
                                                       allgcrefs)
        # compute longevity of variables
        longevity, last_real_usage = compute_vars_longevity(
                                                    inputargs, operations)
        self.longevity = longevity
        self.last_real_usage = last_real_usage
        self.rm = ZARCHRegisterManager(self.longevity,
                                     frame_manager = self.fm,
                                     assembler = self.assembler)
        self.fprm = FPRegisterManager(self.longevity, frame_manager = self.fm,
                                      assembler = self.assembler)
        return operations

    def prepare_loop(self, inputargs, operations, looptoken, allgcrefs):
        operations = self._prepare(inputargs, operations, allgcrefs)
        self._set_initial_bindings(inputargs, looptoken)
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))
        self.min_bytes_before_label = 4    # for redirect_call_assembler()
        return operations

    def prepare_bridge(self, inputargs, arglocs, operations, allgcrefs,
                       frame_info):
        operations = self._prepare(inputargs, operations, allgcrefs)
        self._update_bindings(arglocs, inputargs)
        self.min_bytes_before_label = 0
        return operations

    def ensure_next_label_is_at_least_at_position(self, at_least_position):
        self.min_bytes_before_label = max(self.min_bytes_before_label,
                                          at_least_position)

    def _update_bindings(self, locs, inputargs):
        # XXX this should probably go to llsupport/regalloc.py
        used = {}
        i = 0
        for loc in locs:
            if loc is None: # xxx bit kludgy
                loc = r.SPP
            arg = inputargs[i]
            i += 1
            if loc.is_reg():
                if loc is r.SPP:
                    self.rm.bindings_to_frame_reg[arg] = None
                else:
                    self.rm.reg_bindings[arg] = loc
                    used[loc] = None
            elif loc.is_fp_reg():
                self.fprm.reg_bindings[arg] = loc
                used[loc] = None
            else:
                assert loc.is_stack()
                self.fm.bind(arg, loc)
        self.rm.free_regs = []
        for reg in self.rm.all_regs:
            if reg not in used:
                self.rm.free_regs.append(reg)
        self.fprm.free_regs = []
        for reg in self.fprm.all_regs:
            if reg not in used:
                self.fprm.free_regs.append(reg)
        self.possibly_free_vars(list(inputargs))
        self.fm.finish_binding()
        self.rm._check_invariants()
        self.fprm._check_invariants()

    def get_final_frame_depth(self):
        return self.fm.get_frame_depth()

    def possibly_free_var(self, var):
        if var is not None:
            if var.type == FLOAT:
                self.fprm.possibly_free_var(var)
            else:
                self.rm.possibly_free_var(var)

    def possibly_free_vars(self, vars):
        for var in vars:
            self.possibly_free_var(var)

    def possibly_free_vars_for_op(self, op):
        for i in range(op.numargs()):
            var = op.getarg(i)
            self.possibly_free_var(var)

    def force_allocate_reg(self, var):
        if var.type == FLOAT:
            forbidden_vars = self.fprm.temp_boxes
            return self.fprm.force_allocate_reg(var, forbidden_vars)
        else:
            forbidden_vars = self.rm.temp_boxes
            return self.rm.force_allocate_reg(var, forbidden_vars)

    def force_allocate_reg_or_cc(self, var):
        assert var.type == INT
        if self.next_op_can_accept_cc(self.operations, self.rm.position):
            # hack: return the SPP location to mean "lives in CC".  This
            # SPP will not actually be used, and the location will be freed
            # after the next op as usual.
            self.rm.force_allocate_frame_reg(var)
            return r.SPP
        else:
            # else, return a regular register (not SPP).
            return self.force_allocate_reg(var)

    def walk_operations(self, inputargs, operations):
        from rpython.jit.backend.zarch.assembler import (
                asm_operations)
        i = 0
        self.limit_loop_break = (self.assembler.mc.get_relative_pos() +
                                     LIMIT_LOOP_BREAK)
        self.operations = operations
        while i < len(operations):
            op = operations[i]
            self.assembler.mc.mark_op(op)
            self.rm.position = i
            self.fprm.position = i
            if op.has_no_side_effect() and op not in self.longevity:
                i += 1
                self.possibly_free_vars_for_op(op)
                continue
            #
            for j in range(op.numargs()):
                box = op.getarg(j)
                if box.type != FLOAT:
                    self.rm.temp_boxes.append(box)
                else:
                    self.fprm.temp_boxes.append(box)
            #
            opnum = op.getopnum()
            if not we_are_translated() and opnum == -127:
                self._consider_force_spill(op)
            else:
                arglocs = prepare_oplist[opnum](self, op)
                asm_operations[opnum](self.assembler, op, arglocs, self)
            self.free_op_vars()
            self.possibly_free_var(op)
            self.rm._check_invariants()
            self.fprm._check_invariants()
            if self.assembler.mc.get_relative_pos() > self.limit_loop_break:
                self.assembler.break_long_loop()
                self.limit_loop_break = (self.assembler.mc.get_relative_pos() +
                                             LIMIT_LOOP_BREAK)
            i += 1
        assert not self.rm.reg_bindings
        assert not self.fprm.reg_bindings
        self.flush_loop()
        self.assembler.mc.mark_op(None) # end of the loop
        self.operations = None
        for arg in inputargs:
            self.possibly_free_var(arg)

    def flush_loop(self):
        # Emit a nop in the rare case where we have a guard_not_invalidated
        # immediately before a label
        mc = self.assembler.mc
        while self.min_bytes_before_label > mc.get_relative_pos():
            mc.nop()

    def get_gcmap(self, forbidden_regs=[], noregs=False):
        frame_depth = self.fm.get_frame_depth()
        gcmap = allocate_gcmap(self.assembler, frame_depth,
                               r.JITFRAME_FIXED_SIZE)
        for box, loc in self.rm.reg_bindings.iteritems():
            if loc in forbidden_regs:
                continue
            if box.type == REF and self.rm.is_still_alive(box):
                assert not noregs
                assert loc.is_reg()
                val = self.assembler.cpu.all_reg_indexes[loc.value]
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        for box, loc in self.fm.bindings.iteritems():
            if box.type == REF and self.rm.is_still_alive(box):
                assert isinstance(loc, locations.StackLocation)
                val = loc.get_position() + r.JITFRAME_FIXED_SIZE
                gcmap[val // WORD // 8] |= r_uint(1) << (val % (WORD * 8))
        return gcmap

    def loc(self, var):
        if var.type == FLOAT:
            return self.fprm.loc(var)
        else:
            return self.rm.loc(var)

    def next_instruction(self):
        self.rm.next_instruction()
        self.fprm.next_instruction()

    def force_spill_var(self, var):
        if var.type == FLOAT:
            self.fprm.force_spill_var(var)
        else:
            self.rm.force_spill_var(var)

    def _consider_force_spill(self, op):
        # This operation is used only for testing
        self.force_spill_var(op.getarg(0))

    def before_call(self, force_store=[], save_all_regs=False):
        self.rm.before_call(force_store, save_all_regs)
        self.fprm.before_call(force_store, save_all_regs)

    def after_call(self, v):
        if v.type == FLOAT:
            return self.fprm.after_call(v)
        else:
            return self.rm.after_call(v)

    def call_result_location(self, v):
        if v.type == FLOAT:
            return self.fprm.call_result_location(v)
        else:
            return self.rm.call_result_location(v)

    def ensure_reg(self, box):
        if box.type == FLOAT:
            return self.fprm.ensure_reg(box)
        else:
            return self.rm.ensure_reg(box)

    def ensure_reg_or_16bit_imm(self, box):
        if box.type == FLOAT:
            return self.fprm.ensure_reg(box)
        else:
            if check_imm_box(box):
                return imm(box.getint())
            return self.rm.ensure_reg(box)

    def ensure_reg_or_any_imm(self, box):
        if box.type == FLOAT:
            return self.fprm.ensure_reg(box)
        else:
            if isinstance(box, Const):
                return imm(box.getint())
            return self.rm.ensure_reg(box)

    def get_scratch_reg(self, type):
        if type == FLOAT:
            return self.fprm.get_scratch_reg()
        else:
            return self.rm.get_scratch_reg()

    def free_op_vars(self):
        # free the boxes in the 'temp_boxes' lists, which contain both
        # temporary boxes and all the current operation's arguments
        self.rm.free_temp_vars()
        self.fprm.free_temp_vars()

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
        arglocs = self.assembler.target_arglocs(descr)
        jump_op = self.final_jump_op
        assert len(arglocs) == jump_op.numargs()
        for i in range(jump_op.numargs()):
            box = jump_op.getarg(i)
            if not isinstance(box, Const):
                loc = arglocs[i]
                if loc is not None and loc.is_stack():
                    self.fm.hint_frame_pos[box] = self.fm.get_loc_index(loc)

    # ******************************************************
    # *         P R E P A R E  O P E R A T I O N S         * 
    # ******************************************************

def notimplemented(self, op):
    msg = '[S390X/regalloc] %s not implemented\n' % op.getopname()
    if we_are_translated():
        llop.debug_print(lltype.Void, msg)
    raise NotImplementedError(msg)

prepare_oplist = [notimplemented] * (rop._LAST + 1)

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'prepare_%s' % key
    if hasattr(Regalloc, methname):
        func = getattr(Regalloc, methname).im_func
        prepare_oplist[value] = func
