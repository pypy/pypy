from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import free_non_gc_object, we_are_translated
from pypy.rlib.debug import ll_assert

DEFAULT_CHUNK_SIZE = 1019


def get_chunk_manager(chunk_size=DEFAULT_CHUNK_SIZE, cache={}):
    try:
        return cache[chunk_size]
    except KeyError:
        pass

    CHUNK = lltype.ForwardReference()
    CHUNK.become(lltype.Struct('AddressChunk',
                               ('next', lltype.Ptr(CHUNK)),
                               ('items', lltype.FixedSizeArray(
                                   llmemory.Address, chunk_size))))
    null_chunk = lltype.nullptr(CHUNK)

    class FreeList(object):
        _alloc_flavor_ = "raw"

        def __init__(self):
            self.free_list = null_chunk

        def get(self):
            if not self.free_list:
                # we zero-initialize the chunks to make the translation
                # backends happy, but we don't need to do it at run-time.
                zero = not we_are_translated()
                return lltype.malloc(CHUNK, flavor="raw", zero=zero)
                
            result = self.free_list
            self.free_list = result.next
            return result

        def put(self, chunk):
            if we_are_translated():
                chunk.next = self.free_list
                self.free_list = chunk
            else:
                # Don't cache the old chunks but free them immediately.
                # Helps debugging, and avoids that old chunks full of
                # addresses left behind by a test end up in genc...
                lltype.free(chunk, flavor="raw")

    unused_chunks = FreeList()
    cache[chunk_size] = unused_chunks, null_chunk
    return unused_chunks, null_chunk


def get_address_stack(chunk_size=DEFAULT_CHUNK_SIZE, cache={}):
    try:
        return cache[chunk_size]
    except KeyError:
        pass

    unused_chunks, null_chunk = get_chunk_manager(chunk_size)

    class AddressStack(object):
        _alloc_flavor_ = "raw"
        
        def __init__(self):
            self.chunk = unused_chunks.get()
            self.chunk.next = null_chunk
            self.used_in_last_chunk = 0
            # invariant: self.used_in_last_chunk == 0 if and only if
            # the AddressStack is empty

        def enlarge(self):
            new = unused_chunks.get()
            new.next = self.chunk
            self.chunk = new
            self.used_in_last_chunk = 0
        enlarge._dont_inline_ = True

        def shrink(self):
            old = self.chunk
            self.chunk = old.next
            unused_chunks.put(old)
            self.used_in_last_chunk = chunk_size
        shrink._dont_inline_ = True

        def append(self, addr):
            used = self.used_in_last_chunk
            if used == chunk_size:
                self.enlarge()
                used = 0
            self.chunk.items[used] = addr
            self.used_in_last_chunk = used + 1      # always > 0 here

        def non_empty(self):
            return self.used_in_last_chunk != 0

        def pop(self):
            used = self.used_in_last_chunk - 1
            ll_assert(used >= 0, "pop on empty AddressStack")
            result = self.chunk.items[used]
            self.used_in_last_chunk = used
            if used == 0 and self.chunk.next:
                self.shrink()
            return result

        def delete(self):
            cur = self.chunk
            while cur:
                next = cur.next
                unused_chunks.put(cur)
                cur = next
            free_non_gc_object(self)

        def foreach(self, callback, arg):
            """Invoke 'callback(address, arg)' for all addresses in the stack.
            Typically, 'callback' is a bound method and 'arg' can be None.
            """
            chunk = self.chunk
            count = self.used_in_last_chunk
            while chunk:
                while count > 0:
                    count -= 1
                    callback(chunk.items[count], arg)
                chunk = chunk.next
                count = chunk_size
        foreach._annspecialcase_ = 'specialize:arg(1)'

    cache[chunk_size] = AddressStack
    return AddressStack


def get_address_deque(chunk_size=DEFAULT_CHUNK_SIZE, cache={}):
    try:
        return cache[chunk_size]
    except KeyError:
        pass

    unused_chunks, null_chunk = get_chunk_manager(chunk_size)

    class AddressDeque(object):
        _alloc_flavor_ = "raw"
        
        def __init__(self):
            chunk = unused_chunks.get()
            chunk.next = null_chunk
            self.oldest_chunk = self.newest_chunk = chunk
            self.index_in_oldest = 0
            self.index_in_newest = 0

        def enlarge(self):
            new = unused_chunks.get()
            new.next = null_chunk
            self.newest_chunk.next = new
            self.newest_chunk = new
            self.index_in_newest = 0
        enlarge._dont_inline_ = True

        def shrink(self):
            old = self.oldest_chunk
            self.oldest_chunk = old.next
            unused_chunks.put(old)
            self.index_in_oldest = 0
        shrink._dont_inline_ = True

        def append(self, addr):
            index = self.index_in_newest
            if index == chunk_size:
                self.enlarge()
                index = 0
            self.newest_chunk.items[index] = addr
            self.index_in_newest = index + 1

        def non_empty(self):
            return (self.oldest_chunk != self.newest_chunk
                    or self.index_in_oldest < self.index_in_newest)

        def popleft(self):
            ll_assert(self.non_empty(), "pop on empty AddressDeque")
            index = self.index_in_oldest
            if index == chunk_size:
                self.shrink()
                index = 0
            result = self.oldest_chunk.items[index]
            self.index_in_oldest = index + 1
            return result

        def delete(self):
            cur = self.oldest_chunk
            while cur:
                next = cur.next
                unused_chunks.put(cur)
                cur = next
            free_non_gc_object(self)

    cache[chunk_size] = AddressDeque
    return AddressDeque
