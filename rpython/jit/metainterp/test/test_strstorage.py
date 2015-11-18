import py
from rpython.rlib.strstorage import str_storage_getitem
from rpython.rlib.test.test_strstorage import BaseStrStorageTest
from rpython.jit.metainterp.test.support import LLJitMixin

class TestStrStorage(BaseStrStorageTest, LLJitMixin):

    # for the individual tests see
    # ====> ../../../rlib/test/test_strstorage.py

    def str_storage_getitem(self, TYPE, buf, offset):
        def f():
            return str_storage_getitem(TYPE, buf, offset)
        res = self.interp_operations(f, [])
        self.check_operations_history({'getarrayitem_gc_i': 1,
                                       'finish': 1})
        return res
