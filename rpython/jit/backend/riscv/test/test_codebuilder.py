#!/usr/bin/env python

from hypothesis import assume, given, settings, strategies
from rpython.jit.backend.riscv import codebuilder
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv import rounding_modes
from rpython.jit.backend.riscv.arch import XLEN
from rpython.jit.backend.riscv.instructions import (
    AMO_ACQUIRE, AMO_RELEASE, FMO_INPUT, FMO_OUTPUT, FMO_READ, FMO_WRITE,
    all_instructions)
from rpython.jit.backend.riscv.test.external_assembler import assemble
import py


class CodeBuilder(codebuilder.AbstractRISCVBuilder):
    def __init__(self):
        self.buffer = []
        self._int_const_pool = {}
        self._float_const_pool = {}

    def writechar(self, char):
        self.buffer.append(char)

    def overwrite(self, index, char):
        self.buffer[index] = char

    def hexdump(self):
        return ''.join(self.buffer)

    def append_pending_int_constant(self, load_inst_pos, reg, const_value):
        self._int_const_pool[load_inst_pos] = (reg, const_value)

    def append_pending_float_constant(self, load_inst_pos, reg, const_value):
        self._float_const_pool[load_inst_pos] = (reg, const_value)

    def _get_relative_pos_for_load_imm(self, break_basic_block=False):
        return len(self.buffer)

    emit_pending_constants = codebuilder._emit_pending_constants


class TestCodeBuilder(object):
    pass


def _get_op_name(mnemonic):
    return mnemonic.replace('_', '.')

def _get_fence_memory_order_str(mo_bits):
    res = ''
    if mo_bits & FMO_INPUT:
        res += 'i'
    if mo_bits & FMO_OUTPUT:
        res += 'o'
    if mo_bits & FMO_READ:
        res += 'r'
    if mo_bits & FMO_WRITE:
        res += 'w'
    return res

def _get_amo_suffix(aqrl):
    res = ''
    if aqrl & AMO_ACQUIRE:
        res += 'aq'
    if aqrl & AMO_RELEASE:
        res += 'rl'
    return '.' + res if res else ''

def _get_op_test_strategy(op_spec):
    if op_spec == 'R' or op_spec == 'RB':
        return strategies.sampled_from(r.registers_except_zero)
    elif op_spec == 'F':
        return strategies.sampled_from(r.fp_registers)
    elif op_spec == 'I12':
        return strategies.integers(min_value=-2**11, max_value=2**11 - 1)
    elif op_spec == 'I13':
        return strategies.integers(min_value=-2**11, max_value=2**11 - 1) \
                .map(lambda x: x * 2).filter(lambda x: x != 2)
    elif op_spec == 'U20':
        return strategies.integers(min_value=0, max_value=2**20 - 1)
    elif op_spec == 'I21':
        return strategies.integers(min_value=-2**19, max_value=2**19 - 1) \
                .map(lambda x: x * 2).filter(lambda x: x != 2)
    elif op_spec == 'SH5':
        return strategies.integers(min_value=0, max_value=2**5 - 1)
    elif op_spec == 'SH6':
        return strategies.integers(min_value=0, max_value=2**6 - 1)
    elif op_spec == 'RM':
        return strategies.sampled_from(rounding_modes.all_rounding_modes)
    elif op_spec == 'FMO':
        return strategies.integers(min_value=1, max_value=15)
    elif op_spec == 'AMO':
        return strategies.integers(min_value=0, max_value=3)
    elif op_spec == 'AMOLR':
        return strategies.sampled_from([0, AMO_ACQUIRE,
                                        AMO_ACQUIRE | AMO_RELEASE])
    elif op_spec == 'AMOSC':
        return strategies.sampled_from([0, AMO_RELEASE,
                                        AMO_ACQUIRE | AMO_RELEASE])
    assert False, 'unhandled op spec: ' + op_spec

def _gen_r_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 3

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           rs1=_get_op_test_strategy(op_spec[1]),
           rs2=_get_op_test_strategy(op_spec[2]))
    def test(self, rd, rs1, rs2):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, rs1, rs2)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        asm = '%s %s, %s, %s' % (op_name, rd, rs1, rs2)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_i_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 3

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           rs1=_get_op_test_strategy(op_spec[1]),
           imm=_get_op_test_strategy(op_spec[2]))
    def test(self, rd, rs1, imm):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, rs1, imm)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        if op_spec[1] == 'RB':
            asm = '%s %s, %d(%s)' % (op_name, rd, imm, rs1)
        else:
            asm = '%s %s, %s, %d' % (op_name, rd, rs1, imm)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_s_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 3
    assert op_spec[1] == 'RB'

    @settings(max_examples=20)
    @given(rs2=_get_op_test_strategy(op_spec[0]),
           rs1=_get_op_test_strategy(op_spec[1]),
           imm=_get_op_test_strategy(op_spec[2]))
    def test(self, rs2, rs1, imm):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rs2, rs1, imm)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        asm = '%s %s, %d(%s)' % (op_name, rs2, imm, rs1)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_b_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 3

    @settings(max_examples=20)
    @given(rs1=_get_op_test_strategy(op_spec[0]),
           rs2=_get_op_test_strategy(op_spec[1]),
           imm=_get_op_test_strategy(op_spec[2]))
    def test(self, rs1, rs2, imm):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rs1, rs2, imm)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        if imm <= 0:
            asm = '''
            .L0:
                .fill %d
                %s %s, %s, .L0
            ''' % (-imm, op_name, rs1, rs2)
            ref_out = assemble(asm)
            assert len(ref_out) == -imm + 4
            assert ref_out[0:-imm] == '\x00' * -imm
            ref_out = ref_out[-imm:]
        else:
            asm = '''
                %s %s, %s, .L0
                .fill %d
            .L0:
            ''' % (op_name, rs1, rs2, imm - 4)
            ref_out = assemble(asm)
            assert len(ref_out) == imm
            assert ref_out[4:] == '\x00' * (imm - 4)
            ref_out = ref_out[0:4]

        assert ref_out == test_out

    return test

def _gen_u_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 2

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           imm=_get_op_test_strategy(op_spec[1]))
    def test(self, rd, imm):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, imm)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        asm = '%s %s, %d' % (op_name, rd, imm)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_j_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 2

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           imm=_get_op_test_strategy(op_spec[1]))
    def test(self, rd, imm):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, imm)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        if imm <= 0:
            asm = '''
            .L0:
                .fill %d
                %s %s, .L0
            ''' % (-imm, op_name, rd)
            ref_out = assemble(asm)
            assert len(ref_out) == -imm + 4
            assert ref_out[0:-imm] == '\x00' * -imm
            ref_out = ref_out[-imm:]
        else:
            asm = '''
                %s %s, .L0
                .fill %d
            .L0:
            ''' % (op_name, rd, imm - 4)
            ref_out = assemble(asm)
            assert len(ref_out) == imm
            assert ref_out[4:] == '\x00' * (imm - 4)
            ref_out = ref_out[0:4]

        assert ref_out == test_out

    return test

def _gen_r4_rm_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 5

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           rs1=_get_op_test_strategy(op_spec[1]),
           rs2=_get_op_test_strategy(op_spec[2]),
           rs3=_get_op_test_strategy(op_spec[3]),
           rm=_get_op_test_strategy(op_spec[4]))
    def test(self, rd, rs1, rs2, rs3, rm):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, rs1, rs2, rs3, rm)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        asm = '%s %s, %s, %s, %s, %s' % (op_name, rd, rs1, rs2, rs3, rm)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_r_rm_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 4

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           rs1=_get_op_test_strategy(op_spec[1]),
           rs2=_get_op_test_strategy(op_spec[2]),
           rm=_get_op_test_strategy(op_spec[3]))
    def test(self, rd, rs1, rs2, rm):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, rs1, rs2, rm)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        asm = '%s %s, %s, %s, %s' % (op_name, rd, rs1, rs2, rm)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_i12_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 2

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           rs1=_get_op_test_strategy(op_spec[1]))
    def test(self, rd, rs1):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, rs1)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        asm = '%s %s, %s' % (op_name, rd, rs1)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_i12_rm_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 3

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           rs1=_get_op_test_strategy(op_spec[1]),
           rm=_get_op_test_strategy(op_spec[2]))
    def test(self, rd, rs1, rm):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, rs1, rm)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        asm = '%s %s, %s, %s' % (op_name, rd, rs1, rm)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_a_type_instr_test(mnemonic, instr_type, op_spec):
    assert op_spec == ''

    def test(self):
        cb = CodeBuilder()
        getattr(cb, mnemonic)()
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        asm = '%s' % (op_name)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_f_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 2

    @settings(max_examples=20)
    @given(pred_order=_get_op_test_strategy(op_spec[0]),
           succ_order=_get_op_test_strategy(op_spec[1]))
    def test(self, pred_order, succ_order):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(pred_order, succ_order)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic)
        pred_order_str = _get_fence_memory_order_str(pred_order)
        succ_order_str = _get_fence_memory_order_str(succ_order)
        asm = '%s %s, %s' % (op_name, pred_order_str, succ_order_str)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_amo2_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 3

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           rs1=_get_op_test_strategy(op_spec[1]),
           aqrl=_get_op_test_strategy(op_spec[2]))
    def test(self, rd, rs1, aqrl):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, rs1, aqrl)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic) + _get_amo_suffix(aqrl)
        asm = '%s %s, (%s)' % (op_name, rd, rs1)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

def _gen_amo3_type_instr_test(mnemonic, instr_type, op_spec):
    op_spec = op_spec.split(':')
    assert len(op_spec) == 4

    @settings(max_examples=20)
    @given(rd=_get_op_test_strategy(op_spec[0]),
           rs2=_get_op_test_strategy(op_spec[1]),
           rs1=_get_op_test_strategy(op_spec[2]),
           aqrl=_get_op_test_strategy(op_spec[3]))
    def test(self, rd, rs2, rs1, aqrl):
        cb = CodeBuilder()
        getattr(cb, mnemonic)(rd, rs2, rs1, aqrl)
        test_out = cb.hexdump()

        op_name = _get_op_name(mnemonic) + _get_amo_suffix(aqrl)
        # Note: AMO instruction assembly puts rs2 in parentheses and at the
        # end.
        asm = '%s %s, %s, (%s)' % (op_name, rd, rs2, rs1)
        ref_out = assemble(asm)

        assert ref_out == test_out

    return test

_INSTR_TYPE_DICT = {
    'R': _gen_r_type_instr_test,
    'I': _gen_i_type_instr_test,
    'S': _gen_s_type_instr_test,
    'B': _gen_b_type_instr_test,
    'U': _gen_u_type_instr_test,
    'J': _gen_j_type_instr_test,
    'I_SHAMT5': _gen_i_type_instr_test,
    'I_SHAMT6': _gen_i_type_instr_test,
    'R4_RM': _gen_r4_rm_type_instr_test,
    'R_RM': _gen_r_rm_type_instr_test,
    'I12': _gen_i12_type_instr_test,
    'I12_RM': _gen_i12_rm_type_instr_test,
    'A': _gen_a_type_instr_test,
    'F': _gen_f_type_instr_test,
    'AMO2': _gen_amo2_type_instr_test,
    'AMO3': _gen_amo3_type_instr_test,
}

def _gen_instr_test(mnemonic, instr_type, op_spec):
    return _INSTR_TYPE_DICT[instr_type](mnemonic, instr_type, op_spec)

def _gen_all_instr_tests(cls):
    for mnemonic, instr_type, op_spec, fields in all_instructions:
        if instr_type not in _INSTR_TYPE_DICT:
            continue
        setattr(cls, 'test_' + mnemonic,
                _gen_instr_test(mnemonic, instr_type, op_spec))

_gen_all_instr_tests(TestCodeBuilder)


class TestLoadImm(object):
    def test_load_int_imm_single_addi(self):
        rd = r.x5
        imm = -42

        cb = CodeBuilder()
        cb.load_int_imm(rd.value, imm)
        test_out = cb.hexdump()

        cb = CodeBuilder()
        cb.ADDI(rd.value, r.zero.value, imm)
        ref_out = cb.hexdump()

        assert ref_out == test_out

    def test_load_int_imm_single_lui(self):
        rd = r.x5
        imm = -8192

        cb = CodeBuilder()
        cb.load_int_imm(rd.value, imm)
        test_out = cb.hexdump()

        cb = CodeBuilder()
        cb.LUI(rd.value, 0xffffe)
        ref_out = cb.hexdump()

        assert ref_out == test_out

    def test_load_int_imm_lui_addiw(self):
        rd = r.x5
        imm = -8191

        cb = CodeBuilder()
        cb.load_int_imm(rd.value, imm)
        test_out = cb.hexdump()

        cb = CodeBuilder()
        cb.LUI(rd.value, 0xffffe)
        cb.ADDIW(rd.value, rd.value, 0x001)
        ref_out = cb.hexdump()

        assert ref_out == test_out

    def test_load_int_imm_lui_addiw_i32_max(self):
        rd = r.x5
        imm = 0x7fffffff

        cb = CodeBuilder()
        cb.load_int_imm(rd.value, imm)
        test_out = cb.hexdump()

        cb = CodeBuilder()
        cb.LUI(rd.value, 0x80000)
        cb.ADDIW(rd.value, rd.value, -1)
        ref_out = cb.hexdump()

        assert ref_out == test_out

    def test_load_int_imm_lui_addiw_i32_min(self):
        rd = r.x5
        imm = -0x80000000

        cb = CodeBuilder()
        cb.load_int_imm(rd.value, imm)
        test_out = cb.hexdump()

        cb = CodeBuilder()
        cb.LUI(rd.value, 0x80000)
        ref_out = cb.hexdump()

        assert ref_out == test_out

    def test_load_int_imm_lui_addiw_i32_next_min(self):
        rd = r.x5
        imm = -0x7fffffff

        cb = CodeBuilder()
        cb.load_int_imm(rd.value, imm)
        test_out = cb.hexdump()

        cb = CodeBuilder()
        cb.LUI(rd.value, 0x80000)
        cb.ADDIW(rd.value, rd.value, 1)
        ref_out = cb.hexdump()

        assert ref_out == test_out

    def test_load_int_imm_large_imm(self):
        if XLEN != 8:
            py.test.skip('only 64-bit need constant pool, skip 32-bit')

        rd = r.x10
        imm = 0x1122334455667788

        cb = CodeBuilder()
        cb.load_int_imm(rd.value, imm)
        cb.RET()
        cb.emit_pending_constants()
        test_out = cb.hexdump()

        cb = CodeBuilder()
        cb.AUIPC(rd.value, 0)
        cb.load_int(rd.value, rd.value, 16)
        cb.RET()
        cb.write32(0)  # Automatically inserted alignment
        cb.write64(imm)
        ref_out = cb.hexdump()

        assert ref_out == test_out

    def test_load_float_imm(self):
        rd = r.f10
        imm = 0x3ff0000000000000

        cb = CodeBuilder()
        cb.load_float_imm(rd.value, imm)
        cb.RET()
        cb.emit_pending_constants()
        test_out = cb.hexdump()

        cb = CodeBuilder()
        cb.AUIPC(r.x31.value, 0)
        cb.load_float(rd.value, r.x31.value, 16)
        cb.RET()
        cb.write32(0)  # Automatically inserted alignment
        cb.write64(imm)
        ref_out = cb.hexdump()

        assert ref_out == test_out
