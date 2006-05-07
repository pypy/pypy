from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.memory.lltypelayout import sizeof
import struct

INT_SIZE = sizeof(lltype.Signed)

CHUNK_SIZE = 1022

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

def get_address_linked_list(chunk_size=CHUNK_SIZE):
    unused_chunks = FreeList(chunk_size + 2)
    class AddressLinkedList(object):
        _alloc_flavor_ = "raw"
        
        def __init__(self):
            self.chunk = unused_chunks.get()
            self.chunk.address[0] = NULL
            self.chunk.signed[1] = 0

        def append(self, addr):
            if addr == NULL:
                return
            if self.chunk.signed[1] == chunk_size:
                new = unused_chunks.get()
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
                unused_chunks.put(old)
                used_chunks = self.chunk.signed[1]
            result = self.chunk.address[used_chunks + 1]
            self.chunk.address[used_chunks + 1] = NULL
            self.chunk.signed[1] = used_chunks - 1
            return result

        def free(self):   # XXX very inefficient
            while self.pop() != NULL:
                pass
    return AddressLinkedList
