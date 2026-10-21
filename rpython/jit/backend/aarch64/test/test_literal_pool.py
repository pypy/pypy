import math
import py
import struct
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.aarch64 import assembler as aarch64_assembler
from rpython.jit.backend.aarch64.codebuilder import InstrBuilder, encode_fmov_imm8
from rpython.jit.metainterp.history import BasicFailDescr, BasicFinalDescr
from rpython.jit.metainterp.history import JitCellToken, TargetToken
from rpython.jit.tool.oparser import parse
from rpython.jit.codewriter import longlong
from rpython.rtyper.lltypesystem import lltype, rffi


def _float_bits(value):
    return struct.unpack('<q', struct.pack('<d', value))[0]


class _WordMC(InstrBuilder):
    def __init__(self):
        self._chars = []

    def writechar(self, char):
        self._chars.append(char)


def _emitted_word(method, *args):
    mc = _WordMC()
    getattr(mc, method)(*args)
    assert len(mc._chars) == 4
    return (ord(mc._chars[0]) | (ord(mc._chars[1]) << 8) |
            (ord(mc._chars[2]) << 16) | (ord(mc._chars[3]) << 24))


CPU = getcpuclass()


class FakeStats(object):
    pass


class TestLiteralPool(object):
    def setup_method(self, _):
        self.cpu = CPU(rtyper=None, stats=FakeStats())
        self.cpu.setup_once()

    def _float_result(self, deadframe, index=0):
        return longlong.getrealfloat(self.cpu.get_float_value(deadframe, index))

    def test_float_constants(self):
        faildescr = BasicFinalDescr(1)
        loop = parse("""
        [f0]
        f1 = float_add(f0, 0.1)
        f2 = float_mul(f1, 2.5)
        f3 = float_add(f2, -3.75)
        finish(f3, descr=faildescr)
        """, namespace={'faildescr': faildescr})
        looptoken = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        deadframe = self.cpu.execute_token(looptoken,
                                           longlong.getfloatstorage(1.0))
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail is faildescr
        expected = (1.0 + 0.1) * 2.5 + (-3.75)
        assert self._float_result(deadframe) == expected

    def test_mid_trace_flush_and_guard_failure(self):
        orig_distance = aarch64_assembler.LITERAL_POOL_FLUSH_DISTANCE
        orig_flush = aarch64_assembler.AssemblerARM64._flush_literal_pool
        nflush = [0]

        def counting_flush(self):
            if self.pending_literals:
                nflush[0] += 1
            return orig_flush(self)

        faildescr = BasicFailDescr(1)
        finaldescr = BasicFinalDescr(2)
        loop = parse("""
        [f0, i0]
        f1 = float_add(f0, 0.1)
        f2 = float_mul(f1, 32.0)
        f3 = float_add(f2, 0.0625)
        i1 = int_eq(i0, 1)
        guard_true(i1, descr=faildescr) [f3]
        finish(f3, descr=finaldescr)
        """, namespace={'faildescr': faildescr, 'finaldescr': finaldescr})
        looptoken = JitCellToken()
        try:
            aarch64_assembler.LITERAL_POOL_FLUSH_DISTANCE = 0
            aarch64_assembler.AssemblerARM64._flush_literal_pool = counting_flush
            self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        finally:
            aarch64_assembler.LITERAL_POOL_FLUSH_DISTANCE = orig_distance
            aarch64_assembler.AssemblerARM64._flush_literal_pool = orig_flush

        assert nflush[0] >= 2

        expected = (1.0 + 0.1) * 32.0 + 0.0625
        deadframe = self.cpu.execute_token(looptoken,
                                           longlong.getfloatstorage(1.0), 1)
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail is finaldescr
        assert self._float_result(deadframe) == expected

        deadframe = self.cpu.execute_token(looptoken,
                                           longlong.getfloatstorage(1.0), 0)
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail is faildescr
        assert self._float_result(deadframe) == expected

    def test_bridge_with_float_constant(self):
        faildescr = BasicFailDescr(1)
        finaldescr = BasicFinalDescr(2)
        bridgedescr = BasicFinalDescr(3)
        targettoken = TargetToken()
        loop = parse("""
        [f0]
        label(f0, descr=targettoken)
        f1 = float_add(f0, 0.1)
        i0 = float_ge(f1, 0.0)
        guard_true(i0, descr=faildescr) [f1]
        finish(f1, descr=finaldescr)
        """, namespace=locals())
        looptoken = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)

        bridge = parse("""
        [f1]
        f2 = float_mul(f1, 2.5)
        finish(f2, descr=bridgedescr)
        """, namespace=locals())
        self.cpu.compile_bridge(faildescr, bridge.inputargs,
                                bridge.operations, looptoken)

        deadframe = self.cpu.execute_token(looptoken,
                                           longlong.getfloatstorage(-1.0))
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail is bridgedescr
        expected = (-1.0 + 0.1) * 2.5
        assert self._float_result(deadframe) == expected

    def test_flush_raises_when_entry_too_far(self):
        asm = self.cpu.assembler
        asm.mc = InstrBuilder()
        buf = lltype.malloc(rffi.CArray(lltype.Char), 8, flavor='raw')
        addr = rffi.cast(lltype.Signed, buf)
        try:
            pos = asm.mc.currpos()
            asm.mc.LDR_d_literal(0, 0)
            asm.pending_literals = [(pos, 0, addr)]
            extra = (1 << 20) + 8
            for i in range(extra):
                asm.mc.writechar('\x00')
            py.test.raises(AssertionError, asm._flush_literal_pool)
        finally:
            lltype.free(buf, flavor='raw')

    def test_fmov_imm8_helper_and_encoders(self):
        cases = [
            (1.0, 0x70, 2, 0x1e6e1002),
            (2.5, 0x04, 2, 0x1e609002),
            (-0.125, 0xc0, 7, 0x1e781007),
            (31.0, 0x3f, 0, 0x1e67f000),
            (0.5, 0x60, 31, 0x1e6c101f),
            (-10.0, 0xa4, 3, 0x1e749003),
        ]
        for value, imm8, rd, word in cases:
            assert encode_fmov_imm8(_float_bits(value)) == imm8
            assert _emitted_word('FMOV_di', rd, imm8) == word
        assert _emitted_word('MOVI_d_zero', 2) == 0x2f00e402

    def test_fmov_imm8_not_encodable(self):
        assert encode_fmov_imm8(_float_bits(0.0)) == -1
        for value in (-0.0, 0.1, 32.0, 0.0625, 1.1, float('inf'), float('nan')):
            assert encode_fmov_imm8(_float_bits(value)) == -1

    def test_float_immediate_constants_skip_literal_pool(self):
        orig_load = aarch64_assembler.AssemblerARM64.load
        pooled = []

        def wrapping_load(self, loc, value):
            n = len(self.pending_literals)
            orig_load(self, loc, value)
            if len(self.pending_literals) > n:
                addr = self.pending_literals[-1][2]
                pooled.append(rffi.cast(rffi.CArrayPtr(lltype.Signed), addr)[0])

        faildescr = BasicFailDescr(1)
        finaldescr = BasicFinalDescr(2)
        loop = parse("""
        [f0, i0]
        f1 = float_add(f0, 0.0)
        f2 = float_add(f1, 1.0)
        f3 = float_mul(f2, 2.5)
        f4 = float_add(f3, -0.125)
        f5 = float_add(f4, 31.0)
        f6 = float_add(f5, 0.1)
        f7 = float_add(f6, 32.0)
        fz = float_mul(f0, 0.0)
        fnz = float_mul(f0, -0.0)
        i1 = int_eq(i0, 1)
        guard_true(i1, descr=faildescr) [fz, fnz]
        finish(f7, descr=finaldescr)
        """, namespace={'faildescr': faildescr, 'finaldescr': finaldescr})
        looptoken = JitCellToken()
        try:
            aarch64_assembler.AssemblerARM64.load = wrapping_load
            self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        finally:
            aarch64_assembler.AssemblerARM64.load = orig_load

        deadframe = self.cpu.execute_token(looptoken,
                                           longlong.getfloatstorage(1.0), 1)
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail is finaldescr
        expected = (((((1.0 + 0.0) + 1.0) * 2.5) + (-0.125)) + 31.0) + 0.1 + 32.0
        assert self._float_result(deadframe, 0) == expected

        deadframe = self.cpu.execute_token(looptoken,
                                           longlong.getfloatstorage(1.0), 0)
        fail = self.cpu.get_latest_descr(deadframe)
        assert fail is faildescr
        assert self._float_result(deadframe, 0) == 0.0
        assert math.copysign(1.0, self._float_result(deadframe, 0)) == 1.0
        assert self._float_result(deadframe, 1) == 0.0
        assert math.copysign(1.0, self._float_result(deadframe, 1)) == -1.0
        assert set(pooled) == set([_float_bits(-0.0), _float_bits(0.1),
                                   _float_bits(32.0)])

