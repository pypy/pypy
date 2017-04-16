
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, CANNOT_FAIL, Py_ssize_t,
                                    build_type_checkers)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.cpyext.pyobject import Py_DecRef, PyObject, make_ref
from pypy.objspace.std.listobject import W_ListObject
from pypy.interpreter.error import oefmt


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

@cpython_api([rffi.VOIDP, Py_ssize_t, PyObject], PyObject, error=CANNOT_FAIL,
             result_borrowed=True)
def PyList_SET_ITEM(space, w_list, index, w_item):
    """Macro form of PyList_SetItem() without error checking. This is normally
    only used to fill in new lists where there is no previous content.

    This function "steals" a reference to item, and, unlike PyList_SetItem(),
    does not discard a reference to any item that it being replaced; any
    reference in list at position i will be leaked.
    """
    assert isinstance(w_list, W_ListObject)
    assert 0 <= index < w_list.length()
    # Deliberately leak, so that it can be safely decref'd.
    make_ref(space, w_list.getitem(index))
    Py_DecRef(space, w_item)
    w_list.setitem(index, w_item)
    return w_item


@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyList_SetItem(space, w_list, index, w_item):
    """Set the item at index index in list to item.  Return 0 on success
    or -1 on failure.
    
    This function "steals" a reference to item and discards a reference to
    an item already in the list at the affected position.
    """
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    if index < 0 or index >= w_list.length():
        raise oefmt(space.w_IndexError, "list assignment index out of range")
    #Py_DecRef(space, w_item)
    w_list.setitem(index, w_item)
    return 0

@cpython_api([PyObject, Py_ssize_t], PyObject, result_borrowed=True)
def PyList_GetItem(space, w_list, index):
    """Return the object at position pos in the list pointed to by p.  The
    position must be positive, indexing from the end of the list is not
    supported.  If pos is out of bounds, return NULL and set an
    IndexError exception."""
    from pypy.module.cpyext.sequence import CPyListStrategy
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    if index < 0 or index >= w_list.length():
        raise oefmt(space.w_IndexError, "list index out of range")
    cpy_strategy = space.fromcache(CPyListStrategy)
    if w_list.strategy is not cpy_strategy:
        w_list.ensure_object_strategy() # make sure we can return a borrowed obj
    w_res = w_list.getitem(index)
    return w_res     # borrowed ref


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
    space.call_method(space.w_list, "insert", w_list, space.newint(index), w_item)
    return 0

@cpython_api([rffi.VOIDP], Py_ssize_t, error=CANNOT_FAIL)
def PyList_GET_SIZE(space, w_obj):
    """Macro form of PyList_Size() without error checking.
    """
    return space.len_w(w_obj)


@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyList_Size(space, ref):
    """Return the length of the list object in list; this is equivalent to
    len(list) on a list object.
    """
    if not PyList_Check(space, ref):
        raise oefmt(space.w_TypeError, "expected list object")
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
    space.call_method(space.w_list, "sort", w_list)
    return 0

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PyList_Reverse(space, w_list):
    """Reverse the items of list in place.  Return 0 on success, -1 on
    failure.  This is the equivalent of list.reverse()."""
    if not isinstance(w_list, W_ListObject):
        PyErr_BadInternalCall(space)
    space.call_method(space.w_list, "reverse", w_list)
    return 0

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyList_GetSlice(space, w_list, low, high):
    """Return a list of the objects in list containing the objects between low
    and high.  Return NULL and set an exception if unsuccessful.  Analogous
    to list[low:high].  Negative indices, as when slicing from Python, are not
    supported."""
    w_start = space.newint(low)
    w_stop = space.newint(high)
    return space.getslice(w_list, w_start, w_stop)

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyList_SetSlice(space, w_list, low, high, w_sequence):
    """Set the slice of list between low and high to the contents of
    itemlist.  Analogous to list[low:high] = itemlist. The itemlist may
    be NULL, indicating the assignment of an empty list (slice deletion).
    Return 0 on success, -1 on failure.  Negative indices, as when
    slicing from Python, are not supported."""
    w_start = space.newint(low)
    w_stop = space.newint(high)
    if w_sequence:
        space.setslice(w_list, w_start, w_stop, w_sequence)
    else:
        space.delslice(w_list, w_start, w_stop)
    return 0
