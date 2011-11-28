import math

import numpypy


inf = float("inf")
e = math.e


def average(a):
    # This implements a weighted average, for now we don't implement the
    # weighting, just the average part!
    return mean(a)


def mean(a):
    if not hasattr(a, "mean"):
        a = numpypy.array(a)
    return a.mean()


def arange(start, stop=None, step=1, dtype=None):
    '''arange([start], stop[, step], dtype=None)
    Generate values in the half-interval [start, stop).
    '''
    if stop is None:
        stop = start
        start = 0
    if dtype is None:
        test = numpypy.array([start, stop, step, 0])
        dtype = test.dtype
    arr = numpypy.zeros(int(math.ceil((stop - start) / step)), dtype=dtype)
    i = start
    for j in range(arr.size):
        arr[j] = i
        j += 1
        i += step
    return arr
