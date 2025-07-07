from rpython.flowspace.model import Constant
from rpython.jit.codewriter.jitcode import SwitchDictDescr
from rpython.jit.codewriter.flatten import SSARepr, Label, TLabel, Register
from rpython.jit.codewriter.assembler import Assembler, AssemblerError
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.jit.codewriter.genextension import WorkList

import pytest

def test_assemble_loop():
    ssarepr = SSARepr("test", genextension=True)
    i0, i1 = Register('int', 0x16), Register('int', 0x17)
    ssarepr.insns = [
        (Label('L1'),),
        ('goto_if_not_int_gt', i0, Constant(4, lltype.Signed), TLabel('L2')),
        ('int_add', i1, i0, '->', i1),
        ('int_sub', i0, Constant(1, lltype.Signed), '->', i0),
        ('goto', TLabel('L1')),
        (Label('L2'),),
        ('int_return', i1),
        ]
    assembler = Assembler()
    jitcode = assembler.assemble(ssarepr, num_regs={'int': 0x18})
    assert jitcode._genext_source == """\
def jit_shortcut(self): # test
    pc = self.pc
    while 1:
        if pc == 0: # ('goto_if_not_int_gt', %i22, (4), TLabel('L2'))
            self.pc = 5
            self._result_argcode = 'v'
            self.opimpl_goto_if_not_int_gt(self.registers_i[22], ConstInt(4), 16, 0)
            pc = self.pc
            if pc == 5: pc = 5
            elif pc == 16: pc = 16
            else:
                assert 0 # unreachable
            continue
        if pc == 5: # ('int_add', %i23, %i22, '->', %i23)
            self.pc = 9
            self._result_argcode = 'i'
            self.registers_i[23] = self.opimpl_int_add(self.registers_i[23], self.registers_i[22])
            pc = 9
            continue
        if pc == 9: # ('int_sub', %i22, (1), '->', %i22)
            self.pc = 13
            self._result_argcode = 'i'
            self.registers_i[22] = self.opimpl_int_sub(self.registers_i[22], ConstInt(1))
            pc = 0
            continue
        if pc == 13: # ('goto', TLabel('L1'))
            self.pc = 16
            pc = self.pc = 0 # goto
            continue
            pc = 0
            continue
        if pc == 16: # ('int_return', %i23)
            self.pc = 18
            try:
                self.opimpl_int_return(self.registers_i[23])
            except ChangeFrame: return
            assert 0 # unreachable
        assert 0 # unreachable"""

def test_switch():
    ssarepr = SSARepr("test", genextension=True)
    i0 = Register('int', 0x16)
    switchdescr = SwitchDictDescr()
    switchdescr._labels = [(-5, Label("L1")), (2, Label("L2")),
                           (7, Label("L3"))]
    ssarepr.insns = [
        (Label("L0"),),
        ('-live-', i0),
        ('switch', i0, switchdescr),
        ('int_return', Constant(42, lltype.Signed)),
        ('---',),
        (Label("L1"),),
        ('-live-',),
        ('int_return', Constant(12, lltype.Signed)),
        ('---',),
        (Label("L2"),),
        ('-live-',),
        ('int_return', Constant(51, lltype.Signed)),
        ('---',),
        (Label("L3"),),
        ('-live-',),
        ('int_return', Constant(1212, lltype.Signed)),
        ('---',),
    ]
    assembler = Assembler()
    jitcode = assembler.assemble(ssarepr, num_regs={'int': 0x17})
    assert jitcode._genext_source == """\
def jit_shortcut(self): # test
    pc = self.pc
    while 1:
        if pc == 0: # ('-live-', %i22)
            self.pc = 3
            pass # live
            pc = 3
            continue
        if pc == 3: # ('switch', %i22, <SwitchDictDescr {-5: 9, 2: 14, 7: 19}>)
            self.pc = 7
            arg = self.registers_i[22]
            if arg.is_constant():
                value = arg.getint()
                if value == -5:
                    pc = self.pc = 12
                    continue
                elif value == 2:
                    pc = self.pc = 17
                    continue
                elif value == 7:
                    pc = self.pc = 22
                    continue
                else:
                    assert 0 # unreachable
            self._result_argcode = 'v'
            self.opimpl_switch(self.registers_i[22], glob0, 3)
            pc = self.pc
            if pc == 9: pc = 12
            elif pc == 14: pc = 17
            elif pc == 19: pc = 22
            elif pc == 7: pc = 7
            else:
                assert 0 # unreachable
            continue
        if pc == 7: # ('int_return', (42))
            self.pc = 9
            try:
                self.opimpl_int_return(ConstInt(42))
            except ChangeFrame: return
            assert 0 # unreachable
        if pc == 9: # ('-live-',)
            self.pc = 12
            pass # live
            pc = 12
            continue
        if pc == 12: # ('int_return', (12))
            self.pc = 14
            try:
                self.opimpl_int_return(ConstInt(12))
            except ChangeFrame: return
            assert 0 # unreachable
        if pc == 14: # ('-live-',)
            self.pc = 17
            pass # live
            pc = 17
            continue
        if pc == 17: # ('int_return', (51))
            self.pc = 19
            try:
                self.opimpl_int_return(ConstInt(51))
            except ChangeFrame: return
            assert 0 # unreachable
        if pc == 19: # ('-live-',)
            self.pc = 22
            pass # live
            pc = 22
            continue
        if pc == 22: # ('int_return', (1212))
            self.pc = 24
            try:
                self.opimpl_int_return(self.registers_i[23])
            except ChangeFrame: return
            assert 0 # unreachable
        assert 0 # unreachable"""

def test_skip_jump_to_live():
    ssarepr = SSARepr("test", genextension=True)
    i0, i1 = Register('int', 0x0), Register('int', 0x1)
    ssarepr.insns = [
        (Label('L1'),),
        ('int_sub', i0, Constant(1, lltype.Signed), '->', i0),
        ('int_add', i1, i0, '->', i1),
        ('-live-', i1, i0), # goal: make int_add jump to 'goto_if_not_int_gt'
        ('goto_if_not_int_gt', i0, Constant(0, lltype.Signed), TLabel('L2')),
        ('goto', TLabel('L1')),
        ('---',),
        (Label('L2'),),
        ('int_return', i1),
        ('---',)]
    assembler = Assembler()
    jitcode = assembler.assemble(ssarepr, num_regs={'int': 2})
    assert jitcode._genext_source == """\
def jit_shortcut(self): # test
    pc = self.pc
    while 1:
        if pc == 0: # ('int_sub', %i0, (1), '->', %i0)
            self.pc = 4
            self._result_argcode = 'i'
            self.registers_i[0] = self.opimpl_int_sub(self.registers_i[0], ConstInt(1))
            pc = 4
            continue
        if pc == 4: # ('int_add', %i1, %i0, '->', %i1)
            self.pc = 8
            self._result_argcode = 'i'
            self.registers_i[1] = self.opimpl_int_add(self.registers_i[1], self.registers_i[0])
            pc = 11
            continue
        if pc == 8: # ('-live-', %i1, %i0)
            self.pc = 11
            pass # live
            pc = 11
            continue
        if pc == 11: # ('goto_if_not_int_gt', %i0, (0), TLabel('L2'))
            self.pc = 16
            self._result_argcode = 'v'
            self.opimpl_goto_if_not_int_gt(self.registers_i[0], ConstInt(0), 19, 11)
            pc = self.pc
            if pc == 16: pc = 0
            elif pc == 19: pc = 19
            else:
                assert 0 # unreachable
            continue
        if pc == 16: # ('goto', TLabel('L1'))
            self.pc = 19
            pc = self.pc = 0 # goto
            continue
            pc = 0
            continue
        if pc == 19: # ('int_return', %i1)
            self.pc = 21
            try:
                self.opimpl_int_return(self.registers_i[1])
            except ChangeFrame: return
            assert 0 # unreachable
        assert 0 # unreachable"""


def test_skip_conditional_jump():
    ssarepr = SSARepr("test", genextension=True)
    i0, i1 = Register('int', 0x0), Register('int', 0x1)
    ssarepr.insns = [
        (Label('L1'),),
        ('int_sub', i0, Constant(1, lltype.Signed), '->', i0),
        ('int_add', i1, i0, '->', i1),
        ('-live-', i1, i0), # goal: make int_add jump to 'goto_if_not_int_gt'
        ('goto_if_not_int_gt', i0, Constant(0, lltype.Signed), TLabel('L2')),
        ('goto', TLabel('L1')),
        ('---',),
        (Label('L2'),),
        ('-live-', i1, i0),     # TODO
        (Label('L3'),),         # optimize -live- and goto L4 chan
        ('goto', TLabel('L4')), # here
        (Label('L4'),),
        ('int_return', i1),
        ('---',)]
    assembler = Assembler()
    jitcode = assembler.assemble(ssarepr, num_regs={'int': 2})
    assert jitcode._genext_source == """\
def jit_shortcut(self): # test
    pc = self.pc
    while 1:
        if pc == 0: # ('int_sub', %i0, (1), '->', %i0)
            self.pc = 4
            self._result_argcode = 'i'
            self.registers_i[0] = self.opimpl_int_sub(self.registers_i[0], ConstInt(1))
            pc = 4
            continue
        if pc == 4: # ('int_add', %i1, %i0, '->', %i1)
            self.pc = 8
            self._result_argcode = 'i'
            self.registers_i[1] = self.opimpl_int_add(self.registers_i[1], self.registers_i[0])
            pc = 11
            continue
        if pc == 8: # ('-live-', %i1, %i0)
            self.pc = 11
            pass # live
            pc = 11
            continue
        if pc == 11: # ('goto_if_not_int_gt', %i0, (0), TLabel('L2'))
            self.pc = 16
            self._result_argcode = 'v'
            self.opimpl_goto_if_not_int_gt(self.registers_i[0], ConstInt(0), 19, 11)
            pc = self.pc
            if pc == 16: pc = 0
            elif pc == 19: pc = 22
            else:
                assert 0 # unreachable
            continue
        if pc == 16: # ('goto', TLabel('L1'))
            self.pc = 19
            pc = self.pc = 0 # goto
            continue
            pc = 0
            continue
        if pc == 19: # ('-live-', %i1, %i0)
            self.pc = 22
            pass # live
            pc = 25
            continue
        if pc == 22: # ('goto', TLabel('L4'))
            self.pc = 25
            pc = self.pc = 25 # goto
            continue
            pc = 25
            continue
        if pc == 25: # ('int_return', %i1)
            self.pc = 27
            try:
                self.opimpl_int_return(self.registers_i[1])
            except ChangeFrame: return
            assert 0 # unreachable
        assert 0 # unreachable"""


def test_skip_chained_jump_1():
    ssarepr = SSARepr("test", genextension=True)
    i0, i1 = Register('int', 0x0), Register('int', 0x1)
    ssarepr.insns = [
        (Label('L1'),),
        ('int_sub', i0, Constant(1, lltype.Signed), '->', i0),
        ('int_add', i1, i0, '->', i1),
        ('goto', TLabel('L2'),),
        (Label('L3'),),
        ('-live-', i1, i0),
        ('goto', TLabel('L1'),),
        (Label('L2'),),
        ('goto', TLabel('L3'),),
        ('int_return', i1),
        ('---',)]
    assembler = Assembler()
    jitcode = assembler.assemble(ssarepr, num_regs={'int': 2})
    assert jitcode._genext_source == """\
def jit_shortcut(self): # test
    pc = self.pc
    while 1:
        if pc == 0: # ('int_sub', %i0, (1), '->', %i0)
            self.pc = 4
            self._result_argcode = 'i'
            self.registers_i[0] = self.opimpl_int_sub(self.registers_i[0], ConstInt(1))
            pc = 4
            continue
        if pc == 4: # ('int_add', %i1, %i0, '->', %i1)
            self.pc = 8
            self._result_argcode = 'i'
            self.registers_i[1] = self.opimpl_int_add(self.registers_i[1], self.registers_i[0])
            pc = 0
            continue
        if pc == 8: # ('goto', TLabel('L2'))
            self.pc = 11
            pc = self.pc = 0 # goto
            continue
            pc = 0
            continue
        if pc == 11: # ('-live-', %i1, %i0)
            self.pc = 14
            pass # live
            pc = 0
            continue
        if pc == 14: # ('goto', TLabel('L1'))
            self.pc = 17
            pc = self.pc = 0 # goto
            continue
            pc = 0
            continue
        if pc == 17: # ('goto', TLabel('L3'))
            self.pc = 20
            pc = self.pc = 0 # goto
            continue
            pc = 0
            continue
        if pc == 20: # ('int_return', %i1)
            self.pc = 22
            try:
                self.opimpl_int_return(self.registers_i[1])
            except ChangeFrame: return
            assert 0 # unreachable
        assert 0 # unreachable"""


def test_specialize_int_add():
    i0, i1, i2 = Register('int', 0), Register('int', 1), Register('int', 2)
    insn1 = (
        'int_add', i1, i0, '->', i1
    )
    work_list = WorkList()
    insn_specializer = work_list.specialize(insn1, {i0, i1}, 5) # i0 and i1 are unboxed in local variables already
    assert work_list.specialize(insn1, {i0, i1}, 5) is insn_specializer
    newpc = insn_specializer.get_pc()
    assert newpc == 100
    s = insn_specializer.make_code()
    assert s == "i1 = i1 + i0"
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == {i0, i1}


    insn2 = (
        'int_add', i1, i0, '->', i2
    )
    insn_specializer = work_list.specialize(insn2, {i0, i1}, 7) # i0 and i1 are unboxed in local variables already
    s = insn_specializer.make_code()
    assert s == "i2 = i1 + i0"
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == {i0, i1, i2}

    insn_specializer = work_list.specialize(insn1, set(), 5) # i0 and i1 are unboxed in local variables already
    s = insn_specializer.make_code()
    assert s == """\
ri1 = self.registers_i[1]
ri0 = self.registers_i[0]
if ri1.is_constant() and ri0.is_constant():
    i1 = ri1.getint()
    i0 = ri0.getint()
    pc = 100
    continue
else:
    self.registers_i[1] = self.opimpl_int_add(ri1, ri0)"""
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == set()


    insn_specializer = work_list.specialize(insn1, {i2}, 5) # i0 and i1 are unboxed in local variables already
    s = insn_specializer.make_code()
    assert s == """\
ri1 = self.registers_i[1]
ri0 = self.registers_i[0]
if ri1.is_constant() and ri0.is_constant():
    i1 = ri1.getint()
    i0 = ri0.getint()
    pc = 103
    continue
else:
    self.registers_i[1] = self.opimpl_int_add(ri1, ri0)"""
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == {i2}

def test_int_add_const():
    i0, i1, i2 = Register('int', 0), Register('int', 1), Register('int', 2)
    insn1 = (
        'int_add', i0, Constant(1, lltype.Signed), '->', i1
    )
    work_list = WorkList()
    insn_specializer = work_list.specialize(insn1, {i0}, 5)
    newpc = insn_specializer.get_pc()
    assert newpc == 100
    s = insn_specializer.make_code()
    assert s == "i1 = i0 + 1"
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == {i0, i1}

    insn_specializer = work_list.specialize(insn1, set(), 5)
    newpc = insn_specializer.get_pc()
    assert newpc == 5
    s = insn_specializer.make_code()
    assert s == """\
ri0 = self.registers_i[0]
if ri0.is_constant():
    i0 = ri0.getint()
    pc = 100
    continue
else:
    self.registers_i[1] = self.opimpl_int_add(ri0, ConstInt(1))"""
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == set()

def test_int_sub():
    i0, i1, i2 = Register('int', 0), Register('int', 1), Register('int', 2)
    insn1 = (
        'int_sub', i1, i0, '->', i1
    )
    work_list = WorkList()
    insn_specializer = work_list.specialize(insn1, {i0, i1}, 5) # i0 and i1 are unboxed in local variables already
    assert work_list.specialize(insn1, {i0, i1}, 5) is insn_specializer
    newpc = insn_specializer.get_pc()
    assert newpc == 100
    s = insn_specializer.make_code()
    assert s == "i1 = i1 - i0"
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == {i0, i1}


    insn2 = (
        'int_sub', i1, i0, '->', i2
    )
    insn_specializer = work_list.specialize(insn2, {i0, i1}, 7) # i0 and i1 are unboxed in local variables already
    s = insn_specializer.make_code()
    assert s == "i2 = i1 - i0"
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == {i0, i1, i2}

    insn_specializer = work_list.specialize(insn1, set(), 5) # i0 and i1 are unboxed in local variables already
    s = insn_specializer.make_code()
    assert s == """\
ri1 = self.registers_i[1]
ri0 = self.registers_i[0]
if ri1.is_constant() and ri0.is_constant():
    i1 = ri1.getint()
    i0 = ri0.getint()
    pc = 100
    continue
else:
    self.registers_i[1] = self.opimpl_int_sub(ri1, ri0)"""

def test_int_sub_first_arg_is_const():
    pass

def test_strgetitem():
    r0, i0, i1 = Register('ref', 0), Register('int', 0), Register('int', 1)
    insn1 = ('strgetitem', r0, i0, '->', i1)
    work_list = WorkList()

    insn_specializer = work_list.specialize(insn1, set(), 5) # i0 and i1 are unboxed in local variables already
    s = insn_specializer.make_code()
    assert s == """\
rr0 = self.registers_r[0]
ri0 = self.registers_i[0]
if rr0.is_constant() and ri0.is_constant():
    r0 = rr0.getref_base()
    i0 = ri0.getint()
    pc = 100
    continue
else:
    self.registers_i[1] = self.opimpl_strgetitem(rr0, ri0)"""

    insn_specializer = work_list.specialize(insn1, {i0, r0}, 5) # i0 and i1 are unboxed in local variables already
    assert work_list.specialize(insn1, {i0, r0}, 5) is insn_specializer
    newpc = insn_specializer.get_pc()
    assert newpc == 100
    s = insn_specializer.make_code()
    assert s == "i1 = ord(lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), r0).chars[i0])"
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == {r0, i0, i1}

def test_goto_if_not_int_lt():
    i0, i1, i2 = Register('int', 0), Register('int', 1), Register('int', 2)
    L1 = TLabel('L1')
    insn = ('goto_if_not_int_lt', i0, i1, L1)
    work_list = WorkList()

    # unspecialized case
    insn_specializer = work_list.specialize(insn, set(), 5, L1)
    newpc = insn_specializer.get_pc()
    assert newpc == 5
    s = insn_specializer.make_code()
    assert s == """\
ri0 = self.registers_i[0]
ri1 = self.registers_i[1]
if ri0.is_constant() and ri1.is_constant():
    i0 = ri0.getint()
    i1 = ri1.getint()
    cond = i0 < i1
    if not cond: pc = 100
    continue
condbox = self.opimpl_int_lt(ri0, ri1)
self.opimpl_goto_if_not(condbox, 100, 5)"""

def test_int_guard_value():
    i0, i1, i2 = Register('int', 0), Register('int', 1), Register('int', 2)
    insn = ('int_guard_value', i0)
    insns = [insn]
    work_list = WorkList()
    insn_specializer = work_list.specialize(insn, {i0}, 5)
    newpc = insn_specializer.get_pc()
    assert newpc == 100
    s = insn_specializer.make_code()
    assert s == 'pass # int_guard_value, argument is already constant'
    next_constant_registers = insn_specializer.get_next_constant_registers()
    assert next_constant_registers == {i0}

    insn_specializer = work_list.specialize(insn, set(), 5)
    s = insn_specializer.make_code()
    assert s == """\
ri0 = self.registers_i[0]
if ri0.is_constant():
    pc = 100
    continue
self.opimpl_int_guard_value(self.registers_i[0], 5)"""

    insn_specializer = work_list.specialize(insn, {i1, i2}, 5)
    s = insn_specializer.make_code()
    # we need to sync the registers from the unboxed values to allow the guard to be created
    # TODO: only do this for registers that are alive at this point
    assert s == """\
ri0 = self.registers_i[0]
if ri0.is_constant():
    pc = 102
    continue
self.registers_i[1] = ConstInt(i1)
self.registers_i[2] = ConstInt(i2)
self.opimpl_int_guard_value(self.registers_i[0], 5)"""

def test_switch():
    pass

def dont_test_int_add_sequence():
    i0, i1, i2 = Register('int', 0), Register('int', 1), Register('int', 2)
    insns = [
        ('int_add', i0, Constant(1, lltype.Signed), '->', i1),
        ('int_add', i0, i1, '->', i2)]
    work_list = WorkList(insns)
    insn_specializer = work_list.specialize(insn1, {i0}, 5)
    newpc = insn_specializer.get_pc()
    assert newpc == 100
    s = insn_specializer.make_code()

#def test_fast_to_slow():
