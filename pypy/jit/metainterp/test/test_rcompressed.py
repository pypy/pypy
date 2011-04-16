import py
from pypy.config.translationoption import IS_64_BITS
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib import jit


class TestRCompressed(LLJitMixin):

    def setup_class(cls):
        if not IS_64_BITS:
            py.test.skip("only for 64-bits")

    def test_simple(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        SPTR = lltype.Ptr(S)
        def f(n):
            y = lltype.malloc(S)
            y.n = n
            p = llop.hide_into_ptr32(llmemory.HiddenGcRef32, y)
            z = llop.show_from_ptr32(SPTR, p)
            return z.n
        res = self.interp_operations(f, [42])
        assert res == 42

    def test_store_load(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('p', llmemory.HiddenGcRef32),
                                 ('c', lltype.Char))
        SPTR = lltype.Ptr(S)
        @jit.dont_look_inside
        def escape(ptr):
            assert llop.show_from_ptr32(SPTR, ptr.p).n == 42
            return ptr
        def f(n):
            y = lltype.malloc(S)
            y.n = n
            t = lltype.malloc(T)
            t.c = '?'
            t.p = llop.hide_into_ptr32(llmemory.HiddenGcRef32, y)
            t = escape(t)
            z = llop.show_from_ptr32(SPTR, t.p)
            return z.n * 1000 + ord(t.c)
        res = self.interp_operations(f, [42])
        assert res == 42063

    def test_call_argument(self):
        # the issue here is that even if we wrote this test, for now, it's
        # not going to really test the interesting parts, which are in
        # GcLLDescr_framework.rewrite_assembler
        py.test.skip("write me")

    def test_call_result(self):
        py.test.skip("write me")
