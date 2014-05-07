""" This is a mini-tutorial on iterators, strides, and
memory layout. It assumes you are familiar with the terms, see
http://docs.scipy.org/doc/numpy/reference/arrays.ndarray.html
for a more gentle introduction.

Given an array x: x.shape == [5,6], where each element occupies one byte

At which byte in x.data does the item x[3,4] begin?
if x.strides==[1,5]:
    pData = x.pData + (x.start + 3*1 + 4*5)*sizeof(x.pData[0])
    pData = x.pData + (x.start + 24) * sizeof(x.pData[0])
so the offset of the element is 24 elements after the first

What is the next element in x after coordinates [3,4]?
if x.order =='C':
   next == [3,5] => offset is 28
if x.order =='F':
   next == [4,4] => offset is 24
so for the strides [1,5] x is 'F' contiguous
likewise, for the strides [6,1] x would be 'C' contiguous.

Iterators have an internal representation of the current coordinates
(indices), the array, strides, and backstrides. A short digression to
explain backstrides: what is the coordinate and offset after [3,5] in
the example above?
if x.order == 'C':
   next == [4,0] => offset is 4
if x.order == 'F':
   next == [4,5] => offset is 25
Note that in 'C' order we stepped BACKWARDS 24 while 'overflowing' a
shape dimension
  which is back 25 and forward 1,
  which is x.strides[1] * (x.shape[1] - 1) + x.strides[0]
so if we precalculate the overflow backstride as
[x.strides[i] * (x.shape[i] - 1) for i in range(len(x.shape))]
we can go faster.
All the calculations happen in next()

next_skip_x(steps) tries to do the iteration for a number of steps at once,
but then we cannot guarantee that we only overflow one single shape
dimension, perhaps we could overflow times in one big step.
"""
from rpython.rlib import jit
from pypy.module.micronumpy import support
from pypy.module.micronumpy.base import W_NDimArray


class PureShapeIter(object):
    def __init__(self, shape, idx_w):
        self.shape = shape
        self.shapelen = len(shape)
        self.indexes = [0] * len(shape)
        self._done = False
        self.idx_w_i = [None] * len(idx_w)
        self.idx_w_s = [None] * len(idx_w)
        for i, w_idx in enumerate(idx_w):
            if isinstance(w_idx, W_NDimArray):
                self.idx_w_i[i], self.idx_w_s[i] = w_idx.create_iter(shape)

    def done(self):
        return self._done

    @jit.unroll_safe
    def next(self):
        for i, idx_w_i in enumerate(self.idx_w_i):
            if idx_w_i is not None:
                self.idx_w_s[i] = idx_w_i.next(self.idx_w_s[i])
        for i in range(self.shapelen - 1, -1, -1):
            if self.indexes[i] < self.shape[i] - 1:
                self.indexes[i] += 1
                break
            else:
                self.indexes[i] = 0
        else:
            self._done = True

    @jit.unroll_safe
    def get_index(self, space, shapelen):
        return [space.wrap(self.indexes[i]) for i in range(shapelen)]


class IterState(object):
    _immutable_fields_ = ['iterator', 'index', 'indices[*]', 'offset']

    def __init__(self, iterator, index, indices, offset):
        self.iterator = iterator
        self.index = index
        self.indices = indices
        self.offset = offset


class ArrayIter(object):
    _immutable_fields_ = ['array', 'size', 'ndim_m1', 'shape_m1[*]',
                          'strides[*]', 'backstrides[*]']

    def __init__(self, array, size, shape, strides, backstrides):
        assert len(shape) == len(strides) == len(backstrides)
        self.array = array
        self.size = size
        self.ndim_m1 = len(shape) - 1
        self.shape_m1 = [s - 1 for s in shape]
        self.strides = strides
        self.backstrides = backstrides

    def reset(self):
        return IterState(self, 0, [0] * len(self.shape_m1), self.array.start)

    @jit.unroll_safe
    def next(self, state):
        assert state.iterator is self
        index = state.index + 1
        indices = state.indices
        offset = state.offset
        for i in xrange(self.ndim_m1, -1, -1):
            idx = indices[i]
            if idx < self.shape_m1[i]:
                indices[i] = idx + 1
                offset += self.strides[i]
                break
            else:
                indices[i] = 0
                offset -= self.backstrides[i]
        return IterState(self, index, indices, offset)

    @jit.unroll_safe
    def next_skip_x(self, state, step):
        assert state.iterator is self
        assert step >= 0
        if step == 0:
            return state
        index = state.index + step
        indices = state.indices
        offset = state.offset
        for i in xrange(self.ndim_m1, -1, -1):
            idx = indices[i]
            if idx < (self.shape_m1[i] + 1) - step:
                indices[i] = idx + step
                offset += self.strides[i] * step
                break
            else:
                rem_step = (idx + step) // (self.shape_m1[i] + 1)
                cur_step = step - rem_step * (self.shape_m1[i] + 1)
                indices[i] = idx + cur_step
                offset += self.strides[i] * cur_step
                step = rem_step
                assert step > 0
        return IterState(self, index, indices, offset)

    def done(self, state):
        assert state.iterator is self
        return state.index >= self.size

    def getitem(self, state):
        assert state.iterator is self
        return self.array.getitem(state.offset)

    def getitem_bool(self, state):
        assert state.iterator is self
        return self.array.getitem_bool(state.offset)

    def setitem(self, state, elem):
        assert state.iterator is self
        self.array.setitem(state.offset, elem)


def AxisIter(array, shape, axis, cumulative):
    strides = array.get_strides()
    backstrides = array.get_backstrides()
    if not cumulative:
        if len(shape) == len(strides):
            # keepdims = True
            strides = strides[:axis] + [0] + strides[axis + 1:]
            backstrides = backstrides[:axis] + [0] + backstrides[axis + 1:]
        else:
            strides = strides[:axis] + [0] + strides[axis:]
            backstrides = backstrides[:axis] + [0] + backstrides[axis:]
    return ArrayIter(array, support.product(shape), shape, strides, backstrides)


def AllButAxisIter(array, axis):
    size = array.get_size()
    shape = array.get_shape()[:]
    backstrides = array.backstrides[:]
    if size:
        size /= shape[axis]
    shape[axis] = backstrides[axis] = 0
    return ArrayIter(array, size, shape, array.strides, backstrides)
