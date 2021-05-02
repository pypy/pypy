#!/usr/bin/env python

from hypothesis import assume, given, settings, strategies
from rpython.jit.backend.riscv import codebuilder
from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv import rounding_modes
from rpython.jit.backend.riscv.instructions import all_instructions
from rpython.jit.backend.riscv.test.external_assembler import assemble


class CodeBuilder(codebuilder.AbstractRISCVBuilder):
    def __init__(self):
        self.buffer = []

    def writechar(self, char):
        self.buffer.append(char)

    def hexdump(self):
        return ''.join(self.buffer)


class TestCodeBuilder(object):
    pass


def _get_op_name(mnemonic):
    return mnemonic.replace('_', '.')

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
