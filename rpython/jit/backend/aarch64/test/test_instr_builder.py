from hypothesis import given, settings, strategies as st
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

    @settings(max_examples=20)
    @given(r1=st.sampled_from(r.registers))
    def test_ret(self, r1):
        cb = CodeBuilder()
        cb.RET_r(r1.value)
        res = cb.hexdump()
        exp = assemble('RET %r' % r1)
        assert res == exp

    @settings(max_examples=20)
    @given(r1=st.sampled_from(r.registers),
           r2=st.sampled_from(r.registers),
           offset=st.integers(min_value=-64, max_value=63))
    def test_STP_rr(self, r1, r2, offset):
        cb = CodeBuilder()
        cb.STP_rr_preindex(r1.value, r2.value, r.sp.value, offset * 8)
        assert cb.hexdump() == assemble("STP %r, %r, [sp, %d]!" % (r1, r2, offset * 8))
        cb = CodeBuilder()
        cb.STP_rri(r1.value, r2.value, r.sp.value, offset * 8)
        assert cb.hexdump() == assemble("STP %r, %r, [sp, %d]" % (r1, r2, offset * 8))

    @settings(max_examples=20)
    @given(r1=st.sampled_from(r.registers),
           r2=st.sampled_from(r.registers))
    def test_MOV_rr(self, r1, r2):
        cb = CodeBuilder()
        cb.MOV_rr(r1.value, r2.value)
        assert cb.hexdump() == assemble("MOV %r, %r" % (r1, r2))

    @settings(max_examples=20)
    @given(r1=st.sampled_from(r.registers),
           immed=st.integers(min_value=0, max_value=(1<<16) - 1))
    def test_MOVN(self, r1, immed):
        cb = CodeBuilder()
        cb.MOVN_r_u16(r1.value, immed)
        assert cb.hexdump() == assemble("MOV %r, %d" % (r1, ~immed))

    @settings(max_examples=20)
    @given(r1=st.sampled_from(r.registers),
           immed=st.integers(min_value=0, max_value=(1<<16) - 1),
           shift=st.sampled_from([0, 16, 32, 48]))
    def test_MOV_r_u16(self, r1, immed, shift):
        cb = CodeBuilder()
        cb.MOV_r_u16(r1.value, immed, shift)
        if shift == 0:
            assert cb.hexdump() == assemble("MOVK %r, %d" % (r1, immed))
        else:
            assert cb.hexdump() == assemble("MOVK %r, %d, lsl %d" % (r1, immed, shift))

