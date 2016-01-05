from rpython.jit.backend.zarch.pool import LiteralPool
from rpython.jit.metainterp.history import (AbstractFailDescr,
         AbstractDescr, BasicFailDescr, BasicFinalDescr, JitCellToken,
         TargetToken, ConstInt, ConstPtr, Const, ConstFloat)
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
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
