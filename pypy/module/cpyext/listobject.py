
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, CANNOT_FAIL, Py_ssize_t,
                                    build_type_checkers)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.cpyext.pyobject import Py_DecRef, PyObject, borrow_from
from pypy.objspace.std.listobject import W_ListObject
from pypy.interpreter.error import OperationError


PyList_Check, PyList_CheckExact = build_type_checkers("List")

@cpython_api([Py_ssize_t], PyObject)
def PyList_New(space, len):
    """Return a new list of length len on success, or NULL on failure.
    
    If length is greater than zero, the returned list object's items are
    set to NULL.  Thus you cannot use abstract API functions such as
    PySequence_SetItem()  or expose the object to Python code before
    setting all items to a real object with PyList_SetItem().
    """
    return space.newlist([None] * len)

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyList_SetItem(space, w_list, index, w_item):
    """Set the item at index index in list to item.  Return 0 on success
    or -1 on failure.
    
    This function "steals" a reference to item and discards a reference to
    an item already in the list at the affected position.
    """
    Py_DecRef(space, w_item)
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    if index < 0 or index >= w_list.length():
        raise OperationError(space.w_IndexError, space.wrap(
            "list assignment index out of range"))
    w_list.setitem(index, w_item)
    return 0

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PyList_GetItem(space, w_list, index):
    """Return the object at position pos in the list pointed to by p.  The
    position must be positive, indexing from the end of the list is not
    supported.  If pos is out of bounds, return NULL and set an
    IndexError exception."""
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    wrappeditems = w_list.getitems()
    if index < 0 or index >= len(wrappeditems):
        raise OperationError(space.w_IndexError, space.wrap(
            "list index out of range"))
    return borrow_from(w_list, wrappeditems[index])


@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyList_Append(space, w_list, w_item):
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    w_list.append(w_item)
    return 0

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyList_Insert(space, w_list, index, w_item):
    """Insert the item item into list list in front of index index.  Return
    0 if successful; return -1 and set an exception if unsuccessful.
    Analogous to list.insert(index, item)."""
    space.call_method(w_list, "insert", space.wrap(index), w_item)
    return 0

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyList_GET_SIZE(space, w_list):
    """Macro form of PyList_Size() without error checking.
    """
    assert isinstance(w_list, W_ListObject)
    return w_list.length()


@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyList_Size(space, ref):
    """Return the length of the list object in list; this is equivalent to
    len(list) on a list object.
    """
    if not PyList_Check(space, ref):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected list object"))
    return PyList_GET_SIZE(space, ref)

@cpython_api([PyObject], PyObject)
def PyList_AsTuple(space, w_list):
    """Return a new tuple object containing the contents of list; equivalent to
    tuple(list)."""
    return space.call_function(space.w_tuple, w_list)

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyList_Sort(space, w_list):
    """Sort the items of list in place.  Return 0 on success, -1 on
    failure.  This is equivalent to list.sort()."""
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    space.call_method(w_list, "sort")
    return 0

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyList_Reverse(space, w_list):
    """Reverse the items of list in place.  Return 0 on success, -1 on
    failure.  This is the equivalent of list.reverse()."""
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    space.call_method(w_list, "reverse")
    return 0

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyList_SetSlice(space, w_list, low, high, w_sequence):
    """Set the slice of list between low and high to the contents of
    itemlist.  Analogous to list[low:high] = itemlist. The itemlist may
    be NULL, indicating the assignment of an empty list (slice deletion).
    Return 0 on success, -1 on failure.  Negative indices, as when
    slicing from Python, are not supported."""
    w_start = space.wrap(low)
    w_stop = space.wrap(high)
    if w_sequence:
        space.setslice(w_list, w_start, w_stop, w_sequence)
    else:
        space.delslice(w_list, w_start, w_stop)
    return 0
