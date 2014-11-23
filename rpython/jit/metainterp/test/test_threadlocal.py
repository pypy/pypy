import py
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rtyper.lltypesystem import llmemory
from rpython.rtyper.lltypesystem.lloperation import llop


class ThreadLocalTest(object):

    def test_threadlocalref_get(self):
        def f():
            addr1 = llop.threadlocalref_addr(llmemory.Address)
            # a "does not crash" test only
            return 1

        res = self.interp_operations(f, [])
        assert res == 1


class TestLLtype(ThreadLocalTest, LLJitMixin):
    pass
