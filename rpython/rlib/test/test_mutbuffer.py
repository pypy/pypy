import pytest
from rpython.rlib.mutbuffer import MutableStringBuffer

class TestMutableStringBuffer(object):

    def test_finish(self):
        buf = MutableStringBuffer(4)
        pytest.raises(ValueError, "buf.as_str()")
        s = buf.finish()
        assert s == '\x00' * 4
        pytest.raises(ValueError, "buf.finish()")

    def test_setitem(self):
        buf = MutableStringBuffer(4)
        buf.setitem(0, 'A')
        buf.setitem(1, 'B')
        buf.setitem(2, 'C')
        buf.setitem(3, 'D')
        assert buf.finish() == 'ABCD'

    def test_setslice(self):
        buf = MutableStringBuffer(6)
        buf.setslice(2, 'ABCD')
        assert buf.finish() == '\x00\x00ABCD'
