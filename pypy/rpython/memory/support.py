from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import free_non_gc_object

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
                return lltype.malloc(CHUNK, flavor="raw")
                
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

        def enlarge(self):
            new = unused_chunks.get()
            new.previous = self.chunk
            new.length = 0
            self.chunk = new
            return new
        enlarge._dont_inline_ = True

        def shrink(self):
            old = self.chunk
            self.chunk = old.previous
            unused_chunks.put(old)
            return self.chunk
        shrink._dont_inline_ = True

        def append(self, addr):
            if addr == llmemory.NULL:
                return
            chunk = self.chunk
            if chunk.length == chunk_size:
                chunk = self.enlarge()
            used_chunks = chunk.length
            chunk.length = used_chunks + 1
            chunk.items[used_chunks] = addr

        def non_empty(self):
            chunk = self.chunk
            return chunk.length != 0 or bool(chunk.previous)

        def pop(self):
            chunk = self.chunk
            if chunk.length == 0:
                chunk = self.shrink()
            used_chunks = self.chunk.length - 1
            result = chunk.items[used_chunks]
            chunk.length = used_chunks
            return result

        def delete(self):
            cur = self.chunk
            while cur:
                prev = cur.previous
                unused_chunks.put(cur)
                cur = prev
            free_non_gc_object(self)

    return AddressLinkedList
