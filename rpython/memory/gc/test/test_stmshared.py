from rpython.memory.gc.stmshared import WORD
from rpython.memory.gc.stmshared import StmGCSharedArea
from rpython.memory.gc.stmshared import StmGCThreadLocalAllocator


class FakeGC:
    class gcheaderbuilder:
        size_gc_header = 3
    def __init__(self):
        self._object_sizes = {}
    def set_size(self, obj, size):
        assert obj not in self._object_sizes
        self._object_sizes[obj] = size
    def get_size_incl_hash(self, obj):
        return self._object_sizes[obj]


def test_simple():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 10*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    thl1.malloc_object(2*WORD-1)
    assert len(thl1._seen_pages) == 1
    thl1.malloc_object(2*WORD)
    assert len(thl1._seen_pages) == 1
    thl1.malloc_object(1*WORD)
    assert len(thl1._seen_pages) == 2
    thl1.malloc_object(2*WORD)
    assert len(thl1._seen_pages) == 2
    thl1.malloc_object(2*WORD)
    assert len(thl1._seen_pages) == 3
    thl1.malloc_object(2*WORD)
    assert len(thl1._seen_pages) == 3
    thl1.delete()

def test_free():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 10*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    obj = thl1.malloc_object(2*WORD)
    gc.set_size(obj, 2*WORD)
    thl1.free_object(obj)
    obj2 = thl1.malloc_object(2*WORD)
    assert obj2 == obj     # reusing the same location
    thl1.delete()

def test_big_object():
    gc = FakeGC()
    shared = StmGCSharedArea(gc, 10*WORD, 2*WORD)
    shared.setup()
    thl1 = StmGCThreadLocalAllocator(shared)
    obj = thl1.malloc_object(3*WORD)
    gc.set_size(obj, 3*WORD)
    thl1.free_object(obj)
    thl1.delete()
