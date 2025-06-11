from rpython.flowspace.model import Constant
from rpython.jit.codewriter.jitcode import SwitchDictDescr
from rpython.jit.codewriter.flatten import SSARepr, Label, TLabel, Register
from rpython.jit.codewriter.assembler import Assembler, AssemblerError
from rpython.rtyper.lltypesystem import lltype, llmemory

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
            pc = 13
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
                    pc = self.pc = 9
                    continue
                if value == 2:
                    pc = self.pc = 14
                    continue
                if value == 7:
                    pc = self.pc = 19
                    continue
            self._result_argcode = 'v'
            self.opimpl_switch(self.registers_i[22], glob0, 3)
            pc = self.pc
            if pc == 9: pc = 9
            elif pc == 14: pc = 14
            elif pc == 19: pc = 19
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
