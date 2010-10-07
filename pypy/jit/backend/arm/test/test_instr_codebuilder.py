from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import codebuilder
from gen import assemble
import py
class CodeBuilder(codebuilder.ARMv7Builder):
    def __init__(self):
        self.buffer = []

    def writechar(self, char):
        self.buffer.append(char)

    def hexdump(self):
        return ''.join(self.buffer)

class TestInstrCodeBuilder(object):
    def setup_method(self, ffuu_method):
        self.cb = CodeBuilder()

    def test_ldr(self):
        self.cb.LDR_ri(r.r0, r.r1)
        self.assert_equal('LDR r0, [r1]')

    def test_ldr_neg(self):
        self.cb.LDR_ri(r.r3, r.fp, -16)
        self.assert_equal('LDR r3, [fp, #-16]')

    def test_add_ri(self):
        self.cb.ADD_ri(r.r0, r.r1, 1)
        self.assert_equal('ADD r0, r1, #1')

    def test_mov_rr(self):
        self.cb.MOV_rr(r.r7, r.r12)
        self.assert_equal('MOV r7, r12')

    def test_mov_ri(self):
        self.cb.MOV_ri(r.r9, 123)
        self.assert_equal('MOV r9, #123')

    def test_mov_ri2(self):
        self.cb.MOV_ri(r.r9, 255)
        self.assert_equal('MOV r9, #255')

    def test_mov_ri_max(self):
        py.test.skip('Check the actual largest thing')
        self.cb.MOV_ri(r.r9, 0xFFF)
        self.assert_equal('MOV r9, #4095')

    def test_str_ri(self):
        self.cb.STR_ri(r.r9, r.r14)
        self.assert_equal('STR r9, [r14]')

    def test_asr_ri(self):
        self.cb.ASR_ri(r.r7, r.r5, 24)
        self.assert_equal('ASR r7, r5, #24')

    def test_orr_rr_no_shift(self):
        self.cb.ORR_rr(r.r0, r.r7,r.r12)
        self.assert_equal('ORR r0, r7, r12')

    def test_orr_rr_lsl_8(self):
        self.cb.ORR_rr(r.r0, r.r7,r.r12, 8)
        self.assert_equal('ORR r0, r7, r12, lsl #8')

    def test_push_one_reg(self):
        self.cb.PUSH([r.r1])
        self.assert_equal('PUSH {r1}')

    def test_push_multiple(self):
        self.cb.PUSH([r.r3, r.r1, r.r6, r.r8, r.sp, r.pc])
        self.assert_equal('PUSH {r3, r1, r6, r8, sp, pc}')

    def test_push_multiple2(self):
        self.cb.PUSH([r.fp, r.ip, r.lr, r.pc])
        self.assert_equal('PUSH {fp, ip, lr, pc}')

    def test_sub_ri(self):
        self.cb.SUB_ri(r.r2, r.r4, 123)
        self.assert_equal('SUB r2, r4, #123')

    def test_sub_ri2(self):
        py.test.skip('XXX check the actual largest value')
        self.cb.SUB_ri(r.r3, r.r7, 0xFFF)
        self.assert_equal('SUB r3, r7, #4095')

    def assert_equal(self, asm):
        assert self.cb.hexdump() == assemble(asm)

