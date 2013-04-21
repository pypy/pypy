from rpython.memory.gc.stmshared import WORD
from rpython.memory.gc.stmshared import StmGCSharedArea
from rpython.memory.gc.stmshared import StmGCThreadLocalAllocator
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi


SGH = 3

class FakeGC:
    class gcheaderbuilder:
        size_gc_header = SGH
    def __init__(self):
        self._object_sizes = {}
    def set_size(self, obj, size):
        assert obj not in self._object_sizes
        self._object_sizes[obj] = size
    def get_size_incl_hash(self, obj):
        return self._object_sizes[obj]
    def acquire_global_lock(self):
        pass
    def release_global_lock(self):
        pass

class FakeRootWalker:
    def __init__(self, rootobjlist):
        self._rootobjlist = rootobjlist
    def walk_all_stack_roots(self, collect_stack_root, arg):
        for obj in self._rootobjlist:
            p = lltype.malloc(rffi.CArray(llmemory.Address), 1, flavor='raw')
            p[0] = obj
            collect_stack_root(arg, llmemory.cast_ptr_to_adr(p))
            assert p[0] == obj   # should not move
            lltype.free(p)


def test_simple():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 9*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    thl1.malloc_object(2*WORD-1-SGH)
    assert len(thl1._seen_pages) == 1
    thl1.malloc_object(2*WORD-SGH)
    assert len(thl1._seen_pages) == 1
    thl1.malloc_object(1*WORD-SGH)
    assert len(thl1._seen_pages) == 2
    thl1.malloc_object(2*WORD-SGH)
    assert len(thl1._seen_pages) == 2
    thl1.malloc_object(2*WORD-SGH)
    assert len(thl1._seen_pages) == 3
    thl1.malloc_object(2*WORD-SGH)
    assert len(thl1._seen_pages) == 3
    assert thl1.count_pages == 3
    thl1.delete()

def test_free():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 9*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    obj = thl1.malloc_object(2*WORD-SGH)
    gc.set_size(obj, 2*WORD-SGH)
    thl1.free_object(obj)
    obj2 = thl1.malloc_object(2*WORD-SGH)
    assert obj2 == obj     # reusing the same location
    thl1.delete()

def test_big_object():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 9*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    obj = thl1.malloc_object(3*WORD-SGH)
    gc.set_size(obj, 3*WORD-SGH)
    thl1.free_object(obj)
    thl1.delete()

def test_allocation_is_thread_local():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 9*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    thl2 = StmGCThreadLocalAllocator(shared)
    #
    assert len(thl1._seen_pages) == 0
    thl1.malloc_object(2*WORD-SGH)
    assert len(thl1._seen_pages) == 1
    #
    assert len(thl2._seen_pages) == 0
    thl2.malloc_object(2*WORD-SGH)
    assert len(thl2._seen_pages) == 1
    #
    thl1.delete()
    thl2.delete()

def test_dying_gift_to_shared_area():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 9*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    thl1.malloc_object(2*WORD-SGH)
    assert thl1.count_pages == 1
    assert len(thl1._seen_pages) == 1
    #
    assert shared.count_global_pages == 0
    thl1.delete()
    assert shared.count_global_pages == 1

def test_do_major_collection():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 9*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    obj1 = thl1.malloc_object(2*WORD-SGH)
    obj2 = thl1.malloc_object(2*WORD-SGH)
    #
    gc.root_walker = FakeRootWalker([obj2])
    shared.do_major_collection()
    #
    xxx
