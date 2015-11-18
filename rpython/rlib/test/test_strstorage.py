import py
import struct
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.strstorage import str_storage_getitem
from rpython.rtyper.test.tool import BaseRtypingTest

class BaseStrStorageTest:

    def test_signed(self):
        buf = struct.pack('@ll', 42, 43)
        size = struct.calcsize('@l')
        assert self.str_storage_getitem(lltype.Signed, buf, 0) == 42
        assert self.str_storage_getitem(lltype.Signed, buf, size) == 43

    def test_float(self):
        buf = struct.pack('@dd', 12.3, 45.6)
        size = struct.calcsize('@d')
        assert self.str_storage_getitem(lltype.Float, buf, 0) == 12.3
        assert self.str_storage_getitem(lltype.Float, buf, size) == 45.6


class TestDirect(BaseStrStorageTest):

    def str_storage_getitem(self, TYPE, buf, offset):
        return str_storage_getitem(TYPE, buf, offset)


class TestRTyping(BaseStrStorageTest, BaseRtypingTest):

    def str_storage_getitem(self, TYPE, buf, offset):
        def fn(offset):
            return str_storage_getitem(TYPE, buf, offset)
        return self.interpret(fn, [offset])
