from __future__ import absolute_import

import math

import _numpypy

def arange(start, stop=None, step=1, dtype=None):
    '''arange([start], stop[, step], dtype=None)
    Generate values in the half-interval [start, stop).
    '''
    if stop is None:
        stop = start
        start = 0
    if dtype is None:
        test = _numpypy.multiarray.array([start, stop, step, 0])
        dtype = test.dtype
    length = math.ceil((float(stop) - start) / step)
    length = int(length)
    arr = _numpypy.multiarray.zeros(length, dtype=dtype)
    i = start
    for j in range(arr.size):
        arr[j] = i
        i += step
    return arr

# How to call this from descr_searchsorted??
def searchsort(space, arr, v, side, result):
    def left_find_index(a, val):
        imin = 0
        imax = a.size
        while imin < imax:
            imid = imin + ((imax - imin) >> 1)
            if a[imid] <= val:
                imin = imid +1
            else:
                imax = imid
        return imin
    def right_find_index(a, val):
        imin = 0
        imax = a.size
        while imin < imax:
            imid = imin + ((imax - imin) >> 1)
            if a[imid] < val:
                imin = imid +1
            else:
                imax = imid
        return imin
    if side == 'l':
        func = left_find_index
    else:
        func = right_find_index
    for i in range(v.get_size()):
        result[i] = func(self, v[i])
    return result

