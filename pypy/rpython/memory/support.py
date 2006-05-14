from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.lltypelayout import sizeof

INT_SIZE = sizeof(lltype.Signed)

DEFAULT_CHUNK_SIZE = 1019

def get_address_linked_list(chunk_size=DEFAULT_CHUNK_SIZE):

    CHUNK = lltype.ForwardReference()
    CHUNK.become(lltype.Struct('AddressLinkedListChunk',
                               ('previous', lltype.Ptr(CHUNK)),
                               ('length', lltype.Signed),
                               ('items', lltype.FixedSizeArray(
                                   llmemory.Address, chunk_size))))
    null_chunk = lltype.nullptr(CHUNK)

    class FreeList(object):
        _alloc_flavor_ = "raw"

        def __init__(self):
            self.free_list = null_chunk

        def get(self):
            if not self.free_list:
                return lltype.malloc(CHUNK, flavor='raw')
            result = self.free_list
            self.free_list = result.previous
            return result

        def put(self, chunk):
            chunk.previous = self.free_list
            self.free_list = chunk

    unused_chunks = FreeList()

    class AddressLinkedList(object):
        _alloc_flavor_ = "raw"
        
        def __init__(self):
            self.chunk = unused_chunks.get()
            self.chunk.previous = null_chunk
            self.chunk.length = 0

        def append(self, addr):
            if addr == llmemory.NULL:
                return
            if self.chunk.length == chunk_size:
                new = unused_chunks.get()
                new.previous = self.chunk
                new.length = 0
                self.chunk = new
            used_chunks = self.chunk.length
            self.chunk.length += 1
            self.chunk.items[used_chunks] = addr
            
        def pop(self):
            used_chunks = self.chunk.length
            if used_chunks == 0:
                old = self.chunk
                previous = old.previous
                if not previous:
                    return llmemory.NULL
                self.chunk = previous
                unused_chunks.put(old)
                used_chunks = self.chunk.length
            result = self.chunk.items[used_chunks - 1]
            #self.chunk.items[used_chunks - 1] = llmemory.NULL
            self.chunk.length = used_chunks - 1
            return result

        def free(self):   # XXX very inefficient
            cur = self.chunk
            while cur.previous:
                prev = cur.previous
                unused_chunks.put(cur)
                cur = prev
            self.chunk = cur
            cur.length =  0

    return AddressLinkedList
