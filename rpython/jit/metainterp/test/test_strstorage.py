import py
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.strstorage import str_storage_getitem
from rpython.rlib.test.test_strstorage import BaseStrStorageTest
from rpython.jit.codewriter import longlong
from rpython.jit.metainterp.history import getkind
from rpython.jit.metainterp.test.support import LLJitMixin

class TestStrStorage(BaseStrStorageTest, LLJitMixin):

    # for the individual tests see
    # ====> ../../../rlib/test/test_strstorage.py

    def str_storage_getitem(self, TYPE, buf, offset):
        def f():
            return str_storage_getitem(TYPE, buf, offset)
        res = self.interp_operations(f, [], supports_singlefloats=True)
        #
        kind = getkind(TYPE)[0] # 'i' or 'f'
        self.check_operations_history({'getarrayitem_gc_%s' % kind: 1,
                                       'finish': 1})
        #
        if TYPE == lltype.SingleFloat:
            # interp_operations returns the int version of r_singlefloat, but
            # our tests expects to receive an r_singlefloat: let's convert it
            # back!
            return longlong.int2singlefloat(res)
        return res
