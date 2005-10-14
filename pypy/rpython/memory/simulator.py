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

    def memcopy(self, offset1, other, offset2, size):
        if offset1 + size > self.size:
            raise MemorySimulatorError, "trying to access memory between blocks"
        if offset2 + size > other.size:
            raise MemorySimulatorError, "trying to access memory between blocks"
        other.memory[offset2:offset2+size] = self.memory[offset1:offset1+size]
        other.status[offset2:offset2+size] = self.status[offset1:offset1+size]


# block which stores functions and PyObects
class ObjectBlock(object):
    def __init__(self, baseaddress, size):
        self.baseaddress = baseaddress
        self.size = size
        self.objects_to_num = {}
        self.objects = []
        
    def get_py_object(self, offset):
        try:
            return self.objects[offset]
        except IndexError:
            raise MemorySimulatorError, "trying to access unknown object"

    def get_address_of_object(self, obj):
        if obj in self.objects_to_num:
            return self.objects_to_num[obj]
        else:
            assert len(self.objects) <= self.size
            index = len(self.objects)
            self.objects_to_num[obj] = index
            self.objects.append(obj)
            return index


SIZE_OF_OBJECT_BLOCK = 2 ** 16 # arbitraly choosen size

class MemorySimulator(object):
    size_of_simulated_ram = 64 * 1024 * 1024
    def __init__(self, ram_size = None):
        self.objectblock = ObjectBlock(4, SIZE_OF_OBJECT_BLOCK)
        self.blocks = [ObjectBlock(4, SIZE_OF_OBJECT_BLOCK)]
        self.freememoryaddress = 4 + SIZE_OF_OBJECT_BLOCK
        if ram_size is not None:
            self.size_of_simulated_ram = ram_size
        self.current_size = 0

    def find_block(self, address):
        if address >= self.freememoryaddress:
            raise MemorySimulatorError, "trying to access memory not malloc'ed"
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
        if size == 0:
            size = 1
        result = self.freememoryaddress
        self.blocks.append(MemoryBlock(result, size))
        self.freememoryaddress += size
        self.current_size += size
        if self.current_size + size > self.size_of_simulated_ram:
            raise MemorySimulatorError, "out of memory"
        return result

    def free(self, baseaddress):
        if baseaddress == 0:
            raise MemorySimulatorError, "trying to free NULL address"
        block = self.find_block(baseaddress)
        if baseaddress != block.baseaddress:
            raise MemorySimulatorError, "trying to free address not malloc'ed"
        self.current_size -= block.size
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
        block1 = self.find_block(address1)
        block2 = self.find_block(address2)
        offset1 = address1 - block1.baseaddress
        offset2 = address2 - block2.baseaddress
        block1.memcopy(offset1, block2, offset2, size)

    def get_py_object(self, address):
        block = self.objectblock
        offset = address - block.baseaddress
        assert isinstance(block, ObjectBlock)
        return block.get_py_object(offset)

    def get_address_of_object(self, obj):
        return (self.objectblock.get_address_of_object(obj) +
                self.objectblock.baseaddress)
