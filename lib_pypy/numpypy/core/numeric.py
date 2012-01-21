
from _numpypy import array

def asanyarray(a, dtype=None, order=None, maskna=None, ownmaskna=False):
    """
    Convert the input to an ndarray, but pass ndarray subclasses through.

    Parameters
    ----------
    a : array_like
        Input data, in any form that can be converted to an array.  This
        includes scalars, lists, lists of tuples, tuples, tuples of tuples,
        tuples of lists, and ndarrays.
    dtype : data-type, optional
        By default, the data-type is inferred from the input data.
    order : {'C', 'F'}, optional
        Whether to use row-major ('C') or column-major ('F') memory
        representation.  Defaults to 'C'.
   maskna : bool or None, optional
        If this is set to True, it forces the array to have an NA mask.
        If this is set to False, it forces the array to not have an NA
        mask.
    ownmaskna : bool, optional
        If this is set to True, forces the array to have a mask which
        it owns.

    Returns
    -------
    out : ndarray or an ndarray subclass
        Array interpretation of `a`.  If `a` is an ndarray or a subclass
        of ndarray, it is returned as-is and no copy is performed.

    See Also
    --------
    asarray : Similar function which always returns ndarrays.
    ascontiguousarray : Convert input to a contiguous array.
    asfarray : Convert input to a floating point ndarray.
    asfortranarray : Convert input to an ndarray with column-major
                     memory order.
    asarray_chkfinite : Similar function which checks input for NaNs and
                        Infs.
    fromiter : Create an array from an iterator.
    fromfunction : Construct an array by executing a function on grid
                   positions.

    Examples
    --------
    Convert a list into an array:

    >>> a = [1, 2]
    >>> np.asanyarray(a)
    array([1, 2])

    Instances of `ndarray` subclasses are passed through as-is:

    >>> a = np.matrix([1, 2])
    >>> np.asanyarray(a) is a
    True

    """
    return array(a, dtype, copy=False, order=order, subok=True,
                                maskna=maskna, ownmaskna=ownmaskna)
