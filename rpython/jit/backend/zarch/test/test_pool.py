from rpython.jit.backend.zarch.pool import LiteralPool
from rpython.jit.metainterp.history import (AbstractFailDescr,
         AbstractDescr, BasicFailDescr, BasicFinalDescr, JitCellToken,
         TargetToken, ConstInt, ConstPtr, Const, ConstFloat)
from rpython.jit.metainterp.resoperation import (ResOperation, rop,
         InputArgInt)
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.jit.backend.zarch.helper.regalloc import check_imm32
import py

class TestPoolZARCH(object):
    def setup_class(self):
        self.calldescr = None

    def setup_method(self, name):
        self.pool = LiteralPool()
        self.asm = None

    def ensure_can_hold(self, opnum, args, descr=None):
        op = ResOperation(opnum, args, descr=descr)
        self.pool.ensure_can_hold_constants(self.asm, op)

    def const_in_pool(self, c):
        try:
            self.pool.get_offset(c)
        except KeyError:
            return False
        return True

    def test_constant_in_call_malloc(self):
        c = ConstPtr(rffi.cast(llmemory.GCREF, 0xdeadbeef))
        self.ensure_can_hold(rop.CALL_MALLOC_GC, [c], descr=self.calldescr)
        assert self.const_in_pool(c)
        assert self.const_in_pool(ConstPtr(rffi.cast(llmemory.GCREF, 0xdeadbeef)))

    @py.test.mark.parametrize('opnum',
            [rop.INT_ADD, rop.INT_SUB, rop.INT_MUL])
    def test_constants_arith(self, opnum):
        for c1 in [ConstInt(1), ConstInt(2**44), InputArgInt(1)]:
            for c2 in [InputArgInt(1), ConstInt(1), ConstInt(2**55)]:
                self.ensure_can_hold(opnum, [c1,c2])
                if c1.is_constant() and check_imm32(c1):
                    assert self.const_in_pool(c1)
                else:
                    assert not self.const_in_pool(c1)
                if c2.is_constant() and check_imm32(c2):
                    assert self.const_in_pool(c2)
                else:
                    assert not self.const_in_pool(c2)
