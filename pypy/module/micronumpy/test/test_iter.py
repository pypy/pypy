from pypy.module.micronumpy.iter import MultiDimViewIterator


class MockArray(object):
    size = 1


class TestIterDirect(object):
    def test_C_viewiterator(self):
        #Let's get started, simple iteration in C order with
        #contiguous layout => strides[-1] is 1
        start = 0
        shape = [3, 5]
        strides = [5, 1]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [10, 4]
        i = MultiDimViewIterator(MockArray, start, strides, backstrides, shape)
        i.next()
        i.next()
        i.next()
        assert i.offset == 3
        assert not i.done()
        assert i.indexes == [0,3]
        #cause a dimension overflow
        i.next()
        i.next()
        assert i.offset == 5
        assert i.indexes == [1,0]

        #Now what happens if the array is transposed? strides[-1] != 1
        # therefore layout is non-contiguous
        strides = [1, 3]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [2, 12]
        i = MultiDimViewIterator(MockArray, start, strides, backstrides, shape)
        i.next()
        i.next()
        i.next()
        assert i.offset == 9
        assert not i.done()
        assert i.indexes == [0,3]
        #cause a dimension overflow
        i.next()
        i.next()
        assert i.offset == 1
        assert i.indexes == [1,0]

    def test_C_viewiterator_step(self):
        #iteration in C order with #contiguous layout => strides[-1] is 1
        #skip less than the shape
        start = 0
        shape = [3, 5]
        strides = [5, 1]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [10, 4]
        i = MultiDimViewIterator(MockArray, start, strides, backstrides, shape)
        i.next_skip_x(2)
        i.next_skip_x(2)
        i.next_skip_x(2)
        assert i.offset == 6
        assert not i.done()
        assert i.indexes == [1,1]
        #And for some big skips
        i.next_skip_x(5)
        assert i.offset == 11
        assert i.indexes == [2,1]
        i.next_skip_x(5)
        # Note: the offset does not overflow but recycles,
        # this is good for broadcast
        assert i.offset == 1
        assert i.indexes == [0,1]
        assert i.done()

        #Now what happens if the array is transposed? strides[-1] != 1
        # therefore layout is non-contiguous
        strides = [1, 3]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [2, 12]
        i = MultiDimViewIterator(MockArray, start, strides, backstrides, shape)
        i.next_skip_x(2)
        i.next_skip_x(2)
        i.next_skip_x(2)
        assert i.offset == 4
        assert i.indexes == [1,1]
        assert not i.done()
        i.next_skip_x(5)
        assert i.offset == 5
        assert i.indexes == [2,1]
        assert not i.done()
        i.next_skip_x(5)
        assert i.indexes == [0,1]
        assert i.offset == 3
        assert i.done()
