import py
from pypy.rpython.memory.simulator import MemoryBlock

class TestMemoryBlock(object):
    def test_getsetbyte(self):
        block = MemoryBlock(1, 1000)
        block.setbytes(1, "hello")
        assert block.getbytes(1, 5) == "hello"
        
        
