from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import codebuilder
from pypy.jit.backend.arm import instructions
from pypy.jit.backend.arm.test.support import requires_arm_as
from gen import assemble
import py

requires_arm_as()

class CodeBuilder(codebuilder.ARMv7Builder):
    def __init__(self):
        self.buffer = []

    def writechar(self, char):
        self.buffer.append(char)

    def hexdump(self):
        return ''.join(self.buffer)

class ASMTest(object):
    def assert_equal(self, asm):
        assert self.cb.hexdump() == assemble(asm)


class TestInstrCodeBuilder(ASMTest):
    def setup_method(self, ffuu_method):
        self.cb = CodeBuilder()

    def test_ldr(self):
        self.cb.LDR_ri(r.r0.value, r.r1.value)
        self.assert_equal('LDR r0, [r1]')

    def test_ldr_neg(self):
        self.cb.LDR_ri(r.r3.value, r.fp.value, -16)
        self.assert_equal('LDR r3, [fp, #-16]')

    def test_add_ri(self):
        self.cb.ADD_ri(r.r0.value, r.r1.value, 1)
        self.assert_equal('ADD r0, r1, #1')

    def test_mov_rr(self):
        self.cb.MOV_rr(r.r7.value, r.r12.value)
        self.assert_equal('MOV r7, r12')

    def test_mov_ri(self):
        self.cb.MOV_ri(r.r9.value, 123)
        self.assert_equal('MOV r9, #123')

    def test_mov_ri2(self):
        self.cb.MOV_ri(r.r9.value, 255)
        self.assert_equal('MOV r9, #255')

    def test_mov_ri_max(self):
        py.test.skip('Check the actual largest thing')
        self.cb.MOV_ri(r.r9.value, 0xFFF)
        self.assert_equal('MOV r9, #4095')

    def test_str_ri(self):
        self.cb.STR_ri(r.r9.value, r.r14.value)
        self.assert_equal('STR r9, [r14]')

    def test_str_ri_offset(self):
        self.cb.STR_ri(r.r9.value, r.r14.value, 23)
        self.assert_equal('STR r9, [r14, #23]')

    def test_str_ri_offset(self):
        self.cb.STR_ri(r.r9.value, r.r14.value, -20)
        self.assert_equal('STR r9, [r14, #-20]')

    def test_asr_ri(self):
        self.cb.ASR_ri(r.r7.value, r.r5.value, 24)
        self.assert_equal('ASR r7, r5, #24')

    def test_orr_rr_no_shift(self):
        self.cb.ORR_rr(r.r0.value, r.r7.value,r.r12.value)
        self.assert_equal('ORR r0, r7, r12')

    def test_orr_rr_lsl_8(self):
        self.cb.ORR_rr(r.r0.value, r.r7.value,r.r12.value, 8)
        self.assert_equal('ORR r0, r7, r12, lsl #8')

    def test_push_one_reg(self):
        self.cb.PUSH([r.r1.value])
        self.assert_equal('PUSH {r1}')

    def test_push_multiple(self):
        self.cb.PUSH([reg.value for reg in [r.r1, r.r3, r.r6, r.r8, r.pc]])
        self.assert_equal('PUSH {r1, r3, r6, r8, pc}')

    def test_push_multiple2(self):
        self.cb.PUSH([reg.value for reg in [r.fp, r.ip, r.lr, r.pc]])
        self.assert_equal('PUSH {fp, ip, lr, pc}')

    def test_ldm_one_reg(self):
        self.cb.LDM(r.sp.value, [r.fp.value])
        self.assert_equal('LDM sp, {fp}')

    def test_ldm_multiple_reg(self):
        self.cb.LDM(r.sp.value, [reg.value for reg in [r.fp, r.ip, r.lr]])
        self.assert_equal('LDM sp, {fp, ip, lr}')

    def test_ldm_multiple_reg2(self):
        self.cb.LDM(r.sp.value, [reg.value for reg in [r.fp, r.sp, r.pc]])
        self.assert_equal("LDM sp, {fp, sp, pc}")

    def test_sub_ri(self):
        self.cb.SUB_ri(r.r2.value, r.r4.value, 123)
        self.assert_equal('SUB r2, r4, #123')

    def test_sub_ri2(self):
        py.test.skip('XXX check the actual largest value')
        self.cb.SUB_ri(r.r3.value, r.r7.value, 0xFFF)
        self.assert_equal('SUB r3, r7, #4095')

    def test_cmp_ri(self):
        self.cb.CMP_ri(r.r3.value, 123)
        self.assert_equal('CMP r3, #123')

    def test_mcr(self):
        self.cb.MCR(15, 0, r.r1.value, 7, 10,0)

        self.assert_equal('MCR P15, 0, r1, c7, c10, 0')


class TestInstrCodeBuilderForGeneratedInstr(ASMTest):
    def setup_method(self, ffuu_method):
        self.cb = CodeBuilder()

# XXX refactor this functions

def build_test(builder, key, value, test_name):
    test = builder(key, value)
    setattr(TestInstrCodeBuilderForGeneratedInstr, test_name % key, test)

def gen_test_data_proc_imm_func(name, table):
    if table['result'] and table['base']:
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, r.r7.value, 23)
            self.assert_equal('%s r3, r7, #23' % name[:name.index('_')])
            py.test.raises(ValueError, 'func(r.r3.value, r.r7.value, -12)')
    elif not table['base']:
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, 23)
            self.assert_equal('%s r3, #23' % name[:name.index('_')])
    else:
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, 23)
            self.assert_equal('%s r3, #23' % name[:name.index('_')])
    return f

def gen_test_imm_func(name, table):
    def f(self):
        func = getattr(self.cb, name)
        func(r.r3.value, r.r7.value, 23)
        self.assert_equal('%s r3, [r7, #23]' % name[:name.index('_')])
    return f

def gen_test_reg_func(name, table):
    def f(self):
        func = getattr(self.cb, name)
        func(r.r3.value, r.r7.value, r.r12.value)
        self.assert_equal('%s r3, [r7, r12]' % name[:name.index('_')])
    return f

def gen_test_mul_func(name, table):
    if 'acc' in table and table['acc']:
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, r.r7.value, r.r12.value, r.r13.value)
            self.assert_equal('%s r3, r7, r12, r13' % name)
    elif 'long' in table and table['long']:
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, r.r13.value, r.r7.value, r.r12.value)
            self.assert_equal('%s r13, r3, r7, r12' % name)
    else:
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, r.r7.value, r.r12.value)
            self.assert_equal('%s r3, r7, r12' % name)
    return f

def gen_test_data_reg_shift_reg_func(name, table):
    if name[-2:] == 'rr':
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, r.r7.value, r.r12.value)
            self.assert_equal('%s r3, r7, r12' % name[:name.index('_')])

    else:
        if 'result' in table and not table['result']:
            result = False
        else:
            result = True
        if result:
            def f(self):
                func = getattr(self.cb, name)
                func(r.r3.value, r.r7.value, r.r8.value, r.r11.value, shifttype=0x2)
                self.assert_equal('%s r3, r7, r8, ASR r11' % name[:name.index('_')])
        else:
            def f(self):
                func = getattr(self.cb, name)
                func(r.r3.value, r.r7.value, r.r11.value, shifttype=0x2)
                self.assert_equal('%s r3, r7, ASR r11' % name[:name.index('_')])

    return f

def gen_test_data_reg_func(name, table):
    if name[-2:] == 'ri':
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, r.r7.value, 12)
            self.assert_equal('%s r3, r7, #12' % name[:name.index('_')])

    elif table['base'] and table['result']:
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, r.r7.value, r.r12.value)
            self.assert_equal('%s r3, r7, r12' % name[:name.index('_')])
    else:
        def f(self):
            func = getattr(self.cb, name)
            func(r.r3.value, r.r7.value)
            self.assert_equal('%s r3, r7' % name[:name.index('_')])

    return f

def build_tests():
    test_name = 'test_generated_%s'
    for key, value in instructions.load_store.iteritems():
        if value['imm']:
            f = gen_test_imm_func
        else:
            f = gen_test_reg_func
        build_test(f, key, value, test_name)

    for key, value, in instructions.data_proc.iteritems():
        build_test(gen_test_data_reg_func, key, value, test_name)

    for key, value, in instructions.data_proc_reg_shift_reg.iteritems():
        build_test(gen_test_data_reg_shift_reg_func, key, value, test_name)

    for key, value, in instructions.data_proc_imm.iteritems():
        build_test(gen_test_data_proc_imm_func, key, value, test_name)

    for key, value, in instructions.multiply.iteritems():
        build_test(gen_test_mul_func, key, value, test_name)

build_tests()
