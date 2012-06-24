
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rawstorage import alloc_raw_storage, free_raw_storage,\
     raw_storage_setitem
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin

def raw_storage_getitem(storage, index, TP):
    return rffi.cast(rffi.CArrayPtr(TP), rffi.ptradd(storage, index))[0]

def test_untranslated_storage():
    r = alloc_raw_storage(15)
    raw_storage_setitem(r, 3, 1<<30)
    res = raw_storage_getitem(r, 3, lltype.Signed)
    free_raw_storage(r)
    assert res == 1<<30

class TestRawStorage(BaseRtypingTest, LLRtypeMixin):
    def test_storage_int(self):
        def f(i):
            r = alloc_raw_storage(24)
            raw_storage_setitem(r, 3, i)
            return r
        ll_r = self.interpret(f, [1<<30], malloc_check=False)
        assert raw_storage_getitem(ll_r, 3, lltype.Signed) == 1 << 30
        free_raw_storage(ll_r)
