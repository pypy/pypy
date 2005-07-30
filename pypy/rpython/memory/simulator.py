import array

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
        self.freed = True
        self.memory = None
        self.status = None

    def getbytes(self, offset, size):
        assert offset >= 0
        if self.freed:
            raise MemorySimulatorError, "trying to access free memory"
        if offset + size >= self.size:
            raise MemorySimulatorError, "trying to access memory between blocks"
        if "u" in self.status[offset: offset+size]:
            raise MemorySimulatorError, "trying to access uninitialized memory"
        return self.memory[offset:offset+size].tostring()

    def setbytes(self, offset, value):
        assert offset >= 0
        if self.freed:
            raise MemorySimulatorError, "trying to access free memory"
        if offset + len(value) >= self.size:
            raise MemorySimulatorError, "trying to access memory between blocks"
        a = array.array("c")
        a.fromstring(value)
        s = array.array("c")
        s.fromstring("i" * len(value))
        self.memory[offset:offset + len(value)] = a
        self.status[offset:offset + len(value)] = s
