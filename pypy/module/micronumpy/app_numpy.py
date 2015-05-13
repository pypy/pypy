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
        # find minimal acceptable dtype but not less than int
        dtype = _numpypy.multiarray.result_type(start, stop, step, int)
    length = math.ceil((float(stop) - start) / step)
    length = int(length)
    arr = _numpypy.multiarray.empty(length, dtype=dtype)
    i = start
    for j in xrange(arr.size):
        arr[j] = i
        i += step
    return arr
