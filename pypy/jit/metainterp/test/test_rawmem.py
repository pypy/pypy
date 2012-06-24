from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rawstorage import (alloc_raw_storage, raw_storage_setitem,
                                  free_raw_storage)

class TestJITRawMem(LLJitMixin):
    def test_cast_void_ptr(self):
        TP = lltype.Array(lltype.Float, hints={"nolength": True})
        VOID_TP = lltype.Array(lltype.Void, hints={"nolength": True, "uncast_on_llgraph": True})
        class A(object):
            def __init__(self, x):
                self.storage = rffi.cast(lltype.Ptr(VOID_TP), x)

        def f(n):
            x = lltype.malloc(TP, n, flavor="raw", zero=True)
            a = A(x)
            s = 0.0
            rffi.cast(lltype.Ptr(TP), a.storage)[0] = 1.0
            s += rffi.cast(lltype.Ptr(TP), a.storage)[0]
            lltype.free(x, flavor="raw")
            return s
        self.interp_operations(f, [10])

    def test_fixed_size_malloc(self):
        TIMEVAL = lltype.Struct('dummy', ('tv_sec', rffi.LONG), ('tv_usec', rffi.LONG))
        def f():
            p = lltype.malloc(TIMEVAL, flavor='raw')
            lltype.free(p, flavor='raw')
            return 42
        res = self.interp_operations(f, [])
        assert res == 42
        self.check_operations_history({'call': 2, 'guard_no_exception': 1,
                                       'finish': 1})

    def test_raw_storage(self):
        def f():
            p = alloc_raw_storage(15)
            raw_storage_setitem(p, 3, 24)
            free_raw_storage(p)
            return 42
        res = self.interp_operations(f, [])
        assert res == 42
        self.check_operations_history({'call': 2, 'guard_no_exception': 1,
                                       'finish': 1})
