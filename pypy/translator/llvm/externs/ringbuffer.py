from pypy.rpython.memory import lladdress
from pypy.rpython.lltypesystem import lltype, llmemory

# Cant store in class
size = 8192
entry_maxsize = 16
ringbufdata = lltype.malloc(lltype.GcArray(llmemory.Address), 1)
ringbufindex = lltype.malloc(lltype.GcArray(lltype.Signed), 1)

def ringbuffer_initialise():
    ringbufdata[0] = lladdress.raw_malloc(size + entry_maxsize)

def ringbuffer_malloc(nbytes):
    assert nbytes <= entry_maxsize
    addr = ringbufdata[0] + ringbufindex[0]
    ringbufindex[0] = (ringbufindex[0] + nbytes) & (size - 1)
    return addr

# XXX would be nice to support something like this
# ringbufindex = lltype.malloc(lltype.GcArray(lltype.Char), size + entry_maxsize)

# def ringbuffer_initialise():
#     pass

# def ringbuffer_malloc(nbytes):
#     assert nbytes <= entry_maxsize
#     addr = lladdress.get_address_of_object(ringbufdata[ringbufindex[0]])
#     ringbufindex[0] = (ringbufindex[0] + nbytes) & (size - 1)
#     return addr
