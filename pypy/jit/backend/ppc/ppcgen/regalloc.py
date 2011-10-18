from pypy.jit.backend.llsupport.regalloc import (RegisterManager, FrameManager,
                                                 TempBox, compute_vars_longevity,
                                                 compute_loop_consts)
from pypy.jit.backend.ppc.ppcgen.arch import (WORD, MY_COPY_OF_REGS)
from pypy.jit.backend.ppc.ppcgen.jump import remap_frame_layout_mixed
from pypy.jit.backend.ppc.ppcgen.locations import imm
from pypy.jit.backend.ppc.ppcgen.helper.regalloc import (_check_imm_arg, 
                                                         prepare_cmp_op,
                                                         prepare_binary_int_op,
                                                         prepare_binary_int_op_with_imm)
from pypy.jit.metainterp.history import (INT, REF, FLOAT, Const, ConstInt, 
                                         ConstPtr, LoopToken)
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.ppc.ppcgen import locations
from pypy.rpython.lltypesystem import rffi, lltype
import pypy.jit.backend.ppc.ppcgen.register as r

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
        r.r0:   MY_COPY_OF_REGS + 0 * WORD,
        r.r2:   MY_COPY_OF_REGS + 1 * WORD,
        r.r3:   MY_COPY_OF_REGS + 2 * WORD,
        r.r4:   MY_COPY_OF_REGS + 3 * WORD,
        r.r5:   MY_COPY_OF_REGS + 4 * WORD,
        r.r6:   MY_COPY_OF_REGS + 5 * WORD,
        r.r7:   MY_COPY_OF_REGS + 6 * WORD,
        r.r8:   MY_COPY_OF_REGS + 7 * WORD,
        r.r9:   MY_COPY_OF_REGS + 8 * WORD,
        r.r10:  MY_COPY_OF_REGS + 9 * WORD,
        r.r11:  MY_COPY_OF_REGS + 10 * WORD,
        r.r12:  MY_COPY_OF_REGS + 11 * WORD,
        r.r13:  MY_COPY_OF_REGS + 12 * WORD,
        r.r14:  MY_COPY_OF_REGS + 13 * WORD,
        r.r15:  MY_COPY_OF_REGS + 14 * WORD,
        r.r16:  MY_COPY_OF_REGS + 15 * WORD,
        r.r17:  MY_COPY_OF_REGS + 16 * WORD,
        r.r18:  MY_COPY_OF_REGS + 17 * WORD,
        r.r19:  MY_COPY_OF_REGS + 18 * WORD,
        r.r20:  MY_COPY_OF_REGS + 19 * WORD,
        r.r21:  MY_COPY_OF_REGS + 20 * WORD,
        r.r22:  MY_COPY_OF_REGS + 21 * WORD,
        r.r23:  MY_COPY_OF_REGS + 22 * WORD,
        r.r24:  MY_COPY_OF_REGS + 23 * WORD,
        r.r25:  MY_COPY_OF_REGS + 24 * WORD,
        r.r26:  MY_COPY_OF_REGS + 25 * WORD,
        r.r27:  MY_COPY_OF_REGS + 26 * WORD,
        r.r28:  MY_COPY_OF_REGS + 27 * WORD,
        r.r29:  MY_COPY_OF_REGS + 28 * WORD,
        r.r30:  MY_COPY_OF_REGS + 29 * WORD,
        r.r31:  MY_COPY_OF_REGS + 30 * WORD,
    }

    def __init__(self, longevity, frame_manager=None, assembler=None):
        RegisterManager.__init__(self, longevity, frame_manager, assembler)

    def call_result_location(self, v):
        return r.r3

    def convert_to_imm(self, c):
        if isinstance(c, ConstInt):
            return locations.ImmLocation(c.value)
        else:
            assert isinstance(c, ConstPtr)
            return locations.ImmLocation(rffi.cast(lltype.Signed, c.value))

class PPCFrameManager(FrameManager):
    def __init__(self):
        FrameManager.__init__(self)
        self.frame_depth = 1

    @staticmethod
    def frame_pos(loc, type):
        num_words = PPCFrameManager.frame_size(type)
        return locations.StackLocation(loc, num_words=num_words, type=type)

    @staticmethod
    def frame_size(type):
        if type == FLOAT:
            assert 0, "TODO"
        return 1

class Regalloc(object):
    def __init__(self, longevity, frame_manager=None, assembler=None):
        self.cpu = assembler.cpu
        self.longevity = longevity
        self.frame_manager = frame_manager
        self.assembler = assembler
        self.rm = PPCRegisterManager(longevity, frame_manager, assembler)

    def prepare_loop(self, inputargs, operations, looptoken):
        loop_consts = compute_loop_consts(inputargs, operations[-1], looptoken)
        inputlen = len(inputargs)
        nonfloatlocs = [None] * len(inputargs)
        for i in range(inputlen):
            arg = inputargs[i]
            assert not isinstance(arg, Const)
            if arg not in loop_consts and self.longevity[arg][1] > -1:
                self.try_allocate_reg(arg)
            loc = self.loc(arg)
            nonfloatlocs[i] = loc
        self.possibly_free_vars(inputargs)
        return nonfloatlocs

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

    def _check_invariants(self):
        self.rm._check_invariants()

    def loc(self, var):
        return self.rm.loc(var)

    def position(self):
        return self.rm.position

    def next_instruction(self):
        self.rm.next_instruction()

    def _ensure_value_is_boxed(self, thing, forbidden_vars=[]):
        box = None
        loc = None
        if isinstance(thing, Const):
            if isinstance(thing, ConstPtr):
                box = TempPtr()
            else:
                box = TempInt()
            loc = self.force_allocate_reg(box, forbidden_vars=forbidden_vars)
            imm = self.rm.convert_to_imm(thing)
            self.assembler.load_imm(loc.value, imm.value)
        else:
            loc = self.make_sure_var_in_reg(thing,
                    forbidden_vars=forbidden_vars)
            box = thing
        return loc, box

    def make_sure_var_in_reg(self, var, forbidden_vars=[],
                             selected_reg=None, need_lower_byte=False):
        return self.rm.make_sure_var_in_reg(var, forbidden_vars,
                selected_reg, need_lower_byte)

    # ******************************************************
    # *         P R E P A R E  O P E R A T I O N S         * 
    # ******************************************************

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

    prepare_int_le = prepare_cmp_op()
    prepare_int_lt = prepare_cmp_op()
    prepare_int_ge = prepare_cmp_op()
    prepare_int_gt = prepare_cmp_op()
    prepare_int_eq = prepare_cmp_op()
    prepare_int_ne = prepare_cmp_op()

    prepare_uint_lt = prepare_cmp_op()
    prepare_uint_le = prepare_cmp_op()
    prepare_uint_gt = prepare_cmp_op()
    prepare_uint_ge = prepare_cmp_op()

    def prepare_finish(self, op):
        args = [locations.imm(self.frame_manager.frame_depth)]
        for i in range(op.numargs()):
            arg = op.getarg(i)
            if arg:
                args.append(self.loc(arg))
                self.possibly_free_var(arg)
            else:
                args.append(None)
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
    
    def prepare_guard_true(self, op):
        l0, box = self._ensure_value_is_boxed(op.getarg(0))
        args = self._prepare_guard(op, [l0])
        self.possibly_free_var(box)
        self.possibly_free_vars(op.getfailargs())
        return args

    def prepare_jump(self, op):
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        nonfloatlocs = descr._ppc_arglocs[0]

        tmploc = r.r0       
        src_locs1 = [self.loc(op.getarg(i)) for i in range(op.numargs()) 
                            if op.getarg(i).type != FLOAT]
        assert tmploc not in nonfloatlocs
        dst_locs1 = [loc for loc in nonfloatlocs if loc is not None]
        remap_frame_layout_mixed(self.assembler,
                                 src_locs1, dst_locs1, tmploc,
                                 [], [], None)
        return []

def make_operation_list():
    def not_implemented(self, op, *args):
        raise NotImplementedError, op

    operations = [None] * (rop._LAST + 1)
    for key, val in rop.__dict__.items():
        key = key.lower()
        if key.startswith("_"):
            continue
        methname = "prepare_%s" % key
        if hasattr(Regalloc, methname):
            func = getattr(Regalloc, methname).im_func
        else:
            func = not_implemented
        operations[val] = func
    return operations

Regalloc.operations = make_operation_list()
