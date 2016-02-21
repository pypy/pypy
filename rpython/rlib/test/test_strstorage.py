import py
import sys
import struct
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.strstorage import str_storage_getitem, str_storage_supported
from rpython.rlib.rarithmetic import r_singlefloat
from rpython.rtyper.test.tool import BaseRtypingTest

IS_32BIT = (sys.maxint == 2147483647)

class BaseStrStorageTest:

    def test_str_getitem_supported(self):
        if IS_32BIT:
            expected = False
        else:
            expected = True
        #
        assert self.str_storage_supported(rffi.LONGLONG) == expected
        assert self.str_storage_supported(rffi.DOUBLE) == expected

    def test_signed(self):
        buf = struct.pack('@ll', 42, 43)
        size = struct.calcsize('@l')
        assert self.str_storage_getitem(lltype.Signed, buf, 0) == 42
        assert self.str_storage_getitem(lltype.Signed, buf, size) == 43

    def test_short(self):
        buf = struct.pack('@hh', 42, 43)
        size = struct.calcsize('@h')
        x = self.str_storage_getitem(rffi.SHORT, buf, 0)
        assert int(x) == 42
        x = self.str_storage_getitem(rffi.SHORT, buf, size)
        assert int(x) == 43

    def test_float(self):
        if not str_storage_supported(lltype.Float):
            py.test.skip('str_storage_getitem(lltype.Float) not supported on this machine')
        buf = struct.pack('@dd', 12.3, 45.6)
        size = struct.calcsize('@d')
        assert self.str_storage_getitem(lltype.Float, buf, 0) == 12.3
        assert self.str_storage_getitem(lltype.Float, buf, size) == 45.6

    def test_singlefloat(self):
        buf = struct.pack('@ff', 12.3, 45.6)
        size = struct.calcsize('@f')
        x = self.str_storage_getitem(lltype.SingleFloat, buf, 0)
        assert x == r_singlefloat(12.3)
        x = self.str_storage_getitem(lltype.SingleFloat, buf, size)
        assert x == r_singlefloat(45.6)


class TestDirect(BaseStrStorageTest):

    def str_storage_supported(self, TYPE):
        return str_storage_supported(TYPE)

    def str_storage_getitem(self, TYPE, buf, offset):
        return str_storage_getitem(TYPE, buf, offset)

class TestRTyping(BaseStrStorageTest, BaseRtypingTest):

    def str_storage_supported(self, TYPE):
        def fn():
            return str_storage_supported(TYPE)
        return self.interpret(fn, [])

    def str_storage_getitem(self, TYPE, buf, offset):
        def fn(offset):
            return str_storage_getitem(TYPE, buf, offset)
        return self.interpret(fn, [offset])
