
from pypy.rlib import jit
from pypy.rlib.objectmodel import instantiate
from pypy.module.micronumpy.strides import calculate_broadcast_strides,\
     calculate_slice_strides, calculate_dot_strides, enumerate_chunks

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

# structures to describe slicing

class BaseChunk(object):
    pass

class RecordChunk(BaseChunk):
    def __init__(self, name):
        self.name = name

    def apply(self, arr):
        from pypy.module.micronumpy.interp_numarray import W_NDimSlice

        arr = arr.get_concrete()
        ofs, subdtype = arr.dtype.fields[self.name]
        # strides backstrides are identical, ofs only changes start
        return W_NDimSlice(arr.start + ofs, arr.strides[:], arr.backstrides[:],
                           arr.shape[:], arr, subdtype)

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
        from pypy.module.micronumpy.interp_numarray import W_NDimSlice,\
             VirtualSlice, ConcreteArray

        shape = self.extend_shape(arr.shape)
        if not isinstance(arr, ConcreteArray):
            return VirtualSlice(arr, self, shape)
        r = calculate_slice_strides(arr.shape, arr.start, arr.strides,
                                    arr.backstrides, self.l)
        _, start, strides, backstrides = r
        return W_NDimSlice(start, strides[:], backstrides[:],
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


class BaseIterator(object):
    def next(self, shapelen):
        raise NotImplementedError

    def done(self):
        raise NotImplementedError

    def apply_transformations(self, arr, transformations):
        v = self
        if transformations is not None:
            for transform in transformations:
                v = v.transform(arr, transform)
        return v

    def transform(self, arr, t):
        raise NotImplementedError

class ArrayIterator(BaseIterator):
    def __init__(self, size, element_size):
        self.offset = 0
        self.size = size
        self.element_size = element_size

    def next(self, shapelen):
        return self.next_skip_x(1)

    def next_skip_x(self, x):
        arr = instantiate(ArrayIterator)
        arr.size = self.size
        arr.offset = self.offset + x * self.element_size
        arr.element_size = self.element_size
        return arr

    def next_no_increase(self, shapelen):
        # a hack to make JIT believe this is always virtual
        return self.next_skip_x(0)

    def done(self):
        return self.offset >= self.size

    def transform(self, arr, t):
        return ViewIterator(arr.start, arr.strides, arr.backstrides,
                            arr.shape).transform(arr, t)

class OneDimIterator(BaseIterator):
    def __init__(self, start, step, stop):
        self.offset = start
        self.step = step
        self.size = stop * step + start

    def next(self, shapelen):
        arr = instantiate(OneDimIterator)
        arr.size = self.size
        arr.step = self.step
        arr.offset = self.offset + self.step
        return arr

    def done(self):
        return self.offset == self.size

class ViewIterator(BaseIterator):
    def __init__(self, start, strides, backstrides, shape):
        self.offset  = start
        self._done   = False
        self.strides = strides
        self.backstrides = backstrides
        self.res_shape = shape
        self.indices = [0] * len(self.res_shape)

    def transform(self, arr, t):
        if isinstance(t, BroadcastTransform):
            r = calculate_broadcast_strides(self.strides, self.backstrides,
                                            self.res_shape, t.res_shape)
            return ViewIterator(self.offset, r[0], r[1], t.res_shape)
        elif isinstance(t, ViewTransform):
            r = calculate_slice_strides(self.res_shape, self.offset,
                                        self.strides,
                                        self.backstrides, t.chunks.l)
            return ViewIterator(r[1], r[2], r[3], r[0])

    @jit.unroll_safe
    def next(self, shapelen):
        shapelen = jit.promote(len(self.res_shape))
        offset = self.offset
        indices = [0] * shapelen
        for i in range(shapelen):
            indices[i] = self.indices[i]
        done = False
        for i in range(shapelen - 1, -1, -1):
            if indices[i] < self.res_shape[i] - 1:
                indices[i] += 1
                offset += self.strides[i]
                break
            else:
                indices[i] = 0
                offset -= self.backstrides[i]
        else:
            done = True
        res = instantiate(ViewIterator)
        res.offset = offset
        res.indices = indices
        res.strides = self.strides
        res.backstrides = self.backstrides
        res.res_shape = self.res_shape
        res._done = done
        return res

    @jit.unroll_safe
    def next_skip_x(self, shapelen, step):
        shapelen = jit.promote(len(self.res_shape))
        offset = self.offset
        indices = [0] * shapelen
        for i in range(shapelen):
            indices[i] = self.indices[i]
        done = False
        for i in range(shapelen - 1, -1, -1):
            if indices[i] < self.res_shape[i] - step:
                indices[i] += step
                offset += self.strides[i] * step
                break
            else:
                remaining_step = (indices[i] + step) // self.res_shape[i]
                this_i_step = step - remaining_step * self.res_shape[i]
                offset += self.strides[i] * this_i_step
                indices[i] = indices[i] +  this_i_step
                step = remaining_step
        else:
            done = True
        res = instantiate(ViewIterator)
        res.offset = offset
        res.indices = indices
        res.strides = self.strides
        res.backstrides = self.backstrides
        res.res_shape = self.res_shape
        res._done = done
        return res

    def apply_transformations(self, arr, transformations):
        v = BaseIterator.apply_transformations(self, arr, transformations)
        if len(arr.shape) == 1:
            return OneDimIterator(self.offset, self.strides[0],
                                  self.res_shape[0])
        return v

    def done(self):
        return self._done

class ConstantIterator(BaseIterator):
    def next(self, shapelen):
        return self

    def transform(self, arr, t):
        pass


class AxisIterator(BaseIterator):
    def __init__(self, start, dim, shape, strides, backstrides):
        self.res_shape = shape[:]
        if len(shape) == len(strides):
            # keepdims = True
            self.strides = strides[:dim] + [0] + strides[dim + 1:]
            self.backstrides = backstrides[:dim] + [0] + backstrides[dim + 1:]
        else:
            self.strides = strides[:dim] + [0] + strides[dim:]
            self.backstrides = backstrides[:dim] + [0] + backstrides[dim:]
        self.first_line = True
        self.indices = [0] * len(shape)
        self._done = False
        self.offset = start
        self.dim = dim

    @jit.unroll_safe
    def next(self, shapelen):
        offset = self.offset
        first_line = self.first_line
        indices = [0] * shapelen
        for i in range(shapelen):
            indices[i] = self.indices[i]
        done = False
        for i in range(shapelen - 1, -1, -1):
            if indices[i] < self.res_shape[i] - 1:
                if i == self.dim:
                    first_line = False
                indices[i] += 1
                offset += self.strides[i]
                break
            else:
                if i == self.dim:
                    first_line = True
                indices[i] = 0
                offset -= self.backstrides[i]
        else:
            done = True
        res = instantiate(AxisIterator)
        res.offset = offset
        res.indices = indices
        res.strides = self.strides
        res.backstrides = self.backstrides
        res.res_shape = self.res_shape
        res._done = done
        res.first_line = first_line
        res.dim = self.dim
        return res        

    def done(self):
        return self._done

# ------ other iterators that are not part of the computation frame ----------
    
class SkipLastAxisIterator(object):
    def __init__(self, arr):
        self.arr = arr
        self.indices = [0] * (len(arr.shape) - 1)
        self.done = False
        self.offset = arr.start

    def next(self):
        for i in range(len(self.arr.shape) - 2, -1, -1):
            if self.indices[i] < self.arr.shape[i] - 1:
                self.indices[i] += 1
                self.offset += self.arr.strides[i]
                break
            else:
                self.indices[i] = 0
                self.offset -= self.arr.backstrides[i]
        else:
            self.done = True
