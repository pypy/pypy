from pypy.module.micronumpy.iter import ArrayIterator


class MockArray(object):
    size = 1
    start = 0


class TestIterDirect(object):
    def test_iterator_basic(self):
        #Let's get started, simple iteration in C order with
        #contiguous layout => strides[-1] is 1
        shape = [3, 5]
        strides = [5, 1]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [10, 4]
        i = ArrayIterator(MockArray, shape, strides, backstrides)
        i.next()
        i.next()
        i.next()
        assert i.offset == 3
        assert not i.done()
        assert i.indices == [0,3]
        #cause a dimension overflow
        i.next()
        i.next()
        assert i.offset == 5
        assert i.indices == [1,0]

        #Now what happens if the array is transposed? strides[-1] != 1
        # therefore layout is non-contiguous
        strides = [1, 3]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [2, 12]
        i = ArrayIterator(MockArray, shape, strides, backstrides)
        i.next()
        i.next()
        i.next()
        assert i.offset == 9
        assert not i.done()
        assert i.indices == [0,3]
        #cause a dimension overflow
        i.next()
        i.next()
        assert i.offset == 1
        assert i.indices == [1,0]

    def test_iterator_step(self):
        #iteration in C order with #contiguous layout => strides[-1] is 1
        #skip less than the shape
        shape = [3, 5]
        strides = [5, 1]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [10, 4]
        i = ArrayIterator(MockArray, shape, strides, backstrides)
        i.next_skip_x(2)
        i.next_skip_x(2)
        i.next_skip_x(2)
        assert i.offset == 6
        assert not i.done()
        assert i.indices == [1,1]
        #And for some big skips
        i.next_skip_x(5)
        assert i.offset == 11
        assert i.indices == [2,1]
        i.next_skip_x(5)
        # Note: the offset does not overflow but recycles,
        # this is good for broadcast
        assert i.offset == 1
        assert i.indices == [0,1]
        assert i.done()

        #Now what happens if the array is transposed? strides[-1] != 1
        # therefore layout is non-contiguous
        strides = [1, 3]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [2, 12]
        i = ArrayIterator(MockArray, shape, strides, backstrides)
        i.next_skip_x(2)
        i.next_skip_x(2)
        i.next_skip_x(2)
        assert i.offset == 4
        assert i.indices == [1,1]
        assert not i.done()
        i.next_skip_x(5)
        assert i.offset == 5
        assert i.indices == [2,1]
        assert not i.done()
        i.next_skip_x(5)
        assert i.indices == [0,1]
        assert i.offset == 3
        assert i.done()
