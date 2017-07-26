import py
from rpython.jit.metainterp.history import ConstInt, INT, FLOAT
from rpython.jit.backend.llsupport.regalloc import FrameManager, LinkedList
from rpython.jit.backend.llsupport.regalloc import RegisterManager as BaseRegMan
from rpython.jit.metainterp.resoperation import InputArgInt, InputArgRef,\
     InputArgFloat

def newboxes(*values):
    return [InputArgInt(v) for v in values]

def newrefboxes(count):
    return [InputArgRef() for _ in range(count)]

def boxes_and_longevity(num):
    res = []
    longevity = {}
    for i in range(num):
        box = InputArgInt(0)
        res.append(box)
        longevity[box] = (0, 1)
    return res, longevity

class FakeReg(object):
    def __init__(self, i):
        self.n = i
    def __repr__(self):
        return 'r%d' % self.n

r0, r1, r2, r3 = [FakeReg(i) for i in range(4)]
regs = [r0, r1, r2, r3]

class RegisterManager(BaseRegMan):
    all_regs = regs
    def convert_to_imm(self, v):
        return v

class FakeFramePos(object):
    def __init__(self, pos, box_type):
        self.pos = pos
        self.box_type = box_type
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
        sp = fm.loc(b0)
        assert sp.pos == 0
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
        longevity = {b0: (0, 1)}
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
        longevity = {b0: (0, 1)}
        asm = MockAsm()
        rm = RegisterManager(longevity, frame_manager=fm, assembler=asm)
        f0 = InputArgFloat()
        longevity = {f0: (0, 1)}
        xrm = XRegisterManager(longevity, frame_manager=fm, assembler=asm)
        xrm.loc(f0)
        rm.loc(b0)
        assert fm.get_frame_depth() == 3
                
    def test_spilling(self):
        b0, b1, b2, b3, b4, b5 = newboxes(0, 1, 2, 3, 4, 5)
        longevity = {b0: (0, 3), b1: (0, 3), b3: (0, 5), b2: (0, 2), b4: (1, 4), b5: (1, 3)}
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
