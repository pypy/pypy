import math

import _numpypy

def average(a):
    # This implements a weighted average, for now we don't implement the
    # weighting, just the average part!
    if not hasattr(a, "mean"):
        a = _numpypy.array(a)
    return a.mean()

def identity(n, dtype=None):
    a = _numpypy.zeros((n, n), dtype=dtype)
    for i in range(n):
        a[i][i] = 1
    return a

def eye(n, m=None, k=0, dtype=None):
    if m is None:
        m = n
    a = _numpypy.zeros((n, m), dtype=dtype)
    ni = 0
    mi = 0

    if k < 0:
        p = n + k
        ni = -k
    else:
        p = n - k
        mi = k

    while ni < n and mi < m:
        a[ni][mi] = 1
        ni += 1
        mi += 1
    return a

def arange(start, stop=None, step=1, dtype=None):
    '''arange([start], stop[, step], dtype=None)
    Generate values in the half-interval [start, stop).
    '''
    if stop is None:
        stop = start
        start = 0
    if dtype is None:
        test = _numpypy.array([start, stop, step, 0])
        dtype = test.dtype
    arr = _numpypy.zeros(int(math.ceil((stop - start) / step)), dtype=dtype)
    i = start
    for j in range(arr.size):
        arr[j] = i
        i += step
    return arr
