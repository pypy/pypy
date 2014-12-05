import py
from rpython.rlib import rthread
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop


class ThreadLocalTest(object):

    def test_threadlocalref_get(self):
        tlfield = rthread.ThreadLocalField(lltype.Signed, 'foobar_test_')

        def f():
            tlfield.setraw(0x544c)
            return tlfield.getraw()

        res = self.interp_operations(f, [])
        assert res == 0x544c


class TestLLtype(ThreadLocalTest, LLJitMixin):
    pass
