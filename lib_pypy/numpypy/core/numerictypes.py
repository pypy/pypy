from _numpypy.numerictypes import *
from _numpypy.multiarray import dtype

def issubclass_(arg1, arg2):
    """
    Determine if a class is a subclass of a second class.

    `issubclass_` is equivalent to the Python built-in ``issubclass``,
    except that it returns False instead of raising a TypeError is one
    of the arguments is not a class.

    Parameters
    ----------
    arg1 : class
        Input class. True is returned if `arg1` is a subclass of `arg2`.
    arg2 : class or tuple of classes.
        Input class. If a tuple of classes, True is returned if `arg1` is a
        subclass of any of the tuple elements.

    Returns
    -------
    out : bool
        Whether `arg1` is a subclass of `arg2` or not.

    See Also
    --------
    issubsctype, issubdtype, issctype

    Examples
    --------
    >>> np.issubclass_(np.int32, np.int)
    True
    >>> np.issubclass_(np.int32, np.float)
    False

    """
    try:
        return issubclass(arg1, arg2)
    except TypeError:
        return False

def issubdtype(arg1, arg2):
    """
    Returns True if first argument is a typecode lower/equal in type hierarchy.

    Parameters
    ----------
    arg1, arg2 : dtype_like
        dtype or string representing a typecode.

    Returns
    -------
    out : bool

    See Also
    --------
    issubsctype, issubclass_
    numpy.core.numerictypes : Overview of numpy type hierarchy.

    Examples
    --------
    >>> np.issubdtype('S1', str)
    True
    >>> np.issubdtype(np.float64, np.float32)
    False

    """
    if issubclass_(arg2, generic):
        return issubclass(dtype(arg1).type, arg2)
    mro = dtype(arg2).type.mro()
    if len(mro) > 1:
        val = mro[1]
    else:
        val = mro[0]
    return issubclass(dtype(arg1).type, val)
