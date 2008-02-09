
import py
from pypy.rlib.rbuffer import RBuffer

class TestRbuffer:
    def test_creation(self):
        buf = RBuffer(3)
        assert buf.address()
        buf.free()

    def test_getsetitem(self):
        buf = RBuffer(10)
        assert buf.getitem(3) == '\x00'
        buf.setitem(4, '\x01')
        assert buf.getitem(4) == '\x01'
        buf.free()

    def test_fromaddress(self):
        buf = RBuffer(10)
        buf.setitem(2, '\x03')
        buf2 = RBuffer(7, buf.address() + 2)
        assert buf2.getitem(0) == '\x03'
        buf.free()

    def test_getslice(self):
        buf = RBuffer(10)
        buf.setitem(0, '\x01')
        buf.setitem(1, '\x02')
        buf.setitem(2, '\x03')
        assert buf.getslice(0, 3) == '\x01\x02\x03'
        buf.free()
