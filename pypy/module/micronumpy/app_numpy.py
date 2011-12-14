import math

import numpypy


inf = float("inf")
e = math.e
pi = math.pi


def average(a):
    # This implements a weighted average, for now we don't implement the
    # weighting, just the average part!
    return mean(a)


def mean(a):
    if not hasattr(a, "mean"):
        a = numpypy.array(a)
    return a.mean()

def sum(a):
    if not hasattr(a, "sum"):
        a = numpypy.array(a)
    return a.sum()

def min(a):
    if not hasattr(a, "min"):
        a = numpypy.array(a)
    return a.min()

def max(a):
    if not hasattr(a, "max"):
        a = numpypy.array(a)
    return a.max()

def concatenate(array_iter, axis=0):
    arrays = []
    shape = None
    for a in array_iter:
        if not hasattr(a, 'shape'):
            a = numpypy.array(a)
        arrays.append(a)
        if len(a.shape) < axis + 1:
            raise ValueError("bad axis argument")
        if shape is None:
            shape = list(a.shape)
        else:
            for i, axis_size in enumerate(a.shape):
                if len(a.shape) != len(shape) or (i != axis and axis_size != shape[i]):
                    raise ValueError("array dimensions must agree except for axis being concatenated")
                elif i == axis:
                    shape[i] += axis_size
    
    if len(arrays) == 0:
        raise ValueError("concatenation of zero-length sequences is impossible")
    
    out_array = numpypy.zeros(shape)
    slicing_index = [slice(None)] * len(shape)
    axis_ptr = 0
    for a in arrays:
        slicing_index[axis] = slice(axis_ptr, axis_ptr + a.shape[axis])
        out_array[tuple(slicing_index)] = a
        axis_ptr += a.shape[axis]
    
    return out_array
    
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
