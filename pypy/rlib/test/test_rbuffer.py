
import py
from pypy.rlib.rbuffer import RBuffer

class TestRbuffer:
    def test_creation(self):
        buf = RBuffer(3)
        assert buf.address()
        buf.free()
    
