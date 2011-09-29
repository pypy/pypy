from pypy.rlib.objectmodel import instantiate
from pypy.jit.backend.arm.assembler import AssemblerARM
from pypy.jit.backend.arm.locations import imm, ImmLocation, ConstFloatLoc,\
                                        RegisterLocation, StackLocation, \
                                        VFPRegisterLocation
from pypy.jit.backend.arm.registers import lr, ip, fp
from pypy.jit.backend.arm.conditions import AL
from pypy.jit.metainterp.history import INT, FLOAT, REF
import py
class MockInstr(object):
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return "%s %r %r" % (self.name, self.args, self.kwargs)

    __str__ = __repr__

    def __eq__(self, other):
        return (self.__class__ == other.__class__
                and self.name == other.name
                and self.args == other.args
                and self.kwargs == other.kwargs)
mi = MockInstr
# helper method for tests
def r(i):
    return RegisterLocation(i)

def vfp(i):
    return VFPRegisterLocation(i)

stack = StackLocation
def stack_float(i):
    return stack(i, num_words=2, type=FLOAT)

def imm_float(value):
    addr = int(value) # whatever
    return ConstFloatLoc(addr)

class MockBuilder(object):
    def __init__(self):
        self.instrs = []

    def __getattr__(self, name):
        i = MockInstr(name)
        self.instrs.append(i)
        return i

class TestRegallocMov(object):
    def setup_method(self, method):
        self.builder = MockBuilder()
        self.asm = instantiate(AssemblerARM)
        self.asm.mc = self.builder

    def mov(self, a, b, expected=None):
        self.asm.regalloc_mov(a, b)
        result =self.builder.instrs
        assert result == expected

    def test_mov_imm_to_reg(self):
        val = imm(123)
        reg = r(7)
        expected = [mi('gen_load_int', 7, 123, cond=AL)]
        self.mov(val, reg, expected)

    def test_mov_large_imm_to_reg(self):
        val = imm(65536)
        reg = r(7)
        expected = [mi('gen_load_int', 7, 65536, cond=AL)]
        self.mov(val, reg, expected)

    def test_mov_imm_to_stacklock(self):
        val = imm(100)
        s = stack(7)
        expected = [
                mi('PUSH', [lr.value], cond=AL),
                mi('gen_load_int', lr.value, 100, cond=AL), 
                mi('STR_ri', lr.value, fp.value, imm=-28, cond=AL),
                mi('POP', [lr.value], cond=AL)]
        self.mov(val, s, expected)

    def test_mov_big_imm_to_stacklock(self):
        val = imm(65536)
        s = stack(7)
        expected = [
                mi('PUSH', [lr.value], cond=AL),
                mi('gen_load_int', lr.value, 65536, cond=AL), 
                mi('STR_ri', lr.value, fp.value, imm=-28, cond=AL),
                mi('POP', [lr.value], cond=AL)]

        self.mov(val, s, expected)
    def test_mov_imm_to_big_stacklock(self):
        val = imm(100)
        s = stack(8191)
        expected = [mi('PUSH', [lr.value], cond=AL),
                    mi('gen_load_int', lr.value, 100, cond=AL),
                    mi('PUSH', [ip.value], cond=AL),
                    mi('gen_load_int', ip.value, -32764, cond=AL),
                    mi('STR_rr', lr.value, fp.value, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL),
                    mi('POP', [lr.value], cond=AL)]
        self.mov(val, s, expected)

    def test_mov_big_imm_to_big_stacklock(self):
        val = imm(65536)
        s = stack(8191)
        expected = [mi('PUSH', [lr.value], cond=AL),
                    mi('gen_load_int', lr.value, 65536, cond=AL),
                    mi('PUSH', [ip.value], cond=AL),
                    mi('gen_load_int', ip.value, -32764, cond=AL),
                    mi('STR_rr', lr.value, fp.value, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL),
                    mi('POP', [lr.value], cond=AL)]
        self.mov(val, s, expected)

    def test_mov_reg_to_reg(self):
        r1 = r(1)
        r9 = r(9)
        expected = [mi('MOV_rr', r9.value, r1.value, cond=AL)]
        self.mov(r1, r9, expected)

    def test_mov_reg_to_stack(self):
        s = stack(10)
        r6 = r(6)
        expected = [mi('STR_ri', r6.value, fp.value, imm=-40, cond=AL)]
        self.mov(r6, s, expected)

    def test_mov_reg_to_big_stackloc(self):
        s = stack(8191)
        r6 = r(6)
        expected = [mi('PUSH', [ip.value], cond=AL),
                    mi('gen_load_int', ip.value, -32764, cond=AL),
                    mi('STR_rr', r6.value, fp.value, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL)]
        self.mov(r6, s, expected)

    def test_mov_stack_to_reg(self):
        s = stack(10)
        r6 = r(6)
        expected = [mi('LDR_ri', r6.value, fp.value, imm=-40, cond=AL)]
        self.mov(s, r6, expected)

    def test_mov_big_stackloc_to_reg(self):
        s = stack(8191)
        r6 = r(6)
        expected = [
                    mi('PUSH', [ip.value], cond=AL),
                    mi('gen_load_int', ip.value, -32764, cond=AL),
                    mi('LDR_rr', r6.value, fp.value, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL)]
        self.mov(s, r6, expected)

    def test_mov_float_imm_to_vfp_reg(self):
        f = imm_float(3.5)
        reg = vfp(5)
        expected = [
                    mi('PUSH', [ip.value], cond=AL),
                    mi('gen_load_int', ip.value, f.value, cond=AL),
                    mi('VLDR', 5, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL)]
        self.mov(f, reg, expected)

    def test_mov_vfp_reg_to_vfp_reg(self):
        reg1 = vfp(5)
        reg2 = vfp(14)
        expected = [mi('VMOV_cc', reg2.value, reg1.value, cond=AL)]
        self.mov(reg1, reg2, expected)

    def test_mov_vfp_reg_to_stack(self):
        reg = vfp(7)
        s = stack_float(3)
        expected = [mi('PUSH', [ip.value], cond=AL),
                    mi('SUB_ri', ip.value, fp.value, 12, cond=AL),
                    mi('VSTR', reg.value, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL)]
        self.mov(reg, s, expected)

    def test_mov_vfp_reg_to_large_stackloc(self):
        reg = vfp(7)
        s = stack_float(800)
        expected = [mi('PUSH', [ip.value], cond=AL),
                    mi('gen_load_int', ip.value, 3200, cond=AL),
                    mi('SUB_rr', ip.value, fp.value, ip.value, cond=AL),
                    mi('VSTR', reg.value, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL)]
        self.mov(reg, s, expected)

    def test_mov_stack_to_vfp_reg(self):
        reg = vfp(7)
        s = stack_float(3)
        expected = [mi('PUSH', [ip.value], cond=AL),
                    mi('SUB_ri', ip.value, fp.value, 12, cond=AL),
                    mi('VLDR', reg.value, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL)]
        self.mov(s, reg, expected)

    def test_mov_big_stackloc_to_vfp_reg(self):
        reg = vfp(7)
        s = stack_float(800)
        expected = [mi('PUSH', [ip.value], cond=AL),
                    mi('gen_load_int', ip.value, 3200, cond=AL),
                    mi('SUB_rr', ip.value, fp.value, ip.value, cond=AL),
                    mi('VSTR', reg.value, ip.value, cond=AL),
                    mi('POP', [ip.value], cond=AL)]
        self.mov(reg, s, expected)

    def test_unsopported_cases(self):
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(imm(1), imm(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(imm(1), imm_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(imm(1), vfp(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(imm_float(1), r(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(imm_float(1), stack(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(imm_float(1), stack_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(imm_float(1), imm_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(imm_float(1), imm(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(r(1), imm(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(r(1), imm_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(vfp(1), imm(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(vfp(1), imm_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(stack(1), stack(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(stack(1), imm_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(stack(1), imm(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(stack(1), vfp(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(stack_float(1), r(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(stack_float(1), imm(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(stack_float(1), imm_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(stack_float(1), stack_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(vfp(1), imm(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(vfp(1), imm_float(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(vfp(1), r(2))')
        py.test.raises(AssertionError, 'self.asm.regalloc_mov(vfp(1), stack(2))')

class TestMovFromToVFPLoc(object):
    pass
