# Array methods which are called by the both the C-code for the method
# and the Python code for the NumPy-namespace function

import _numpypy as mu
um = mu
#from numpypy.core import umath as um
from numpypy.core.numeric import asanyarray

def _amax(a, axis=None, out=None, skipna=False, keepdims=False):
    return um.maximum.reduce(a, axis=axis,
                            out=out, skipna=skipna, keepdims=keepdims)

def _amin(a, axis=None, out=None, skipna=False, keepdims=False):
    return um.minimum.reduce(a, axis=axis,
                            out=out, skipna=skipna, keepdims=keepdims)

def _sum(a, axis=None, dtype=None, out=None, skipna=False, keepdims=False):
    return um.add.reduce(a, axis=axis, dtype=dtype,
                            out=out, skipna=skipna, keepdims=keepdims)

def _prod(a, axis=None, dtype=None, out=None, skipna=False, keepdims=False):
    return um.multiply.reduce(a, axis=axis, dtype=dtype,
                            out=out, skipna=skipna, keepdims=keepdims)

def _mean(a, axis=None, dtype=None, out=None, skipna=False, keepdims=False):
    arr = asanyarray(a)

    # Upgrade bool, unsigned int, and int to float64
    if dtype is None and arr.dtype.kind in ['b','u','i']:
        ret = um.add.reduce(arr, axis=axis, dtype='f8',
                            out=out, skipna=skipna, keepdims=keepdims)
    else:
        ret = um.add.reduce(arr, axis=axis, dtype=dtype,
                            out=out, skipna=skipna, keepdims=keepdims)
    rcount = mu.count_reduce_items(arr, axis=axis,
                            skipna=skipna, keepdims=keepdims)
    if isinstance(ret, mu.ndarray):
        ret = um.true_divide(ret, rcount,
                        out=ret, casting='unsafe', subok=False)
    else:
        ret = ret / float(rcount)
    return ret

def _var(a, axis=None, dtype=None, out=None, ddof=0,
                            skipna=False, keepdims=False):
    arr = asanyarray(a)

    # First compute the mean, saving 'rcount' for reuse later
    if dtype is None and arr.dtype.kind in ['b','u','i']:
        arrmean = um.add.reduce(arr, axis=axis, dtype='f8',
                            skipna=skipna, keepdims=True)
    else:
        arrmean = um.add.reduce(arr, axis=axis, dtype=dtype,
                            skipna=skipna, keepdims=True)
    rcount = mu.count_reduce_items(arr, axis=axis,
                            skipna=skipna, keepdims=True)
    if isinstance(arrmean, mu.ndarray):
        arrmean2 = um.true_divide(arrmean, rcount,
                                  casting='unsafe', subok=False)
    else:
        arrmean2 = arrmean / float(rcount)

    # arr - arrmean
    x = arr - arrmean2

    # (arr - arrmean) ** 2
    if arr.dtype.kind == 'c':
        y = um.multiply(x, um.conjugate(x)).real
    else:
        y = um.multiply(x, x)

    # add.reduce((arr - arrmean) ** 2, axis)
    ret = um.add.reduce(y, axis=axis, dtype=dtype, out=out,
                        skipna=skipna, keepdims=keepdims)

    # add.reduce((arr - arrmean) ** 2, axis) / (n - ddof)
    if not keepdims and isinstance(rcount, mu.ndarray):
        rcount = rcount.squeeze(axis=axis)
    rcount -= ddof
    if isinstance(ret, mu.ndarray):
        ret = um.true_divide(ret, rcount,
                        out=ret, casting='unsafe', subok=False)
    else:
        ret = ret / float(rcount)

    return ret

def _std(a, axis=None, dtype=None, out=None, ddof=0,
                            skipna=False, keepdims=False):
    ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
                                skipna=skipna, keepdims=keepdims)

    if isinstance(ret, mu.ndarray):
        ret = um.sqrt(ret, out=ret)
    else:
        ret = um.sqrt(ret)

    return ret
