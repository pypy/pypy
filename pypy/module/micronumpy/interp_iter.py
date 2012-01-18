
from pypy.rlib import jit
from pypy.rlib.objectmodel import instantiate
from pypy.module.micronumpy.strides import calculate_broadcast_strides,\
     calculate_slice_strides, calculate_dot_strides

class BaseTransform(object):
    pass

class ViewTransform(BaseTransform):
    def __init__(self, chunks):
        # 4-tuple specifying slicing
        self.chunks = chunks

class BroadcastTransform(BaseTransform):
    def __init__(self, res_shape):
        self.res_shape = res_shape

class DotTransform(BaseTransform):
    def __init__(self, res_shape, skip_dims):
        self.res_shape = res_shape
        self.skip_dims = skip_dims

class BaseIterator(object):
    def next(self, shapelen):
        raise NotImplementedError

    def done(self):
        raise NotImplementedError

    def apply_transformations(self, arr, transformations):
        v = self
        for transform in transformations:
            v = v.transform(arr, transform)
        return v

    def transform(self, arr, t):
        raise NotImplementedError

class ArrayIterator(BaseIterator):
    def __init__(self, size):
        self.offset = 0
        self.size = size

    def next(self, shapelen):
        arr = instantiate(ArrayIterator)
        arr.size = self.size
        arr.offset = self.offset + 1
        return arr

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
                                        self.backstrides, t.chunks)
            return ViewIterator(r[1], r[2], r[3], r[0])
        elif isinstance(t, DotTransform):
            r = calculate_dot_strides(self.strides, self.backstrides,
                                     t.res_shape, t.skip_dims)
            return ViewIterator(self.offset, r[0], r[1], t.res_shape)

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
