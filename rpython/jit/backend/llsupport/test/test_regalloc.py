import py
import sys
from rpython.jit.metainterp.history import ConstInt, INT, FLOAT
from rpython.jit.metainterp.history import BasicFailDescr, TargetToken
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.resoperation import InputArgInt, InputArgRef,\
     InputArgFloat
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.llsupport.regalloc import FrameManager, LinkedList
from rpython.jit.backend.llsupport.regalloc import RegisterManager as BaseRegMan,\
     Lifetime as RealLifetime, UNDEF_POS, BaseRegalloc, compute_vars_longevity,\
     LifetimeManager
from rpython.jit.tool.oparser import parse
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.annlowlevel import llhelper

def newboxes(*values):
    return [InputArgInt(v) for v in values]

def newrefboxes(count):
    return [InputArgRef() for _ in range(count)]

def Lifetime(definition_pos=UNDEF_POS, last_usage=UNDEF_POS,
             real_usages=UNDEF_POS):
    if real_usages == UNDEF_POS:
        real_usages = last_usage
    lifetime = RealLifetime(definition_pos, last_usage)
    if isinstance(real_usages, int):
        real_usages = [real_usages]
    lifetime.real_usages = real_usages
    return lifetime


def boxes_and_longevity(num):
    res = []
    longevity = {}
    for i in range(num):
        box = InputArgInt(0)
        res.append(box)
        longevity[box] = Lifetime(0, 1)
    return res, longevity

class FakeReg(object):
    def __init__(self, i):
        self.n = i
    def _getregkey(self):
        return self.n
    def is_memory_reference(self):
        return False
    def __repr__(self):
        return 'r%d' % self.n

r0, r1, r2, r3 = [FakeReg(i) for i in range(4)]
regs = [r0, r1, r2, r3]

class RegisterManager(BaseRegMan):
    all_regs = regs

    def __init__(self, longevity, frame_manager=None, assembler=None):
        if isinstance(longevity, dict):
            longevity = LifetimeManager(longevity)
        BaseRegMan.__init__(self, longevity, frame_manager, assembler)

    def convert_to_imm(self, v):
        return v

class FakeFramePos(object):
    def __init__(self, pos, box_type):
        self.pos = pos
        self.value = pos
        self.box_type = box_type
    def _getregkey(self):
        return ~self.value
    def is_memory_reference(self):
        return True
    def __repr__(self):
        return 'FramePos<%d,%s>' % (self.pos, self.box_type)
    def __eq__(self, other):
        return self.pos == other.pos and self.box_type == other.box_type
    def __ne__(self, other):
        return not self == other

class TFrameManagerEqual(FrameManager):
    def frame_pos(self, i, box_type):
        return FakeFramePos(i, box_type)
    def frame_size(self, box_type):
        return 1
    def get_loc_index(self, loc):
        assert isinstance(loc, FakeFramePos)
        return loc.pos

class TFrameManager(FrameManager):
    def frame_pos(self, i, box_type):
        return FakeFramePos(i, box_type)
    def frame_size(self, box_type):
        if box_type == FLOAT:
            return 2
        else:
            return 1
    def get_loc_index(self, loc):
        assert isinstance(loc, FakeFramePos)
        return loc.pos

class FakeCPU(object):
    def get_baseofs_of_frame_field(self):
        return 0

class MockAsm(object):
    def __init__(self):
        self.moves = []
        self.emitted = []
        self.cpu = FakeCPU()

        # XXX register allocation statistics to be removed later
        self.num_moves_calls = 0
        self.num_moves_jump = 0
        self.num_spills = 0
        self.num_spills_to_existing = 0
        self.num_reloads = 0

        self.preamble_num_moves_calls = 0
        self.preamble_num_moves_jump = 0
        self.preamble_num_spills = 0
        self.preamble_num_spills_to_existing = 0
        self.preamble_num_reloads = 0

    def regalloc_mov(self, from_loc, to_loc):
        self.moves.append((from_loc, to_loc))
        self.emitted.append(("move", to_loc, from_loc))


def test_lifetime_next_real_usage():
    lt = RealLifetime(0, 1000)
    lt.real_usages = [0, 1, 5, 10, 24, 35, 55, 56, 57, 90, 92, 100]
    for i in range(100):
        next = lt.next_real_usage(i)
        assert next in lt.real_usages
        assert next > i
        assert lt.real_usages[lt.real_usages.index(next) - 1] <= i

def test_fixed_position():
    b0, b1, b2 = newboxes(0, 0, 0)
    l0 = Lifetime(0, 5)
    l1 = Lifetime(2, 9)
    l2 = Lifetime(0, 9)
    longevity = LifetimeManager({b0: l0, b1: l1, b2: l2})
    longevity.fixed_register(1, r0, b0)
    longevity.fixed_register(4, r2, b0)
    longevity.fixed_register(5, r1, b1)
    longevity.fixed_register(8, r1, b1)

    assert l0.fixed_positions == [(1, r0), (4, r2)]
    assert l1.fixed_positions == [(5, r1), (8, r1)]
    assert l2.fixed_positions is None

    fpr0 = longevity.fixed_register_use[r0]
    fpr1 = longevity.fixed_register_use[r1]
    fpr2 = longevity.fixed_register_use[r2]
    assert r3 not in longevity.fixed_register_use
    assert fpr0.index_lifetimes == [(1, 0)]
    assert fpr1.index_lifetimes == [(5, 2), (8, 5)]
    assert fpr2.index_lifetimes == [(4, 1)]

def test_fixed_position_none():
    b0, b1, b2 = newboxes(0, 0, 0)
    l0 = Lifetime(0, 5)
    l1 = Lifetime(2, 9)
    l2 = Lifetime(0, 9)
    longevity = LifetimeManager({b0: l0, b1: l1, b2: l2})
    longevity.fixed_register(1, r0)
    longevity.fixed_register(4, r2)
    longevity.fixed_register(5, r1)
    longevity.fixed_register(8, r1)

    fpr0 = longevity.fixed_register_use[r0]
    fpr1 = longevity.fixed_register_use[r1]
    fpr2 = longevity.fixed_register_use[r2]
    assert r3 not in longevity.fixed_register_use
    assert fpr0.index_lifetimes == [(1, 1)]
    assert fpr1.index_lifetimes == [(5, 5), (8, 8)]
    assert fpr2.index_lifetimes == [(4, 4)]


def test_free_until_pos_none():
    longevity = LifetimeManager({})
    longevity.fixed_register(5, r1, None)
    longevity.fixed_register(8, r1, None)
    longevity.fixed_register(35, r1, None)

    fpr1 = longevity.fixed_register_use[r1]

    assert fpr1.free_until_pos(0) == 5
    assert fpr1.free_until_pos(1) == 5
    assert fpr1.free_until_pos(2) == 5
    assert fpr1.free_until_pos(3) == 5
    assert fpr1.free_until_pos(4) == 5
    assert fpr1.free_until_pos(5) == 5
    assert fpr1.free_until_pos(10) == 35
    assert fpr1.free_until_pos(20) == 35
    assert fpr1.free_until_pos(30) == 35
    assert fpr1.free_until_pos(36) == sys.maxint

def test_free_until_pos():
    b0, b1, b2 = newboxes(0, 0, 0)
    l0 = Lifetime(0, 5)
    l1 = Lifetime(2, 9)
    l2 = Lifetime(30, 40)
    longevity = LifetimeManager({b0: l0, b1: l1, b2: l2})
    longevity.fixed_register(5, r1, b1)
    longevity.fixed_register(8, r1, b1)
    longevity.fixed_register(35, r1, b2)

    fpr1 = longevity.fixed_register_use[r1]

    # simple cases: we are before the beginning of the lifetime of the variable
    # in the fixed register, then it's free until the definition of the
    # variable
    assert fpr1.free_until_pos(0) == 2
    assert fpr1.free_until_pos(1) == 2
    assert fpr1.free_until_pos(2) == 2
    assert fpr1.free_until_pos(10) == 30
    assert fpr1.free_until_pos(20) == 30
    assert fpr1.free_until_pos(30) == 30

    # after the fixed use, we are fined anyway
    assert fpr1.free_until_pos(36) == sys.maxint
    assert fpr1.free_until_pos(50) == sys.maxint

    # asking for a position *after* the definition of the variable in the fixed
    # register means the variable didn't make it into the fixed register, but
    # at the latest by the use point it will have to go there
    assert fpr1.free_until_pos(3) == 5
    assert fpr1.free_until_pos(4) == 5
    assert fpr1.free_until_pos(5) == 5
    assert fpr1.free_until_pos(6) == 8
    assert fpr1.free_until_pos(7) == 8
    assert fpr1.free_until_pos(8) == 8
    assert fpr1.free_until_pos(31) == 35
    assert fpr1.free_until_pos(32) == 35
    assert fpr1.free_until_pos(33) == 35
    assert fpr1.free_until_pos(34) == 35
    assert fpr1.free_until_pos(35) == 35

def test_free_until_pos_different_regs():
    b0, b1, b2 = newboxes(0, 0, 0)
    l0 = Lifetime(0, 5)
    l1 = Lifetime(2, 9)
    l2 = Lifetime(30, 40)
    longevity = LifetimeManager({b0: l0, b1: l1, b2: l2})
    longevity.fixed_register(1, r0, b0)
    longevity.fixed_register(4, r2, b0)
    fpr2 = longevity.fixed_register_use[r2]
    # the definition of b0 is before the other fixed register use of r0, so the
    # earliest b0 can be in r2 is that use point at index 1
    assert fpr2.free_until_pos(0) == 1


def test_longest_free_reg():
    b0, b1, b2 = newboxes(0, 0, 0)
    l0 = Lifetime(0, 5)
    l1 = Lifetime(2, 9)
    l2 = Lifetime(30, 40)
    longevity = LifetimeManager({b0: l0, b1: l1, b2: l2})
    longevity.fixed_register(1, r0, b0)
    longevity.fixed_register(4, r2, b0)
    longevity.fixed_register(5, r1, b1)
    longevity.fixed_register(8, r1, b1)
    longevity.fixed_register(35, r1, b2)

    assert longevity.longest_free_reg(0, [r0, r1, r2]) == (r1, 2)

class TestRegalloc(object):
    def test_freeing_vars(self):
        b0, b1, b2 = newboxes(0, 0, 0)
        longevity = {b0: Lifetime(0, 1), b1: Lifetime(0, 2), b2: Lifetime(0, 2)}
        rm = RegisterManager(longevity)
        rm.next_instruction()
        for b in b0, b1, b2:
            rm.try_allocate_reg(b)
        rm._check_invariants()
        assert len(rm.free_regs) == 1
        assert len(rm.reg_bindings) == 3
        rm.possibly_free_vars([b0, b1, b2])
        assert len(rm.free_regs) == 1
        assert len(rm.reg_bindings) == 3
        rm._check_invariants()
        rm.next_instruction()
        rm.possibly_free_vars([b0, b1, b2])
        rm._check_invariants()
        assert len(rm.free_regs) == 2
        assert len(rm.reg_bindings) == 2
        rm._check_invariants()
        rm.next_instruction()
        rm.possibly_free_vars([b0, b1, b2])
        rm._check_invariants()
        assert len(rm.free_regs) == 4
        assert len(rm.reg_bindings) == 0
        
    def test_register_exhaustion(self):
        boxes, longevity = boxes_and_longevity(5)
        rm = RegisterManager(longevity)
        rm.next_instruction()
        for b in boxes[:len(regs)]:
            assert rm.try_allocate_reg(b)
        assert rm.try_allocate_reg(boxes[-1]) is None
        rm._check_invariants()

    def test_need_lower_byte(self):
        boxes, longevity = boxes_and_longevity(5)
        b0, b1, b2, b3, b4 = boxes

        class XRegisterManager(RegisterManager):
            no_lower_byte_regs = [r2, r3]
        
        rm = XRegisterManager(longevity)
        rm.next_instruction()
        loc0 = rm.try_allocate_reg(b0, need_lower_byte=True)
        assert loc0 not in XRegisterManager.no_lower_byte_regs
        loc = rm.try_allocate_reg(b1, need_lower_byte=True)
        assert loc not in XRegisterManager.no_lower_byte_regs
        loc = rm.try_allocate_reg(b2, need_lower_byte=True)
        assert loc is None
        loc = rm.try_allocate_reg(b0, need_lower_byte=True)
        assert loc is loc0
        rm._check_invariants()

    def test_specific_register(self):
        boxes, longevity = boxes_and_longevity(5)
        rm = RegisterManager(longevity)
        rm.next_instruction()
        loc = rm.try_allocate_reg(boxes[0], selected_reg=r1)
        assert loc is r1
        loc = rm.try_allocate_reg(boxes[1], selected_reg=r1)
        assert loc is None
        rm._check_invariants()
        loc = rm.try_allocate_reg(boxes[0], selected_reg=r1)
        assert loc is r1
        loc = rm.try_allocate_reg(boxes[0], selected_reg=r2)
        assert loc is r2
        rm._check_invariants()

    def test_force_allocate_reg(self):
        boxes, longevity = boxes_and_longevity(5)
        b0, b1, b2, b3, b4 = boxes
        fm = TFrameManager()

        class XRegisterManager(RegisterManager):
            no_lower_byte_regs = [r2, r3]
        
        rm = XRegisterManager(longevity,
                              frame_manager=fm,
                              assembler=MockAsm())
        rm.next_instruction()
        loc = rm.force_allocate_reg(b0)
        assert isinstance(loc, FakeReg)
        loc = rm.force_allocate_reg(b1)
        assert isinstance(loc, FakeReg)
        loc = rm.force_allocate_reg(b2)
        assert isinstance(loc, FakeReg)
        loc = rm.force_allocate_reg(b3)
        assert isinstance(loc, FakeReg)
        loc = rm.force_allocate_reg(b4)
        assert isinstance(loc, FakeReg)
        # one of those should be now somewhere else
        locs = [rm.loc(b) for b in boxes]
        used_regs = [loc for loc in locs if isinstance(loc, FakeReg)]
        assert len(used_regs) == len(regs)
        loc = rm.force_allocate_reg(b0, need_lower_byte=True)
        assert isinstance(loc, FakeReg)
        assert loc not in [r2, r3]
        rm._check_invariants()

    def test_make_sure_var_in_reg(self):
        boxes, longevity = boxes_and_longevity(5)
        fm = TFrameManager()
        rm = RegisterManager(longevity, frame_manager=fm,
                             assembler=MockAsm())
        rm.next_instruction()
        # allocate a stack position
        b0, b1, b2, b3, b4 = boxes
        sp = fm.loc(b0)
        assert sp.pos == 0
        loc = rm.make_sure_var_in_reg(b0)
        assert isinstance(loc, FakeReg)
        rm._check_invariants()

    def test_force_result_in_reg_1(self):
        b0, b1 = newboxes(0, 0)
        longevity = {b0: Lifetime(0, 1), b1: Lifetime(1, 3)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        # first path, var is already in reg and dies
        loc0 = rm.force_allocate_reg(b0)
        rm._check_invariants()
        rm.next_instruction()
        loc = rm.force_result_in_reg(b1, b0)
        assert loc is loc0
        assert len(asm.moves) == 0
        rm._check_invariants()

    def test_force_result_in_reg_2(self):
        b0, b1 = newboxes(0, 0)
        longevity = {b0: Lifetime(0, 2), b1: Lifetime(1, 3)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        loc0 = rm.force_allocate_reg(b0)
        rm._check_invariants()
        rm.next_instruction()
        loc = rm.force_result_in_reg(b1, b0)
        assert loc is loc0
        assert rm.loc(b0) is not loc0
        assert len(asm.moves) == 1
        rm._check_invariants()

    def test_force_result_in_reg_3(self):
        b0, b1, b2, b3, b4 = newboxes(0, 0, 0, 0, 0)
        longevity = {b0: Lifetime(0, 2), b1: Lifetime(0, 2),
                     b3: Lifetime(0, 2), b2: Lifetime(0, 2),
                     b4: Lifetime(1, 3)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        for b in b0, b1, b2, b3:
            rm.force_allocate_reg(b)
        assert not len(rm.free_regs)
        rm._check_invariants()
        rm.next_instruction()
        rm.force_result_in_reg(b4, b0)
        rm._check_invariants()
        assert len(asm.moves) == 1

    def test_force_result_in_reg_4(self):
        b0, b1 = newboxes(0, 0)
        longevity = {b0: Lifetime(0, 1), b1: Lifetime(0, 1)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        fm.loc(b0)
        rm.force_result_in_reg(b1, b0)
        rm._check_invariants()
        loc = rm.loc(b1)
        assert isinstance(loc, FakeReg)
        loc = rm.loc(b0)
        assert isinstance(loc, FakeFramePos)
        assert len(asm.moves) == 1

    def test_bogus_make_sure_var_in_reg(self):
        b0, = newboxes(0)
        longevity = {b0: Lifetime(0, 1)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        # invalid call to make_sure_var_in_reg(): box unknown so far
        py.test.raises(KeyError, rm.make_sure_var_in_reg, b0)

    def test_return_constant(self):
        asm = MockAsm()
        boxes, longevity = boxes_and_longevity(5)
        fm = TFrameManager()
        rm = RegisterManager(longevity, assembler=asm,
                             frame_manager=fm)
        rm.next_instruction()
        loc = rm.return_constant(ConstInt(1), selected_reg=r1)
        assert loc is r1
        loc = rm.return_constant(ConstInt(1), selected_reg=r1)
        assert loc is r1
        loc = rm.return_constant(ConstInt(1))
        assert isinstance(loc, ConstInt)
        for box in boxes[:-1]:
            rm.force_allocate_reg(box)
        assert len(asm.moves) == 2       # Const(1) -> r1, twice
        assert len(rm.reg_bindings) == 4
        rm._check_invariants()

    def test_force_result_in_reg_const(self):
        boxes, longevity = boxes_and_longevity(2)
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm,
                             assembler=asm)
        rm.next_instruction()
        c = ConstInt(0)
        rm.force_result_in_reg(boxes[0], c)
        rm._check_invariants()

    def test_loc_of_const(self):
        rm = RegisterManager({})
        rm.next_instruction()
        assert isinstance(rm.loc(ConstInt(1)), ConstInt)

    def test_call_support(self):
        class XRegisterManager(RegisterManager):
            save_around_call_regs = [r1, r2]

            def call_result_location(self, v):
                return r1

        fm = TFrameManager()
        asm = MockAsm()
        boxes, longevity = boxes_and_longevity(5)
        rm = XRegisterManager(longevity, frame_manager=fm,
                              assembler=asm)
        for b in boxes[:-1]:
            rm.force_allocate_reg(b)
        rm.before_call()
        assert len(rm.reg_bindings) == 2
        assert fm.get_frame_depth() == 2
        assert len(asm.moves) == 2
        rm._check_invariants()
        rm.after_call(boxes[-1])
        assert len(rm.reg_bindings) == 3
        rm._check_invariants()

    def test_call_support_save_all_regs(self):
        class XRegisterManager(RegisterManager):
            save_around_call_regs = [r1, r2]

            def call_result_location(self, v):
                return r1

        fm = TFrameManager()
        asm = MockAsm()
        boxes, longevity = boxes_and_longevity(5)
        rm = XRegisterManager(longevity, frame_manager=fm,
                              assembler=asm)
        for b in boxes[:-1]:
            rm.force_allocate_reg(b)
        rm.before_call(save_all_regs=True)
        assert len(rm.reg_bindings) == 0
        assert fm.get_frame_depth() == 4
        assert len(asm.moves) == 4
        rm._check_invariants()
        rm.after_call(boxes[-1])
        assert len(rm.reg_bindings) == 1
        rm._check_invariants()
        

    def test_different_frame_width(self):
        class XRegisterManager(RegisterManager):
            pass

        fm = TFrameManager()
        b0 = InputArgInt()
        longevity = {b0: Lifetime(0, 1)}
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        f0 = InputArgFloat()
        longevity = {f0: Lifetime(0, 1)}
        xrm = XRegisterManager(longevity, frame_manager=fm, assembler=asm)
        xrm.loc(f0)
        rm.loc(b0)
        assert fm.get_frame_depth() == 3

    def test_spilling(self):
        b0, b1, b2, b3, b4, b5 = newboxes(0, 1, 2, 3, 4, 5)
        longevity = {b0: Lifetime(0, 3), b1: Lifetime(0, 3),
                     b3: Lifetime(0, 5), b2: Lifetime(0, 2),
                     b4: Lifetime(1, 4), b5: Lifetime(1, 3)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        for b in b0, b1, b2, b3:
            rm.force_allocate_reg(b)
        assert len(rm.free_regs) == 0
        rm.next_instruction()
        loc = rm.loc(b3)
        spilled = rm.force_allocate_reg(b4)
        assert spilled is loc
        spilled2 = rm.force_allocate_reg(b5)
        assert spilled2 is loc
        rm._check_invariants()

    def test_spilling_furthest_next_real_use(self):
        b0, b1, b2, b3, b4, b5 = newboxes(0, 1, 2, 3, 4, 5)
        longevity = {b0: Lifetime(0, 3, [1, 2, 3]), b1: Lifetime(0, 3, [3]),
                     b3: Lifetime(0, 4, [1, 2, 3, 4]), b2: Lifetime(0, 2),
                     b4: Lifetime(1, 4), b5: Lifetime(1, 3)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        for b in b0, b1, b2, b3:
            rm.force_allocate_reg(b)
        assert len(rm.free_regs) == 0
        rm.next_instruction()
        loc = rm.loc(b1)
        spilled = rm.force_allocate_reg(b4)
        assert spilled is loc
        spilled2 = rm.force_allocate_reg(b5)
        assert spilled2 is loc
        rm._check_invariants()


    def test_spill_useless_vars_first(self):
        b0, b1, b2, b3, b4, b5 = newboxes(0, 1, 2, 3, 4, 5)
        longevity = {b0: Lifetime(0, 5), b1: Lifetime(0, 10),
                     # b2 and b3 become useless but b3 lives longer
                     b3: Lifetime(0, 7, 3), b2: Lifetime(0, 6, 3),
                     b4: Lifetime(4, 5), b5: Lifetime(4, 7)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        for b in b0, b1, b2, b3:
            rm.force_allocate_reg(b)
        rm.position = 4
        assert len(rm.free_regs) == 0
        loc = rm.loc(b3)
        spilled = rm.force_allocate_reg(b4)
        assert spilled is loc
        loc = rm.loc(b2)
        spilled2 = rm.force_allocate_reg(b5)
        assert spilled2 is loc
        rm._check_invariants()

    def test_hint_frame_locations_1(self):
        for hint_value in range(11):
            b0, = newboxes(0)
            fm = TFrameManager()
            fm.hint_frame_pos[b0] = hint_value
            blist = newboxes(*range(10))
            for b1 in blist:
                fm.loc(b1)
            for b1 in blist:
                fm.mark_as_free(b1)
            assert fm.get_frame_depth() == 10
            loc = fm.loc(b0)
            if hint_value < 10:
                expected = hint_value
            else:
                expected = 0
            assert fm.get_loc_index(loc) == expected
            assert fm.get_frame_depth() == 10

    def test_linkedlist(self):
        class Loc(object):
            def __init__(self, pos, size, tp):
                self.pos = pos
                self.size = size
                self.tp = tp

        class FrameManager(object):
            @staticmethod
            def get_loc_index(item):
                return item.pos
            @staticmethod
            def frame_pos(pos, tp):
                if tp == 13:
                    size = 2
                else:
                    size = 1
                return Loc(pos, size, tp)

        fm = FrameManager()
        l = LinkedList(fm)
        l.append(1, Loc(1, 1, 0))
        l.append(1, Loc(4, 1, 0))
        l.append(1, Loc(2, 1, 0))
        l.append(1, Loc(0, 1, 0))
        assert l.master_node.val == 0
        assert l.master_node.next.val == 1
        assert l.master_node.next.next.val == 2
        assert l.master_node.next.next.next.val == 4
        assert l.master_node.next.next.next.next is None
        item = l.pop(1, 0)
        assert item.pos == 0
        item = l.pop(1, 0)
        assert item.pos == 1
        item = l.pop(1, 0)
        assert item.pos == 2
        item = l.pop(1, 0)
        assert item.pos == 4
        assert l.pop(1, 0) is None
        l.append(1, Loc(1, 1, 0))
        l.append(1, Loc(5, 1, 0))
        l.append(1, Loc(2, 1, 0))
        l.append(1, Loc(0, 1, 0))
        item = l.pop(2, 13)
        assert item.tp == 13
        assert item.pos == 0
        assert item.size == 2
        assert l.pop(2, 0) is None # 2 and 4
        l.append(1, Loc(4, 1, 0))
        item = l.pop(2, 13)
        assert item.pos == 4
        assert item.size == 2
        assert l.pop(1, 0).pos == 2
        assert l.pop(1, 0) is None
        l.append(2, Loc(1, 2, 0))
        # this will not work because the result will be odd
        assert l.pop(2, 13) is None
        l.append(1, Loc(3, 1, 0))
        item = l.pop(2, 13)
        assert item.pos == 2
        assert item.tp == 13
        assert item.size == 2

    def test_frame_manager_basic_equal(self):
        b0, b1 = newboxes(0, 1)
        fm = TFrameManagerEqual()
        loc0 = fm.loc(b0)
        assert fm.get_loc_index(loc0) == 0
        #
        assert fm.get(b1) is None
        loc1 = fm.loc(b1)
        assert fm.get_loc_index(loc1) == 1
        assert fm.get(b1) == loc1
        #
        loc0b = fm.loc(b0)
        assert loc0b == loc0
        #
        fm.loc(InputArgInt())
        assert fm.get_frame_depth() == 3
        #
        f0 = InputArgFloat()
        locf0 = fm.loc(f0)
        assert fm.get_loc_index(locf0) == 3
        assert fm.get_frame_depth() == 4
        #
        f1 = InputArgFloat()
        locf1 = fm.loc(f1)
        assert fm.get_loc_index(locf1) == 4
        assert fm.get_frame_depth() == 5
        fm.mark_as_free(b1)
        assert fm.freelist
        b2 = InputArgInt()
        fm.loc(b2) # should be in the same spot as b1 before
        assert fm.get(b1) is None
        assert fm.get(b2) == loc1
        fm.mark_as_free(b0)
        p0 = InputArgRef()
        ploc = fm.loc(p0)
        assert fm.get_loc_index(ploc) == 0
        assert fm.get_frame_depth() == 5
        assert ploc != loc1
        p1 = InputArgRef()
        p1loc = fm.loc(p1)
        assert fm.get_loc_index(p1loc) == 5
        assert fm.get_frame_depth() == 6
        fm.mark_as_free(p0)
        p2 = InputArgRef()
        p2loc = fm.loc(p2)
        assert p2loc == ploc
        assert len(fm.freelist) == 0
        for box in fm.bindings.keys():
            fm.mark_as_free(box)
        fm.bind(InputArgRef(), FakeFramePos(3, 'r'))
        assert len(fm.freelist) == 6

    def test_frame_manager_basic(self):
        b0, b1 = newboxes(0, 1)
        fm = TFrameManager()
        loc0 = fm.loc(b0)
        assert fm.get_loc_index(loc0) == 0
        #
        assert fm.get(b1) is None
        loc1 = fm.loc(b1)
        assert fm.get_loc_index(loc1) == 1
        assert fm.get(b1) == loc1
        #
        loc0b = fm.loc(b0)
        assert loc0b == loc0
        #
        fm.loc(InputArgInt())
        assert fm.get_frame_depth() == 3
        #
        f0 = InputArgFloat()
        locf0 = fm.loc(f0)
        # can't be odd
        assert fm.get_loc_index(locf0) == 4
        assert fm.get_frame_depth() == 6
        #
        f1 = InputArgFloat()
        locf1 = fm.loc(f1)
        assert fm.get_loc_index(locf1) == 6
        assert fm.get_frame_depth() == 8
        fm.mark_as_free(b1)
        assert fm.freelist
        b2 = InputArgInt()
        fm.loc(b2) # should be in the same spot as b1 before
        assert fm.get(b1) is None
        assert fm.get(b2) == loc1
        fm.mark_as_free(b0)
        p0 = InputArgRef()
        ploc = fm.loc(p0)
        assert fm.get_loc_index(ploc) == 0
        assert fm.get_frame_depth() == 8
        assert ploc != loc1
        p1 = InputArgRef()
        p1loc = fm.loc(p1)
        assert fm.get_loc_index(p1loc) == 3
        assert fm.get_frame_depth() == 8
        fm.mark_as_free(p0)
        p2 = InputArgRef()
        p2loc = fm.loc(p2)
        assert p2loc == ploc
        assert len(fm.freelist) == 0
        fm.mark_as_free(b2)
        f3 = InputArgFloat()
        fm.mark_as_free(p2)
        floc = fm.loc(f3)
        assert fm.get_loc_index(floc) == 0
        for box in fm.bindings.keys():
            fm.mark_as_free(box)

# _____________________________________________________
# tests that assign registers in a mocked way for a fake CPU

r4, r5, r6, r7, r8, r9 = [FakeReg(i) for i in range(4, 10)]

class RegisterManager2(BaseRegMan):
    all_regs = [r0, r1, r2, r3, r4, r5, r6, r7]

    save_around_call_regs = [r0, r1, r2, r3]

    frame_reg = r8

    # calling conventions: r0 is result
    # r1 r2 r3 are arguments and caller-saved registers
    # r4 r5 r6 r7 are callee-saved registers

    def convert_to_imm(self, v):
        return v.value

    def call_result_location(self, v):
        return r0


class FakeRegalloc(BaseRegalloc):
    def __init__(self):
        self.assembler = MockAsm()

    def prepare_loop(self, inputargs, operations, looptoken, allgcrefs):
        operations = self._prepare(inputargs, operations, allgcrefs)
        self.operations = operations
        self._set_initial_bindings(inputargs, looptoken)
        # note: we need to make a copy of inputargs because possibly_free_vars
        # is also used on op args, which is a non-resizable list
        self.possibly_free_vars(list(inputargs))
        self._add_fixed_registers()
        return operations

    def _prepare(self, inputargs, operations, allgcrefs):
        self.fm = TFrameManager()
        # compute longevity of variables
        longevity = compute_vars_longevity(inputargs, operations)
        self.longevity = longevity
        self.rm = RegisterManager2(
            longevity, assembler=self.assembler, frame_manager=self.fm)
        return operations

    def possibly_free_var(self, var):
        self.rm.possibly_free_var(var)

    def possibly_free_vars(self, vars):
        for var in vars:
            if var is not None: # xxx kludgy
                self.possibly_free_var(var)

    def loc(self, x):
        return self.rm.loc(x)

    def force_allocate_reg_or_cc(self, var):
        assert var.type == INT
        if self.next_op_can_accept_cc(self.operations, self.rm.position):
            # hack: return the ebp location to mean "lives in CC".  This
            # ebp will not actually be used, and the location will be freed
            # after the next op as usual.
            self.rm.force_allocate_frame_reg(var)
            return r8
        else:
            # else, return a regular register (not ebp).
            return self.rm.force_allocate_reg(var, need_lower_byte=True)

    def fake_allocate(self, loop):
        from rpython.jit.backend.x86.jump import remap_frame_layout

        emit = self.assembler.emitted.append
        for i, op in enumerate(loop.operations):
            self.rm.position = i
            opnum = op.getopnum()
            opname = op.getopname()
            if rop.is_comparison(opnum):
                locs = [self.loc(x) for x in op.getarglist()]
                loc = self.force_allocate_reg_or_cc(op)
                emit((opname, loc, locs))
            elif opname.startswith("int_"):
                locs = [self.loc(x) for x in op.getarglist()]
                loc = self.rm.force_result_in_reg(
                    op, op.getarg(0), op.getarglist())
                emit((opname, loc, locs[1:]))
            elif op.is_guard():
                fail_locs = [self.loc(x) for x in op.getfailargs()]
                emit((opname, self.loc(op.getarg(0)), fail_locs))
            elif rop.is_call(opnum):
                # calling convention!
                src_locs = [self.loc(x) for x in op.getarglist()[1:]]
                self.rm.before_call()
                loc = self.rm.after_call(op)
                dst_locs = [r1, r2, r3][:len(src_locs)]
                remap_frame_layout(self.assembler, src_locs, dst_locs, r8)
                emit((opname, loc, dst_locs))
            elif opname == "label":
                descr = op.getdescr()
                locs = [self.loc(x) for x in op.getarglist()]
                emit((opname, locs))
                descr._fake_arglocs = locs
            else:
                locs = [self.loc(x) for x in op.getarglist()]
                if op.type != "v":
                    loc = self.rm.force_allocate_reg(op)
                    emit((opname, loc, locs))
                else:
                    emit((opname, locs))
        return self.assembler.emitted

    def _add_fixed_registers(self):
        for i, op in enumerate(self.operations):
            if rop.is_call(op.getopnum()):
                # calling convention!
                arglist = op.getarglist()[1:]
                for arg, reg in zip(arglist + [None] * (3 - len(arglist)), [r1, r2, r3]):
                    self.longevity.fixed_register(i, reg, arg)
                self.longevity.fixed_register(i, r0, op)


CPU = getcpuclass()
class TestFullRegallocFakeCPU(object):
    # XXX copy-paste from test_regalloc_integration
    cpu = CPU(None, None)
    cpu.setup_once()

    targettoken = TargetToken()
    targettoken2 = TargetToken()
    fdescr1 = BasicFailDescr(1)
    fdescr2 = BasicFailDescr(2)
    fdescr3 = BasicFailDescr(3)

    def setup_method(self, meth):
        self.targettoken._ll_loop_code = 0
        self.targettoken2._ll_loop_code = 0

    def f1(x):
        return x+1

    def f2(x, y):
        return x*y

    def f10(*args):
        assert len(args) == 10
        return sum(args)

    F1PTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
    F2PTR = lltype.Ptr(lltype.FuncType([lltype.Signed]*2, lltype.Signed))
    F10PTR = lltype.Ptr(lltype.FuncType([lltype.Signed]*10, lltype.Signed))
    f1ptr = llhelper(F1PTR, f1)
    f2ptr = llhelper(F2PTR, f2)
    f10ptr = llhelper(F10PTR, f10)

    f1_calldescr = cpu.calldescrof(F1PTR.TO, F1PTR.TO.ARGS, F1PTR.TO.RESULT,
                                   EffectInfo.MOST_GENERAL)
    f2_calldescr = cpu.calldescrof(F2PTR.TO, F2PTR.TO.ARGS, F2PTR.TO.RESULT,
                                   EffectInfo.MOST_GENERAL)
    f10_calldescr = cpu.calldescrof(F10PTR.TO, F10PTR.TO.ARGS, F10PTR.TO.RESULT,
                                    EffectInfo.MOST_GENERAL)

    namespace = locals().copy()

    def parse(self, s, boxkinds=None, namespace=None):
        return parse(s, self.cpu, namespace or self.namespace,
                     boxkinds=boxkinds)

    def allocate(self, s):
        loop = self.parse(s)
        self.loop = loop
        regalloc = FakeRegalloc()
        regalloc.prepare_loop(loop.inputargs, loop.operations,
                              loop.original_jitcell_token, [])
        self.regalloc = regalloc
        return regalloc.fake_allocate(loop)

    def _consider_binop(self, op):
        loc, argloc = self._consider_binop_part(op)
        self.perform(op, [loc, argloc], loc)


    def test_simple(self):
        ops = '''
        [i0]
        label(i0, descr=targettoken)
        i1 = int_add(i0, 1)
        i2 = int_lt(i1, 20)
        guard_true(i2) [i1]
        jump(i1, descr=targettoken)
        '''
        emitted = self.allocate(ops)
        fp0 = FakeFramePos(0, INT)
        assert emitted == [
            ("label", [fp0]),
            ("move", r0, fp0),
            ("int_add", r0, [1]),
            ("int_lt", r8, [r0, 20]),
            ("guard_true", r8, [r0]),
            ("jump", [r0]),
        ]

    def test_call(self):
        ops = '''
        [i0]
        i1 = int_mul(i0, 2)
        i2 = call_i(ConstClass(f1ptr), i1, descr=f1_calldescr)
        guard_false(i2) []
        '''
        emitted = self.allocate(ops)
        fp0 = FakeFramePos(0, INT)
        assert emitted == [
            ("move", r1, fp0),
            ("int_mul", r1, [2]),
            ("call_i", r0, [r1]),
            ("guard_false", r0, []),
        ]

    def test_call_2(self):
        ops = '''
        [i0, i1]
        i2 = int_mul(i0, 2)
        i3 = int_add(i1, 1)
        i4 = call_i(ConstClass(f1ptr), i2, descr=f1_calldescr)
        guard_false(i4) [i3]
        '''
        emitted = self.allocate(ops)
        fp0 = FakeFramePos(0, INT)
        fp1 = FakeFramePos(1, INT)
        assert emitted == [
            ("move", r1, fp0),
            ("int_mul", r1, [2]),
            ("move", r4, fp1), # r4 gets picked since it's callee-saved
            ("int_add", r4, [1]),
            ("call_i", r0, [r1]),
            ("guard_false", r0, [r4]),
        ]


