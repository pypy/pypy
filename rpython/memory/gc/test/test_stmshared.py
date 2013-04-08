from rpython.memory.gc.stmshared import WORD
from rpython.memory.gc.stmshared import StmGCSharedArea
from rpython.memory.gc.stmshared import StmGCThreadLocalAllocator


def test_simple():
    shared = StmGCSharedArea("gc", 10*WORD, 2*WORD)
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
