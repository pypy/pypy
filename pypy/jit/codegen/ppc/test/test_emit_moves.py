import py
from pypy.jit.codegen.ppc.emit_moves import emit_moves, emit_moves_safe

class TheHeap(object):
    def __init__(self, locs):
        self.data = {}
        for i in range(locs):
            self.data[i] = i
        self.numlocs = locs
    def emit_move(self, tar, src):
        self.data[tar] = self.data[src]
    def create_fresh_location(self):
        self.numlocs += 1
        return self.numlocs-1

def test_simple_cycle():
    heap = TheHeap(2)
    tar2src = {'A':'b', 'B':'a'}
    tar2loc = {'A':0, 'B':1}
    src2loc = {'a':0, 'b':1}
    assert heap.data[0] == 0
    assert heap.data[1] == 1
    emit_moves(heap, tar2src.keys(), tar2src, tar2loc, src2loc)
    assert heap.data[0] == 1
    assert heap.data[1] == 0
    assert heap.numlocs == 3 # only creates 1 extra loc

def test_cycle_3():
    heap = TheHeap(3)
    tar2src = {'A':'b', 'B':'c', 'C':'a'}
    tar2loc = {'A':0, 'B':1, 'C':2}
    src2loc = {'a':0, 'b':1, 'c':2}
    assert heap.data[0] == 0
    assert heap.data[1] == 1
    assert heap.data[2] == 2
    emit_moves(heap, tar2src.keys(), tar2src, tar2loc, src2loc)
    assert heap.data[0] == 1
    assert heap.data[1] == 2
    assert heap.data[2] == 0
    assert heap.numlocs == 4 # only creates 1 extra loc

def test_dag():
    heap = TheHeap(3)
    tar2src = {'A':'a', 'B':'b'}
    tar2loc = {'A':0, 'B':1}
    src2loc = {'a':1, 'b':2}
    assert heap.data[0] == 0
    assert heap.data[1] == 1
    assert heap.data[2] == 2
    emit_moves(heap, tar2src.keys(), tar2src, tar2loc, src2loc)
    assert heap.data[0] == 1
    assert heap.data[1] == 2
    assert heap.data[2] == 2
    assert heap.numlocs == 3 # only creates 1 extra loc

def test_one_to_many():
    heap = TheHeap(4)
    tar2src = {'A':'a', 'B':'b', 'C':'a'}
    tar2loc = {'A':2, 'B':1, 'C':3}
    src2loc = {'a':1, 'b':0}
    assert heap.data[0] == 0 # b
    assert heap.data[1] == 1 # a
    assert heap.data[2] == 2
    assert heap.data[3] == 3
    emit_moves(heap, ['B', 'A', 'C'], tar2src, tar2loc, src2loc)
    assert heap.data[1] == 0 # B
    assert heap.data[2] == 1 # A
    assert heap.data[3] == 1 # C

def test_random():
    for _ in range(20):
        import random
        NVAR = random.randrange(1000)
        heap = TheHeap(NVAR)
        varlist = range(NVAR)
        tar2src = {}
        src2loc = {}
        tar2loc = {}
        for i in varlist:
            tar2src[i] = random.randrange(NVAR)
        srcs = list(dict.fromkeys(tar2src.values()))
        srclocs = srcs[:]
        random.shuffle(srclocs)
        for j, k in zip(srcs, srclocs):
            src2loc[j] = k
        varlist2 = varlist[:]
        random.shuffle(varlist2)
        for i, j in zip(varlist, varlist2):
            tar2loc[i] = j
        for i in range(10):
            random.shuffle(varlist)
            heap1 = TheHeap(NVAR)
            emit_moves(heap1, varlist,
                            tar2src.copy(), tar2loc.copy(), src2loc.copy())
            heap2 = TheHeap(NVAR)
            emit_moves_safe(heap2, varlist,
                            tar2src.copy(), tar2loc.copy(), src2loc.copy())
            for i in range(NVAR):
                assert heap1.data[i] == heap2.data[i]
