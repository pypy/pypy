import array
import struct

# all addresses in the simulator are just ints

# possible chars in status are:
# 'u': uninitialized
# 'i': initialized

class MemorySimulatorError(Exception):
    pass

class MemoryBlock(object):
    def __init__(self, baseaddress, size):
        self.baseaddress = baseaddress
        self.size = size
        self.memory = array.array("c", "\x00" * size)
        self.status = array.array("c", "u" * size)
        self.freed = False

    def free(self):
        if self.freed:
            raise MemorySimulatorError, "trying to free already freed memory"
        self.freed = True
        self.memory = None
        self.status = None

    def getbytes(self, offset, size):
        assert offset >= 0
        if self.freed:
            raise MemorySimulatorError, "trying to access free memory"
        if offset + size > self.size:
            raise MemorySimulatorError, "trying to access memory between blocks"
        if "u" in self.status[offset: offset+size]:
            raise MemorySimulatorError, "trying to access uninitialized memory"
        return self.memory[offset:offset+size].tostring()

    def setbytes(self, offset, value):
        assert offset >= 0
        if self.freed:
            raise MemorySimulatorError, "trying to access free memory"
        if offset + len(value) > self.size:
            raise MemorySimulatorError, "trying to access memory between blocks"
        a = array.array("c")
        a.fromstring(value)
        s = array.array("c")
        s.fromstring("i" * len(value))
        self.memory[offset:offset + len(value)] = a
        self.status[offset:offset + len(value)] = s
        assert len(self.memory) == self.size

class MemorySimulator(object):
    def __init__(self):
        self.blocks = []
        self.freememoryaddress = 4

    def find_block(self, address):
        lo = 0
        hi = len(self.blocks)
        while lo < hi:
            mid = (lo + hi) // 2
            block = self.blocks[mid]
            if address < block.baseaddress:
                hi = mid
            elif address < block.baseaddress + block.size:
                return block
            else:
                lo = mid
        return self.blocks[mid]

    def malloc(self, size):
        result = self.freememoryaddress
        self.blocks.append(MemoryBlock(result, size))
        self.freememoryaddress += size
        return result

    def free(self, baseaddress):
        if baseaddress == 0:
            raise MemorySimulatorError, "trying to free NULL address"
        block = self.find_block(baseaddress)
        if baseaddress != block.baseaddress:
            raise MemorySimulatorError, "trying to free address not malloc'ed"
        block.free()

    def getstruct(self, fmt, address):
        block = self.find_block(address)
        offset = address - block.baseaddress
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, block.getbytes(offset, size))

    def setstruct(self, fmt, address, *types):
        block = self.find_block(address)
        offset = address - block.baseaddress
        block.setbytes(offset, struct.pack(fmt, *types))

    def memcopy(self, address1, address2, size):
        data = self.getstruct("c" * size, address1)
        self.setstruct("c" * size, address2, *data)
