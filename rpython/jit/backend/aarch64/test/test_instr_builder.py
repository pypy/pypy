
from rpython.jit.backend.aarch64 import registers as r
from rpython.jit.backend.aarch64 import codebuilder
from rpython.jit.backend.aarch64.test.gen import assemble

class CodeBuilder(codebuilder.InstrBuilder):
    def __init__(self, arch_version=7):
        self.arch_version = arch_version
        self.buffer = []

    def writechar(self, char):
        self.buffer.append(char)

    def hexdump(self):
        return ''.join(self.buffer)

class TestInstrBuilder(object):
    def setup_method(self, meth):
        self.cb = CodeBuilder()

    def test_ret(self):
        self.cb.RET_r(r.x0.value)
        res = self.cb.hexdump()
        exp = assemble('RET x0')
        assert res == exp
        self.cb = CodeBuilder()
        self.cb.RET_r(r.x0.value)
        self.cb.RET_r(r.x5.value)
        self.cb.RET_r(r.x3.value)
        assert self.cb.hexdump() == assemble('RET x0\nRET x5\n RET x3')

    def test_call_header(self):
        self.cb.STP_rr_preindex(r.x29.value, r.x30.value, r.sp.value, -32)
        assert self.cb.hexdump() == assemble("STP x29, x30, [sp, -32]!")
