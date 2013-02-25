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
    arr = _numpypy.multiarray.zeros(int(math.ceil((stop - start) / step)), dtype=dtype)
    i = start
    for j in range(arr.size):
        arr[j] = i
        i += step
    return arr
