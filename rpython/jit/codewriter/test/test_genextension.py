from rpython.flowspace.model import Constant
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
