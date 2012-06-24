
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rawstorage import alloc_raw_storage, free_raw_storage,\
     raw_storage_setitem, raw_storage_getitem
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin

def test_untranslated_storage():
    r = alloc_raw_storage(15)
    raw_storage_setitem(r, 3, 1<<30)
    res = raw_storage_getitem(lltype.Signed, r, 3)
    free_raw_storage(r)
    assert res == 1<<30

class TestRawStorage(BaseRtypingTest, LLRtypeMixin):
    def test_storage_int(self):
        def f(i):
            r = alloc_raw_storage(24)
            raw_storage_setitem(r, 3, i)
            res = raw_storage_getitem(lltype.Signed, r, 3)
            free_raw_storage(r)
            return res
        x = self.interpret(f, [1<<30])
        assert x == 1 << 30
