from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rpython.lltypesystem import lltype, rffi


class TestJITRawMem(LLJitMixin):
    def test_cast_void_ptr(self):
        TP = lltype.Array(lltype.Float, hints={"nolength": True})
        VOID_TP = lltype.Array(lltype.Void, hints={"nolength": True})
        class A(object):
            def __init__(self, x):
                self.storage = rffi.cast(lltype.Ptr(VOID_TP), x)\

        def f(n):
            x = lltype.malloc(TP, n, flavor="raw", zero=True)
            a = A(x)
            s = 0.0
            rffi.cast(lltype.Ptr(TP), a.storage)[0] = 1.0
            s += rffi.cast(lltype.Ptr(TP), a.storage)[0]
            lltype.free(x, flavor="raw")
            return s
        res = self.interp_operations(f, [10])
        assert res == 1.0