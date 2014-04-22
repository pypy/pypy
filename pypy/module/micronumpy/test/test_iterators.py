from pypy.module.micronumpy import support
from pypy.module.micronumpy.iterators import ArrayIter


class MockArray(object):
    start = 0


class TestIterDirect(object):
    def test_iterator_basic(self):
        #Let's get started, simple iteration in C order with
        #contiguous layout => strides[-1] is 1
        shape = [3, 5]
        strides = [5, 1]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [10, 4]
        i = ArrayIter(MockArray, support.product(shape), shape,
                      strides, backstrides)
        s = i.reset()
        s = i.next(s)
        s = i.next(s)
        s = i.next(s)
        assert s.offset == 3
        assert not i.done(s)
        assert s.indices == [0,3]
        #cause a dimension overflow
        s = i.next(s)
        s = i.next(s)
        assert s.offset == 5
        assert s.indices == [1,0]

        #Now what happens if the array is transposed? strides[-1] != 1
        # therefore layout is non-contiguous
        strides = [1, 3]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [2, 12]
        i = ArrayIter(MockArray, support.product(shape), shape,
                      strides, backstrides)
        s = i.reset()
        s = i.next(s)
        s = i.next(s)
        s = i.next(s)
        assert s.offset == 9
        assert not i.done(s)
        assert s.indices == [0,3]
        #cause a dimension overflow
        s = i.next(s)
        s = i.next(s)
        assert s.offset == 1
        assert s.indices == [1,0]

    def test_iterator_step(self):
        #iteration in C order with #contiguous layout => strides[-1] is 1
        #skip less than the shape
        shape = [3, 5]
        strides = [5, 1]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [10, 4]
        i = ArrayIter(MockArray, support.product(shape), shape,
                      strides, backstrides)
        s = i.reset()
        s = i.next_skip_x(s, 2)
        s = i.next_skip_x(s, 2)
        s = i.next_skip_x(s, 2)
        assert s.offset == 6
        assert not i.done(s)
        assert s.indices == [1,1]
        #And for some big skips
        s = i.next_skip_x(s, 5)
        assert s.offset == 11
        assert s.indices == [2,1]
        s = i.next_skip_x(s, 5)
        # Note: the offset does not overflow but recycles,
        # this is good for broadcast
        assert s.offset == 1
        assert s.indices == [0,1]
        assert i.done(s)

        #Now what happens if the array is transposed? strides[-1] != 1
        # therefore layout is non-contiguous
        strides = [1, 3]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [2, 12]
        i = ArrayIter(MockArray, support.product(shape), shape,
                      strides, backstrides)
        s = i.reset()
        s = i.next_skip_x(s, 2)
        s = i.next_skip_x(s, 2)
        s = i.next_skip_x(s, 2)
        assert s.offset == 4
        assert s.indices == [1,1]
        assert not i.done(s)
        s = i.next_skip_x(s, 5)
        assert s.offset == 5
        assert s.indices == [2,1]
        assert not i.done(s)
        s = i.next_skip_x(s, 5)
        assert s.indices == [0,1]
        assert s.offset == 3
        assert i.done(s)
