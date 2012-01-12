
from pypy.rlib import jit
from pypy.rlib.objectmodel import instantiate
from pypy.module.micronumpy.strides import calculate_broadcast_strides

# Iterators for arrays
# --------------------
# all those iterators with the exception of BroadcastIterator iterate over the
# entire array in C order (the last index changes the fastest). This will
# yield all elements. Views iterate over indices and look towards strides and
# backstrides to find the correct position. Notably the offset between
# x[..., i + 1] and x[..., i] will be strides[-1]. Offset between
# x[..., k + 1, 0] and x[..., k, i_max] will be backstrides[-2] etc.

# BroadcastIterator works like that, but for indexes that don't change source
# in the original array, strides[i] == backstrides[i] == 0

class BaseIterator(object):
    def next(self, shapelen):
        raise NotImplementedError

    def done(self):
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

def view_iter_from_arr(arr):
    return ViewIterator(arr.start, arr.strides, arr.backstrides, arr.shape)

class ViewIterator(BaseIterator):
    def __init__(self, start, strides, backstrides, shape, res_shape=None):
        self.offset  = start
        self._done   = False
        if res_shape is not None and res_shape != shape:
            r = calculate_broadcast_strides(strides, backstrides,
                                            shape, res_shape)
            self.strides, self.backstrides = r
            self.res_shape = res_shape
        else:
            self.strides = strides
            self.backstrides = backstrides
            self.res_shape = shape
        self.indices = [0] * len(self.res_shape)

    @jit.unroll_safe
    def next(self, shapelen):
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

    def done(self):
        return self._done

class ConstantIterator(BaseIterator):
    def next(self, shapelen):
        return self

class AxisIterator(BaseIterator):
    """ Accept an addition argument dim
    Redorder the dimensions to iterate over dim most often.
    Set a flag at the end of each run over dim.
    """
    def __init__(self, dim, shape, strides, backstrides):
        self.shape = shape
        self.indices = [0] * len(shape)
        self._done = False
        self.axis_done = False
        self.offset = -1
        self.dim = dim
        self.strides = strides[:dim] + [0] + strides[dim:]
        self.backstrides = backstrides[:dim] + [0] + backstrides[dim:]
        self.dim_order = [dim]
        for i in range(len(shape) - 1, -1, -1):
            if i != self.dim:
                self.dim_order.append(i)

    def done(self):
        return self._done

    @jit.unroll_safe
    def next(self, shapelen):
        offset = self.offset
        done = False
        indices = [0] * shapelen
        for i in range(shapelen):
            indices[i] = self.indices[i]
        axis_done = False        
        for i in self.dim_order:
            if indices[i] < self.shape[i] - 1:
                indices[i] += 1
                break
            else:
                if i == self.dim:
                    axis_done = True
                    offset += 1
                indices[i] = 0
        else:
            done = True
        res = instantiate(AxisIterator)
        res.axis_done = axis_done
        res.strides = self.strides
        res.backstrides = self.backstrides
        res.offset = offset
        res.indices = indices
        res.shape = self.shape
        res.dim = self.dim
        res.dim_order = self.dim_order
        res._done = done
        return res

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
