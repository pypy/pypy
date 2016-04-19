import py
from rpython.jit.metainterp.history import JitCellToken
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.zarch.arch import WORD
from rpython.jit.backend.zarch.regalloc import (ZARCHRegisterManager,
        ZARCHFrameManager)
import rpython.jit.backend.zarch.registers as r
from rpython.jit.backend.llsupport.regalloc import TempVar, NoVariableToSpill
from rpython.jit.tool.oparser import parse

CPU = getcpuclass()

class FakeAssembler(object):
    def __init__(self):
        self.move_count = 0
    def regalloc_mov(self, f, t):
        self.move_count += 1

class FakeRegalloc(ZARCHRegisterManager):
    def __init__(self):
        ZARCHRegisterManager.__init__(self, {}, ZARCHFrameManager(0), FakeAssembler())

    def allocate(self, *regs):
        for reg,var in regs:
            register = r.registers[reg]
            self.reg_bindings[var] = register
            self.free_regs = [fr for fr in self.free_regs if fr is not register]

class TempInt(TempVar):
    type = 'i' 
    def __repr__(self):
        return "<TempInt at %s>" % (id(self),)

def temp_vars(count):
    return [TempInt() for _ in range(count)]

class TestRegalloc(object):
    def setup_method(self, name):
        self.rm = FakeRegalloc()

    def test_all_free(self):
        a,b = temp_vars(2)
        self.rm.force_allocate_reg_pair(a, b, [])
        assert self.rm.reg_bindings[a] == r.r2
        assert self.rm.reg_bindings[b] == r.r3

    def test_cannot_spill_too_many_forbidden_vars(self):
        v = temp_vars(12)
        a, b = v[10], v[11]
        self.rm.frame_manager.bindings[a] = self.rm.frame_manager.loc(a)
        self.rm.frame_manager.bindings[b] = self.rm.frame_manager.loc(b)
        # all registers are allocated
        self.rm.allocate((2,v[0]),(3,v[1]),(4,v[2]),(5,v[3]),
                         (6,v[4]),(7,v[5]),(8,v[6]),(9,v[7]),
                         (10,v[8]),(11,v[9]))
        self.rm.temp_boxes = v[:-2]
        with py.test.raises(AssertionError):
            # assert len(forbidden_vars) <= 8
            self.rm.ensure_even_odd_pair(a, b, bind_first=False)

    def test_all_but_one_forbidden(self):
        a,b,f1,f2,f3,f4,o = temp_vars(7)
        self.rm.allocate((2,f1),(4,f2),(6,f3),(8,f4),(10,o))
        self.rm.force_allocate_reg_pair(a, b, [f1,f2,f3,f4])
        assert self.rm.reg_bindings[a] == r.r10
        assert self.rm.reg_bindings[b] == r.r11

    def test_all_but_one_forbidden_odd(self):
        a,b,f1,f2,f3,f4,f5 = temp_vars(7)
        self.rm.allocate((3,f1),(5,f2),(7,f3),(9,f4),(11,f5))
        self.rm.force_allocate_reg_pair(a, b, [f1,f3,f4,f5])
        assert self.rm.reg_bindings[a] == r.r4
        assert self.rm.reg_bindings[b] == r.r5

    def test_ensure_reg_pair(self):
        a,b,f1 = temp_vars(3)
        self.rm.allocate((4,f1),(2,a))
        self.rm.temp_boxes = [f1]
        re, ro = self.rm.ensure_even_odd_pair(a, b)
        assert re == r.r6
        assert ro == r.r7
        assert re != self.rm.reg_bindings[a]
        assert ro != self.rm.reg_bindings[a]
        assert self.rm.assembler.move_count == 1

    def test_ensure_reg_pair_bind_second(self):
        a,b,f1,f2,f3,f4 = temp_vars(6)
        self.rm.allocate((4,f1),(2,a),(6,f2),(8,f3),(10,f4))
        self.rm.temp_boxes = [f1,f2,f3,f4]
        re, ro = self.rm.ensure_even_odd_pair(a, b, bind_first=False)
        assert re == r.r2
        assert ro == r.r3
        assert ro == self.rm.reg_bindings[b]
        assert a not in self.rm.reg_bindings
        assert self.rm.assembler.move_count == 2

    def test_ensure_pair_fully_allocated_first_forbidden(self):
        v = temp_vars(12)
        a, b = v[10], v[11]
        self.rm.frame_manager.bindings[a] = self.rm.frame_manager.loc(a)
        self.rm.frame_manager.bindings[b] = self.rm.frame_manager.loc(b)
        # all registers are allocated
        self.rm.allocate((2,v[0]),(3,v[1]),(4,v[2]),(5,v[3]),
                         (6,v[4]),(7,v[5]),(8,v[6]),(9,v[7]),
                         (10,v[8]),(11,v[9]))
        self.rm.temp_boxes = [v[0],v[2],v[4],v[6],v[8]]
        e, o = self.rm.ensure_even_odd_pair(a, b, bind_first=False)
        assert e == r.r2
        assert o == r.r3

        self.rm.temp_boxes = [v[0],v[1],v[2],v[4],v[6],v[8]]
        e, o = self.rm.ensure_even_odd_pair(a, b, bind_first=False)
        assert e == r.r2
        assert o == r.r3

def run(inputargs, ops):
    cpu = CPU(None, None)
    cpu.setup_once()
    loop = parse(ops, cpu, namespace=locals())
    looptoken = JitCellToken()
    cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
    deadframe = cpu.execute_token(looptoken, *inputargs)
    return cpu, deadframe

def test_bug_rshift():
    cpu, deadframe = run([9], '''
    [i1]
    i2 = int_add(i1, i1)
    i3 = int_invert(i2)
    i4 = uint_rshift(i1, 3)
    i5 = int_add(i4, i3)
    finish(i5)
    ''')
    assert cpu.get_int_value(deadframe, 0) == (9 >> 3) + (~18)

def test_bug_int_is_true_1():
    cpu, deadframe = run([-10], '''
    [i1]
    i2 = int_mul(i1, i1)
    i3 = int_mul(i2, i1)
    i5 = int_is_true(i2)
    i4 = int_is_zero(i5)
    guard_false(i5) [i4, i3]
    finish(42)
    ''')
    assert cpu.get_int_value(deadframe, 0) == 0
    assert cpu.get_int_value(deadframe, 1) == -1000

def test_bug_0():
    cpu, deadframe = run([-13, 10, 10, 8, -8, -16, -18, 46, -12, 26], '''
    [i1, i2, i3, i4, i5, i6, i7, i8, i9, i10]
    i11 = uint_gt(i3, -48)
    i12 = int_xor(i8, i1)
    i13 = int_gt(i6, -9)
    i14 = int_le(i13, i2)
    i15 = int_le(i11, i5)
    i16 = uint_ge(i13, i13)
    i17 = int_or(i9, -23)
    i18 = int_lt(i10, i13)
    i19 = int_or(i15, i5)
    i20 = int_xor(i17, 54)
    i21 = int_mul(i8, i10)
    i22 = int_or(i3, i9)
    i41 = int_and(i11, -4)
    i42 = int_or(i41, 1)
    i23 = int_mod(i12, i42)
    i24 = int_is_true(i6)
    i25 = uint_rshift(i15, 6)
    i26 = int_or(-4, i25)
    i27 = int_invert(i8)
    i28 = int_sub(-113, i11)
    i29 = int_neg(i7)
    i30 = int_neg(i24)
    i31 = int_floordiv(i3, 53)
    i32 = int_mul(i28, i27)
    i43 = int_and(i18, -4)
    i44 = int_or(i43, 1)
    i33 = int_mod(i26, i44)
    i34 = int_or(i27, i19)
    i35 = uint_lt(i13, 1)
    i45 = int_and(i21, 31)
    i36 = int_rshift(i21, i45)
    i46 = int_and(i20, 31)
    i37 = uint_rshift(i4, i46)
    i38 = uint_gt(i33, -11)
    i39 = int_neg(i7)
    i40 = int_gt(i24, i32)
    i99 = same_as_i(0)
    guard_true(i99) [i40, i36, i37, i31, i16, i34, i35, i23, i22, i29, i14, i39, i30, i38]
    finish(42)
    ''')
    assert cpu.get_int_value(deadframe, 0) == 0
    assert cpu.get_int_value(deadframe, 1) == 0
    assert cpu.get_int_value(deadframe, 2) == 0
    assert cpu.get_int_value(deadframe, 3) == 0
    assert cpu.get_int_value(deadframe, 4) == 1
    assert cpu.get_int_value(deadframe, 5) == -7
    assert cpu.get_int_value(deadframe, 6) == 1
    assert cpu.get_int_value(deadframe, 7) == 0
    assert cpu.get_int_value(deadframe, 8) == -2
    assert cpu.get_int_value(deadframe, 9) == 18
    assert cpu.get_int_value(deadframe, 10) == 1
    assert cpu.get_int_value(deadframe, 11) == 18
    assert cpu.get_int_value(deadframe, 12) == -1
    assert cpu.get_int_value(deadframe, 13) == 0

def test_bug_1():
    cpu, deadframe = run([17, -20, -6, 6, 1, 13, 13, 9, 49, 8], '''
    [i1, i2, i3, i4, i5, i6, i7, i8, i9, i10]
    i11 = uint_lt(i6, 0)
    i41 = int_and(i3, 31)
    i12 = int_rshift(i3, i41)
    i13 = int_neg(i2)
    i14 = int_add(i11, i7)
    i15 = int_or(i3, i2)
    i16 = int_or(i12, i12)
    i17 = int_ne(i2, i5)
    i42 = int_and(i5, 31)
    i18 = uint_rshift(i14, i42)
    i43 = int_and(i14, 31)
    i19 = int_lshift(7, i43)
    i20 = int_neg(i19)
    i21 = int_mod(i3, 1)
    i22 = uint_ge(i15, i1)
    i44 = int_and(i16, 31)
    i23 = int_lshift(i8, i44)
    i24 = int_is_true(i17)
    i45 = int_and(i5, 31)
    i25 = int_lshift(i14, i45)
    i26 = int_lshift(i5, 17)
    i27 = int_eq(i9, i15)
    i28 = int_ge(0, i6)
    i29 = int_neg(i15)
    i30 = int_neg(i22)
    i31 = int_add(i7, i16)
    i32 = uint_lt(i19, i19)
    i33 = int_add(i2, 1)
    i34 = int_neg(i5)
    i35 = int_add(i17, i24)
    i36 = uint_lt(2, i16)
    i37 = int_neg(i9)
    i38 = int_gt(i4, i11)
    i39 = int_lt(i27, i22)
    i40 = int_neg(i27)
    i99 = same_as_i(0)
    guard_true(i99) [i40, i10, i36, i26, i13, i30, i21, i33, i18, i25, i31, i32, i28, i29, i35, i38, i20, i39, i34, i23, i37]
    finish(-42)
    ''')
    assert cpu.get_int_value(deadframe, 0) == 0
    assert cpu.get_int_value(deadframe, 1) == 8
    assert cpu.get_int_value(deadframe, 2) == 1
    assert cpu.get_int_value(deadframe, 3) == 131072
    assert cpu.get_int_value(deadframe, 4) == 20
    assert cpu.get_int_value(deadframe, 5) == -1
    assert cpu.get_int_value(deadframe, 6) == 0
    assert cpu.get_int_value(deadframe, 7) == -19
    assert cpu.get_int_value(deadframe, 8) == 6
    assert cpu.get_int_value(deadframe, 9) == 26
    assert cpu.get_int_value(deadframe, 10) == 12
    assert cpu.get_int_value(deadframe, 11) == 0
    assert cpu.get_int_value(deadframe, 12) == 0
    assert cpu.get_int_value(deadframe, 13) == 2
    assert cpu.get_int_value(deadframe, 14) == 2
    assert cpu.get_int_value(deadframe, 15) == 1
    assert cpu.get_int_value(deadframe, 16) == -57344
    assert cpu.get_int_value(deadframe, 17) == 1
    assert cpu.get_int_value(deadframe, 18) == -1
    if WORD == 4:
        assert cpu.get_int_value(deadframe, 19) == -2147483648
    elif WORD == 8:
        assert cpu.get_int_value(deadframe, 19) == 19327352832
    assert cpu.get_int_value(deadframe, 20) == -49

