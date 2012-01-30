import math

import _numpypy


inf = float("inf")
e = math.e
pi = math.pi


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

def sum(a,axis=None):
    '''sum(a, axis=None)
    Sum of array elements over a given axis.

    Parameters
    ----------
    a : array_like
        Elements to sum.
    axis : integer, optional
        Axis over which the sum is taken. By default `axis` is None,
        and all elements are summed.

    Returns
    -------
    sum_along_axis : ndarray
        An array with the same shape as `a`, with the specified
        axis removed.   If `a` is a 0-d array, or if `axis` is None, a scalar
        is returned.  If an output array is specified, a reference to
        `out` is returned.

    See Also
    --------
    ndarray.sum : Equivalent method.
    '''
    # TODO: add to doc (once it's implemented): cumsum : Cumulative sum of array elements.
    if not hasattr(a, "sum"):
        a = _numpypy.array(a)
    return a.sum(axis)

def min(a, axis=None):
    if not hasattr(a, "min"):
        a = _numpypy.array(a)
    return a.min(axis)

def max(a, axis=None):
    if not hasattr(a, "max"):
        a = _numpypy.array(a)
    return a.max(axis)
    
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
