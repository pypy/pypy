
from pypy.jit.metainterp.history import BoxInt, ConstInt, BoxFloat
from pypy.jit.backend.llsupport.regalloc import FrameManager
from pypy.jit.backend.llsupport.regalloc import RegisterManager as BaseRegMan

def newboxes(*values):
    return [BoxInt(v) for v in values]

def boxes_and_longevity(num):
    res = []
    longevity = {}
    for i in range(num):
        box = BoxInt(0)
        res.append(box)
        longevity[box] = (0, 1)
    return res, longevity

class FakeReg(object):
    pass

r0, r1, r2, r3 = [FakeReg() for _ in range(4)]
regs = [r0, r1, r2, r3]

class RegisterManager(BaseRegMan):
    all_regs = regs
    def convert_to_imm(self, v):
        return v

class TFrameManager(FrameManager):
    def frame_pos(self, i, size):
        return i

class MockAsm(object):
    def __init__(self):
        self.moves = []
    
    def regalloc_mov(self, from_loc, to_loc):
        self.moves.append((from_loc, to_loc))

class TestRegalloc(object):
    def test_freeing_vars(self):
        b0, b1, b2 = newboxes(0, 0, 0)
        longevity = {b0: (0, 1), b1: (0, 2), b2: (0, 2)}
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
        sp = fm.loc(b0, 1)
        assert sp == 0
        loc = rm.make_sure_var_in_reg(b0)
        assert isinstance(loc, FakeReg)
        rm._check_invariants()
        
    def test_force_result_in_reg_1(self):
        b0, b1 = newboxes(0, 0)
        longevity = {b0: (0, 1), b1: (1, 3)}
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
        longevity = {b0: (0, 2), b1: (1, 3)}
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
        longevity = {b0: (0, 2), b1: (0, 2), b3: (0, 2), b2: (0, 2), b4: (1, 3)}
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
        longevity = {b0: (0, 1), b1: (0, 1)}
        fm = TFrameManager()
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        rm.next_instruction()
        fm.loc(b0, 1)
        rm.force_result_in_reg(b1, b0)
        rm._check_invariants()
        loc = rm.loc(b1)
        assert isinstance(loc, FakeReg)
        loc = rm.loc(b0)
        assert isinstance(loc, int)
        assert len(asm.moves) == 1

    def test_return_constant(self):
        asm = MockAsm()
        boxes, longevity = boxes_and_longevity(5)
        fm = TFrameManager()
        rm = RegisterManager(longevity, assembler=asm,
                             frame_manager=fm)
        rm.next_instruction()
        loc = rm.return_constant(ConstInt(0), imm_fine=False)
        assert isinstance(loc, FakeReg)
        loc = rm.return_constant(ConstInt(1), selected_reg=r1)
        assert loc is r1
        loc = rm.return_constant(ConstInt(1), selected_reg=r1)
        assert loc is r1
        loc = rm.return_constant(ConstInt(1), imm_fine=True)
        assert isinstance(loc, ConstInt)
        for box in boxes[:-1]:
            rm.force_allocate_reg(box)
        assert len(asm.moves) == 3
        loc = rm.return_constant(ConstInt(1), imm_fine=False)
        assert isinstance(loc, FakeReg)
        assert len(asm.moves) == 5
        assert len(rm.reg_bindings) == 3

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
        assert fm.frame_depth == 2
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
        assert fm.frame_depth == 4
        assert len(asm.moves) == 4
        rm._check_invariants()
        rm.after_call(boxes[-1])
        assert len(rm.reg_bindings) == 1
        rm._check_invariants()
        

    def test_different_frame_width(self):
        class XRegisterManager(RegisterManager):
            reg_width = 2

        fm = TFrameManager()
        b0 = BoxInt()
        longevity = {b0: (0, 1)}
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        f0 = BoxFloat()
        longevity = {f0: (0, 1)}
        xrm = XRegisterManager(longevity, frame_manager=fm, assembler=asm)
        xrm.loc(f0)
        rm.loc(b0)
        assert fm.frame_depth == 3
        
        
