
from pypy.rlib import jit
from pypy.rlib.objectmodel import instantiate

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

    def get_offset(self):
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

    def get_offset(self):
        return self.offset

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

    def get_offset(self):
        return self.offset

class ViewIterator(BaseIterator):
    def __init__(self, arr, res_shape=None):
        self.indices = [0] * len(arr.shape)
        self.offset  = arr.start
        self._done   = False
        if res_shape is not None and res_shape != arr.shape:
            self.strides = []
            self.backstrides = []
            for i in range(len(arr.shape)):
                if arr.shape[i] == 1:
                    self.strides.append(0)
                    self.backstrides.append(0)
                else:
                    self.strides.append(arr.strides[i])
                    self.backstrides.append(arr.backstrides[i])
            self.strides = [0] * (len(res_shape) - len(arr.shape)) + self.strides
            self.backstrides = [0] * (len(res_shape) - len(arr.shape)) + self.backstrides
            self.res_shape = res_shape
        else:
            self.strides = arr.strides
            self.backstrides = arr.backstrides
            self.res_shape = arr.shape


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

    def get_offset(self):
        return self.offset

class ConstantIterator(BaseIterator):
    def next(self, shapelen):
        return self

    def done(self):
        return False

    def get_offset(self):
        return 0

