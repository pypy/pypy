
""" This is a mini-tutorial on iterators, strides, and
memory layout. It assumes you are familiar with the terms, see
http://docs.scipy.org/doc/numpy/reference/arrays.ndarray.html
for a more gentle introduction.

Given an array x: x.shape == [5,6],

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

next_skip_x() tries to do the iteration for a number of steps at once,
but then we cannot gaurentee that we only overflow one single shape 
dimension, perhaps we could overflow times in one big step.
"""

from pypy.module.micronumpy.strides import enumerate_chunks,\
     calculate_slice_strides
from pypy.module.micronumpy.base import W_NDimArray
from pypy.rlib import jit

# structures to describe slicing

class BaseChunk(object):
    pass

class RecordChunk(BaseChunk):
    def __init__(self, name):
        self.name = name

    def apply(self, arr):
        ofs, subdtype = arr.dtype.fields[self.name]
        # strides backstrides are identical, ofs only changes start
        return W_NDimArray.new_slice(arr.start + ofs, arr.get_strides(),
                                     arr.get_backstrides(),
                                     arr.shape, arr, subdtype)

class Chunks(BaseChunk):
    def __init__(self, l):
        self.l = l

    @jit.unroll_safe
    def extend_shape(self, old_shape):
        shape = []
        i = -1
        for i, c in enumerate_chunks(self.l):
            if c.step != 0:
                shape.append(c.lgt)
        s = i + 1
        assert s >= 0
        return shape[:] + old_shape[s:]

    def apply(self, arr):
        shape = self.extend_shape(arr.shape)
        r = calculate_slice_strides(arr.shape, arr.start, arr.get_strides(),
                                    arr.get_backstrides(), self.l)
        _, start, strides, backstrides = r
        return W_NDimArray.new_slice(start, strides[:], backstrides[:],
                                     shape[:], arr)


class Chunk(BaseChunk):
    axis_step = 1

    def __init__(self, start, stop, step, lgt):
        self.start = start
        self.stop = stop
        self.step = step
        self.lgt = lgt

    def __repr__(self):
        return 'Chunk(%d, %d, %d, %d)' % (self.start, self.stop, self.step,
                                          self.lgt)

class NewAxisChunk(Chunk):
    start = 0
    stop = 1
    step = 1
    lgt = 1
    axis_step = 0

    def __init__(self):
        pass

class BaseTransform(object):
    pass

class ViewTransform(BaseTransform):
    def __init__(self, chunks):
        # 4-tuple specifying slicing
        self.chunks = chunks

class BroadcastTransform(BaseTransform):
    def __init__(self, res_shape):
        self.res_shape = res_shape
