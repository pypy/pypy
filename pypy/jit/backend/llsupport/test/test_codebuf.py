import random
from pypy.jit.backend.llsupport.codebuf import AsmMemoryManager


def test_get_index():
    memmgr = AsmMemoryManager(min_fragment=8,
                              num_indices=5)
    index = 0
    for length in range(100):
        assert memmgr._get_index(length) == index
        if length in [8, 11, 15, 21]:
            index += 1

def test_get_index_default_values():
    memmgr = AsmMemoryManager()
    jumps = [64, 86, 115, 154, 206, 275, 367, 490, 654, 873, 1165,
             1554, 2073, 2765, 3687, 4917, 6557, 8743, 11658, 15545,
             20727, 27637, 36850, 49134, 65513, 87351, 116469, 155293,
             207058, 276078, 368105]
    for i, jump in enumerate(jumps):
        assert memmgr._get_index(jump) == i
        assert memmgr._get_index(jump + 1) == i + 1

def test_add_free_block():
    memmgr = AsmMemoryManager(min_fragment=8,
                              num_indices=5)
    memmgr._add_free_block(10, 18)
    assert memmgr.free_blocks == {10: 18}
    assert memmgr.free_blocks_end == {18: 10}
    assert memmgr.blocks_by_size == [[10], [], [], [], []]
    memmgr._add_free_block(20, 30)
    assert memmgr.free_blocks == {10: 18, 20: 30}
    assert memmgr.free_blocks_end == {18: 10, 30: 20}
    assert memmgr.blocks_by_size == [[10], [20], [], [], []]
    memmgr._add_free_block(18, 20)   # merge both left and right
    assert memmgr.free_blocks == {10: 30}
    assert memmgr.free_blocks_end == {30: 10}
    assert memmgr.blocks_by_size == [[], [], [], [10], []]

def test_allocate_block():
    memmgr = AsmMemoryManager(min_fragment=8,
                              num_indices=5)
    memmgr._add_free_block(10, 18)
    memmgr._add_free_block(20, 30)
    (start, stop) = memmgr._allocate_block(4)
    assert (start, stop) == (10, 18)
    assert memmgr.free_blocks == {20: 30}
    assert memmgr.free_blocks_end == {30: 20}
    assert memmgr.blocks_by_size == [[], [20], [], [], []]
    (start, stop) = memmgr._allocate_block(4)
    assert (start, stop) == (20, 30)
    assert memmgr.free_blocks == {}
    assert memmgr.free_blocks_end == {}
    assert memmgr.blocks_by_size == [[], [], [], [], []]

def test_malloc_without_fragment():
    memmgr = AsmMemoryManager(min_fragment=8,
                              num_indices=5)
    memmgr._add_free_block(10, 18)
    memmgr._add_free_block(20, 30)
    for minsize in range(1, 11):
        for maxsize in range(minsize, 14):
            (start, stop) = memmgr.malloc(minsize, maxsize)
            if minsize <= 8:
                assert (start, stop) == (10, 18)
            else:
                assert (start, stop) == (20, 30)
            memmgr._add_free_block(start, stop)
    memmgr._add_free_block(40, 49)
    (start, stop) = memmgr.malloc(10, 10)
    assert (start, stop) == (20, 30)

def test_malloc_with_fragment():
    for reqsize in range(1, 33):
        memmgr = AsmMemoryManager(min_fragment=8,
                                  num_indices=5)
        memmgr._add_free_block(12, 44)
        (start, stop) = memmgr.malloc(reqsize, reqsize)
        if reqsize + 8 <= 32:
            assert (start, stop) == (12, 12 + reqsize)
            assert memmgr.free_blocks == {stop: 44}
            assert memmgr.free_blocks_end == {44: stop}
            assert [stop] in memmgr.blocks_by_size
        else:
            assert (start, stop) == (12, 44)
            assert memmgr.free_blocks == {}
            assert memmgr.free_blocks_end == {}
            assert memmgr.blocks_by_size == [[], [], [], [], []]


class TestAsmMemoryManager:

    def setup_method(self, _):
        self.memmgr = AsmMemoryManager(min_fragment=8,
                                       num_indices=10,
                                       large_alloc_size=8192)

    def teardown_method(self, _):
        self.memmgr._delete()

    def test_malloc_simple(self):
        for i in range(100):
            while self.memmgr.total_memory_allocated < 16384:
                reqsize = random.randrange(1, 200)
                (start, stop) = self.memmgr.malloc(reqsize, reqsize)
                assert reqsize <= stop - start < reqsize + 8
                assert self.memmgr.total_memory_allocated in [8192, 16384]
            self.teardown_method(None)
            self.setup_method(None)

    def test_random(self):
        got = []
        real_use = 0
        prev_total = 0
        iterations_without_allocating_more = 0
        while True:
            #
            if got and (random.random() < 0.4 or len(got) == 1000):
                # free
                start, stop = got.pop(random.randrange(0, len(got)))
                self.memmgr.free(start, stop)
                real_use -= (stop - start)
                assert real_use >= 0
            #
            else:
                # allocate
                reqsize = random.randrange(1, 200)
                if random.random() < 0.5:
                    reqmaxsize = reqsize
                else:
                    reqmaxsize = reqsize + random.randrange(0, 200)
                (start, stop) = self.memmgr.malloc(reqsize, reqmaxsize)
                assert reqsize <= stop - start < reqmaxsize + 8
                for otherstart, otherstop in got:           # no overlap
                    assert otherstop <= start or stop <= otherstart
                got.append((start, stop))
                real_use += (stop - start)
                if self.memmgr.total_memory_allocated == prev_total:
                    iterations_without_allocating_more += 1
                    if iterations_without_allocating_more == 40000:
                        break    # ok
                else:
                    new_total = self.memmgr.total_memory_allocated
                    iterations_without_allocating_more = 0
                    print real_use, new_total
                    # We seem to never see a printed value greater
                    # than 131072.  Be reasonable and allow up to 147456.
                    assert new_total <= 147456
                    prev_total = new_total
