import py
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.aarch64 import assembler as aarch64_assembler
from rpython.jit.backend.aarch64.codebuilder import InstrBuilder
from rpython.jit.metainterp.history import BasicFailDescr, BasicFinalDescr
from rpython.jit.metainterp.history import JitCellToken, TargetToken
from rpython.jit.tool.oparser import parse
from rpython.jit.codewriter import longlong
from rpython.rtyper.lltypesystem import lltype, rffi


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
        f2 = float_mul(f1, 2.5)
        f3 = float_add(f2, -3.75)
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

        expected = (1.0 + 0.1) * 2.5 + (-3.75)
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
