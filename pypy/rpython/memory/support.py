from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.memory.lltypelayout import sizeof
import struct

INT_SIZE = sizeof(lltype.Signed)

CHUNK_SIZE = 30

class FreeList(object):
    _alloc_flavor_ = "raw"

    def __init__(self, size):
        self.free_list = NULL
        self.size = size

    def get(self):
        if self.free_list == NULL:
            return raw_malloc(self.size * INT_SIZE)
        result = self.free_list
        self.free_list = result.address[0]
        return result

    def put(self, chunk):
        chunk.address[0] = self.free_list
        self.free_list = chunk

class AddressLinkedList(object):
    _alloc_flavor_ = "raw"
    
    unused_chunks = FreeList(CHUNK_SIZE + 2)
    
    def __init__(self):
        self.chunk = NULL

    def append(self, addr):
        if addr == NULL:
            return
        if self.chunk == NULL or self.chunk.signed[1] == CHUNK_SIZE:
            new = AddressLinkedList.unused_chunks.get()
            new.address[0] = self.chunk
            new.signed[1] = 0
            self.chunk = new
        used_chunks = self.chunk.signed[1]
        self.chunk.signed[1] += 1
        self.chunk.address[used_chunks + 2] = addr
        
    def pop(self):
        used_chunks = self.chunk.signed[1]
        if used_chunks == 0:
            old = self.chunk
            previous = old.address[0]
            if previous == NULL:
                return NULL
            self.chunk = previous
            AddressLinkedList.unused_chunks.put(old)
            used_chunks = self.chunk.signed[1]
        result = self.chunk.address[used_chunks + 1]
        self.chunk.address[used_chunks + 1] = NULL
        self.chunk.signed[1] = used_chunks - 1
        return result

    def free(self):
        while self.pop() != NULL:
            pass
