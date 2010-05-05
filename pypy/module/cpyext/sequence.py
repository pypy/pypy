
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, CONST_STRING, Py_ssize_t)
from pypy.module.cpyext.pyobject import PyObject, borrow_from
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.objspace.std import listobject, tupleobject


@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PySequence_Check(space, w_obj):
    """Return 1 if the object provides sequence protocol, and 0 otherwise.
    This function always succeeds."""
    return int(space.findattr(w_obj, space.wrap("__getitem__")) is not None)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PySequence_Size(space, w_obj):
    """
    Returns the number of objects in sequence o on success, and -1 on failure.
    For objects that do not provide sequence protocol, this is equivalent to the
    Python expression len(o)."""
    return space.int_w(space.len(w_obj))

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PySequence_Length(space, w_obj):
    return space.int_w(space.len(w_obj))


@cpython_api([PyObject, CONST_STRING], PyObject)
def PySequence_Fast(space, w_obj, m):
    """Returns the sequence o as a tuple, unless it is already a tuple or list, in
    which case o is returned.  Use PySequence_Fast_GET_ITEM() to access the
    members of the result.  Returns NULL on failure.  If the object is not a
    sequence, raises TypeError with m as the message text."""
    if (space.is_true(space.isinstance(w_obj, space.w_list)) or
        space.is_true(space.isinstance(w_obj, space.w_tuple))):
        return w_obj
    try:
        return space.newtuple(space.fixedview(w_obj))
    except OperationError:
        raise OperationError(space.w_TypeError, space.wrap(rffi.charp2str(m)))

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PySequence_Fast_GET_ITEM(space, w_obj, index):
    """Return the ith element of o, assuming that o was returned by
    PySequence_Fast(), o is not NULL, and that i is within bounds.
    """
    if isinstance(w_obj, listobject.W_ListObject):
        w_res = w_obj.wrappeditems[index]
    else:
        assert isinstance(w_obj, tupleobject.W_TupleObject)
        w_res = w_obj.wrappeditems[index]
    return borrow_from(w_obj, w_res)

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PySequence_Fast_GET_SIZE(space, w_obj):
    """Returns the length of o, assuming that o was returned by
    PySequence_Fast() and that o is not NULL.  The size can also be
    gotten by calling PySequence_Size() on o, but
    PySequence_Fast_GET_SIZE() is faster because it can assume o is a list
    or tuple."""
    if isinstance(w_obj, listobject.W_ListObject):
        return len(w_obj.wrappeditems)
    assert isinstance(w_obj, tupleobject.W_TupleObject)
    return len(w_obj.wrappeditems)

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PySequence_GetSlice(space, w_obj, start, end):
    """Return the slice of sequence object o between i1 and i2, or NULL on
    failure. This is the equivalent of the Python expression o[i1:i2].

    This function used an int type for i1 and i2. This might
    require changes in your code for properly supporting 64-bit systems."""
    return space.getslice(w_obj, space.wrap(start), space.wrap(end))

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PySequence_GetItem(space, w_obj, i):
    """Return the ith element of o, or NULL on failure. This is the equivalent of
    the Python expression o[i]."""
    return space.getitem(w_obj, space.wrap(i))

@cpython_api([PyObject], PyObject)
def PySequence_Tuple(space, w_obj):
    """Return a tuple object with the same contents as the arbitrary sequence o or
    NULL on failure.  If o is a tuple, a new reference will be returned,
    otherwise a tuple will be constructed with the appropriate contents.  This is
    equivalent to the Python expression tuple(o)."""
    return space.call_function(space.w_tuple, w_obj)

@cpython_api([PyObject, PyObject], PyObject)
def PySequence_Concat(space, w_o1, w_o2):
    """Return the concatenation of o1 and o2 on success, and NULL on failure.
    This is the equivalent of the Python expression o1 + o2."""
    return space.add(w_o1, w_o2)

@cpython_api([PyObject], PyObject)
def PySeqIter_New(space, w_seq):
    """Return an iterator that works with a general sequence object, seq.  The
    iteration ends when the sequence raises IndexError for the subscripting
    operation.
    """
    return space.iter(w_seq)

