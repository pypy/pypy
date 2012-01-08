import math

import numpypy


inf = float("inf")
e = math.e
pi = math.pi


def average(a):
    # This implements a weighted average, for now we don't implement the
    # weighting, just the average part!
    return mean(a)

def identity(n, dtype=None):
    a = numpypy.zeros((n,n), dtype=dtype)
    for i in range(n):
        a[i][i] = 1
    return a

def mean(a):
    if not hasattr(a, "mean"):
        a = numpypy.array(a)
    return a.mean()

def sum(a):
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
        a = numpypy.array(a)
    return a.sum()

def min(a):
    if not hasattr(a, "min"):
        a = numpypy.array(a)
    return a.min()

def max(a, axis=None):
    if not hasattr(a, "max"):
        a = numpypy.array(a)
    return a.max(axis)

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
        i += step
    return arr


def reshape(a, shape):
    '''reshape(a, newshape)
    Gives a new shape to an array without changing its data.

    Parameters
    ----------
    a : array_like
        Array to be reshaped.
    newshape : int or tuple of ints
        The new shape should be compatible with the original shape. If
        an integer, then the result will be a 1-D array of that length.
        One shape dimension can be -1. In this case, the value is inferred
        from the length of the array and remaining dimensions.

    Returns
    -------
    reshaped_array : ndarray
        This will be a new view object if possible; otherwise, it will
        be a copy.


    See Also
    --------
    ndarray.reshape : Equivalent method.

    Notes
    -----

    It is not always possible to change the shape of an array without
    copying the data. If you want an error to be raise if the data is copied,
    you should assign the new shape to the shape attribute of the array
'''
    if not hasattr(a, 'reshape'):
        a = numpypy.array(a)
    return a.reshape(shape)
