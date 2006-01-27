from pypy.rpython.memory.lladdress import raw_malloc

class RingBufferData:
    size          = 8192
    entry_maxsize = 16

    def __init__(self):
        self.index = 0
    def init(self):
        self.data = raw_malloc(self.size + self.entry_maxsize)

ringbuffer = RingBufferData()

def initialise():
    ringbuffer.init()

def malloc_exception(nbytes):
    assert nbytes <= ringbuffer.entry_maxsize
    addr = ringbuffer.data + ringbuffer.index
    ringbuffer.index = (ringbuffer.index + nbytes) & (ringbuffer.size - 1)
    return addr

