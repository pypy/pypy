import py
from pypy.objspace.std.smartresizablelist import *

def test_leftmost_set_bit():
    assert leftmost_set_bit(2) == 1
    assert leftmost_set_bit(3) == 1
    assert leftmost_set_bit(4) == 2
    assert leftmost_set_bit(5) == 2
    assert leftmost_set_bit(6) == 2
    assert leftmost_set_bit(7) == 2
    assert leftmost_set_bit(8) == 3
    assert leftmost_set_bit(9) == 3
    assert leftmost_set_bit(10) == 3
    assert leftmost_set_bit(11) == 3
    assert leftmost_set_bit(12) == 3
    assert leftmost_set_bit(13) == 3
    assert leftmost_set_bit(14) == 3
    assert leftmost_set_bit(15) == 3
    assert leftmost_set_bit(2 ** 18 + 1) == 18

def test_decompose():
    for i in range(1, 500):
        k = leftmost_set_bit(i)
        b, e = decompose(i, k)
        hk = k // 2 + (k & 1)
        assert (b << hk) + e + (1 << k) == i

SIZE = 700
def test_grow():
    l = SmartResizableListImplementation(None)
    for i in range(SIZE):
#        import pdb; pdb.set_trace()
        pos = l.grow()
        assert l.length() == i + 1
        assert pos == find_block_index(i)
        l.setitem(i, "hello" + str(i))
        for j in range(i + 1):
            assert l.getitem(j) == "hello" + str(j)

def test_grow_steps():
    for step in range(2, 100, 10):
        l = SmartResizableListImplementation(None)
        for m in range(0, SIZE, step):
            pos = l.grow(step)
            assert pos == find_block_index(m + step - 1)
            assert l.length() == m + step
            for i in range(m, m + step):
                l.setitem(i, "hello" + str(i))
            for j in range(m + 1):
                assert l.getitem(j) == "hello" + str(j)

def test_shrink():
    l = SmartResizableListImplementation(None)
    for i in range(2):
        l.grow(SIZE)
        for i in range(SIZE):
            l.setitem(i, i + 42)
        for i in range(SIZE):
            l.shrink()
            assert l.length() == SIZE - i - 1
            for j in range(l.length()):
                assert l.getitem(j) == j + 42
        py.test.raises(ValueError, l.shrink)

def test_shrink_sets_none():
    l = SmartResizableListImplementation(None)
    for i in range(SIZE):
        l.grow(2)
        assert l.getitem(i) == None
        assert l.getitem(i + 1) == None
        l.setitem(i, i)
        l.setitem(i + 1, i + 1)
        l.shrink()
        assert l.getitem(i) == i

def test_shrink_steps():
    for step in range(2, 100, 10):
        l = SmartResizableListImplementation(None)
        l.grow(SIZE)
        for i in range(SIZE):
            l.setitem(i, "hello" + str(i))
        for m in range(0, SIZE - step, step):
            pos = l.shrink(step)
            assert l.length() == SIZE - m - step
            for i in range(l.length()):
                assert l.getitem(i) == "hello" + str(i)

def test_random():
    import random
    l = SmartResizableListImplementation(None)
    for i in range(1000):
        previous = l.length()
        print i, previous
        c = random.randrange(2)
        if c == 0 or l.length() == 0:
            items = random.randrange(1, SIZE)
            l.grow(items)
            assert l.length() == previous + items
            for i in range(previous, previous + items):
                assert l.getitem(i) is None
                l.setitem(i, i + 42)
        else:
            items = random.randrange(1, l.length() + 1)
            l.shrink(items)
            assert l.length() == previous - items
            if l.length() > 5:
                for i in range(l.length() - 5, l.length()):
                    assert l.getitem(i) == i + 42
    for i in range(l.length()):
        assert l.getitem(i) == i + 42
