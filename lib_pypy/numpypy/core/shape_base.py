from numeric import array, asanyarray, newaxis

def atleast_1d(*arys):
    """
    Convert inputs to arrays with at least one dimension.

    Scalar inputs are converted to 1-dimensional arrays, whilst
    higher-dimensional inputs are preserved.

    Parameters
    ----------
    arys1, arys2, ... : array_like
        One or more input arrays.

    Returns
    -------
    ret : ndarray
        An array, or sequence of arrays, each with ``a.ndim >= 1``.
        Copies are made only if necessary.

    See Also
    --------
    atleast_2d, atleast_3d

    Examples
    --------
    >>> np.atleast_1d(1.0)
    array([ 1.])

    >>> x = np.arange(9.0).reshape(3,3)
    >>> np.atleast_1d(x)
    array([[ 0.,  1.,  2.],
           [ 3.,  4.,  5.],
           [ 6.,  7.,  8.]])
    >>> np.atleast_1d(x) is x
    True

    >>> np.atleast_1d(1, [3, 4])
    [array([1]), array([3, 4])]

    """
    res = []
    for ary in arys:
        ary = asanyarray(ary)
        if len(ary.shape) == 0 :
            result = ary.reshape(1)
        else :
            result = ary
        res.append(result)
    if len(res) == 1:
        return res[0]
    else:
        return res


def atleast_2d(*arys):
    """
    View inputs as arrays with at least two dimensions.

    Parameters
    ----------
    arys1, arys2, ... : array_like
        One or more array-like sequences.  Non-array inputs are converted
        to arrays.  Arrays that already have two or more dimensions are
        preserved.

    Returns
    -------
    res, res2, ... : ndarray
        An array, or tuple of arrays, each with ``a.ndim >= 2``.
        Copies are avoided where possible, and views with two or more
        dimensions are returned.

    See Also
    --------
    atleast_1d, atleast_3d

    Examples
    --------
    >>> np.atleast_2d(3.0)
    array([[ 3.]])

    >>> x = np.arange(3.0)
    >>> np.atleast_2d(x)
    array([[ 0.,  1.,  2.]])
    >>> np.atleast_2d(x).base is x
    True

    >>> np.atleast_2d(1, [1, 2], [[1, 2]])
    [array([[1]]), array([[1, 2]]), array([[1, 2]])]

    """
    res = []
    for ary in arys:
        ary = asanyarray(ary)
        if len(ary.shape) == 0 :
            result = ary.reshape(1, 1)
        elif len(ary.shape) == 1 :
            result = ary[newaxis, :]
        else :
            result = ary
        res.append(result)
    if len(res) == 1:
        return res[0]
    else:
        return res
