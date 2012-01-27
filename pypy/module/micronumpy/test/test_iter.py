import py
from pypy.module.micronumpy.interp_iter import ViewIterator

# This is both a test and a mini-tutorial on iterators, strides, and
# memory layout. It assumes you are familiar with the terms, see
# http://docs.scipy.org/doc/numpy/reference/arrays.ndarray.html
# for a more gentle introduction.
#
# Given an array x: x.shape == [5,6],
#
# At which byte in x.data does the item x[3,4] begin?
# if x.strides==[1,5]:
#     pData = x.pData + (x.start + 3*1 + 4*5)*sizeof(x.pData[0])
#     pData = x.pData + (x.start + 24) * sizeof(x.pData[0])
# so the offset of the element is 24 elements after the first
#
# What is the next element in x after coordinates [3,4]?
# if x.order =='C':
#    next == [3,5] => offset is 28
# if x.order =='F':
#    next == [4,4] => offset is 24
# so for the strides [1,5] x is 'F' contiguous
# likewise, for the strides [6,1] x would be 'C' contiguous.
# 
# Iterators have an internal representation of the current coordinates
# (indices), the array, strides, and backstrides. A short digression to
# explain backstrides: what is the coordinate and offset after [3,5] in
# the example above?
# if x.order == 'C':
#    next == [4,0] => offset is 4
# if x.order == 'F':
#    next == [4,5] => offset is 25
# Note that in 'C' order we stepped BACKWARDS 24 while 'overflowing' a
# shape dimension
#   which is back 25 and forward 1,
#   which is x.strides[1] * (x.shape[1] - 1) + x.strides[0]
# so if we precalculate the overflow backstride as 
# [x.strides[i] * (x.shape[i] - 1) for i in range(len(x.shape))]
# we can go faster.
# All the calculations happen in next()
#
# next_step_x() tries to do the iteration for a number of steps at once,
# but then we cannot gaurentee that we only overflow one single shape 
# dimension, perhaps we could overflow times in one big step.
#

class TestIterDirect(object):
    def test_C_viewiterator(self):
        #Let's get started, simple iteration in C order with
        #contiguous layout => strides[-1] is 1
        start = 0
        shape = [3, 5] 
        strides = [5, 1]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [10, 4]
        i = ViewIterator(start, strides, backstrides, shape)
        i = i.next(2)
        i = i.next(2)
        i = i.next(2)
        assert i.offset == 3
        assert not i.done()
        assert i.indices == [0,3]
        #cause a dimension overflow
        i = i.next(2)
        i = i.next(2)
        assert i.offset == 5
        assert i.indices == [1,0]

        #Now what happens if the array is transposed? strides[-1] != 1
        # therefore layout is non-contiguous
        strides = [1, 3]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [2, 12]
        i = ViewIterator(start, strides, backstrides, shape)
        i = i.next(2)
        i = i.next(2)
        i = i.next(2)
        assert i.offset == 9
        assert not i.done()
        assert i.indices == [0,3]
        #cause a dimension overflow
        i = i.next(2)
        i = i.next(2)
        assert i.offset == 1
        assert i.indices == [1,0]

    def test_C_viewiterator_step(self):
        #iteration in C order with #contiguous layout => strides[-1] is 1
        #skip less than the shape
        start = 0
        shape = [3, 5] 
        strides = [5, 1]
        backstrides = [x * (y - 1) for x,y in zip(strides, shape)]
        assert backstrides == [10, 4]
        i = ViewIterator(start, strides, backstrides, shape)
        i = i.next_skip_x(2,2)
        i = i.next_skip_x(2,2)
        i = i.next_skip_x(2,2)
        assert i.offset == 6
        assert not i.done()
        assert i.indices == [1,1]
        #And for some big skips
        i = i.next_skip_x(2,5)
        assert i.offset == 11
        assert i.indices == [2,1]
        i = i.next_skip_x(2,5)
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
        i = ViewIterator(start, strides, backstrides, shape)
        i = i.next_skip_x(2,2)
        i = i.next_skip_x(2,2)
        i = i.next_skip_x(2,2)
        assert i.offset == 4
        assert i.indices == [1,1]
        assert not i.done()
        i = i.next_skip_x(2,5)
        assert i.offset == 5
        assert i.indices == [2,1]
        assert not i.done()
        i = i.next_skip_x(2,5)
        assert i.indices == [0,1]
        assert i.offset == 3
        assert i.done()
