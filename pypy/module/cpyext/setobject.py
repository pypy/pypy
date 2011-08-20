from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, Py_ssize_t, CANNOT_FAIL,
                                    build_type_checkers)
from pypy.module.cpyext.pyobject import (PyObject, PyObjectP, Py_DecRef,
    borrow_from, make_ref, from_ref)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.objspace.std.setobject import W_SetObject, newset
from pypy.objspace.std.smalltupleobject import W_SmallTupleObject


PySet_Check, PySet_CheckExact = build_type_checkers("Set")


@cpython_api([PyObject], PyObject)
def PySet_New(space, w_iterable):
    """Return a new set containing objects returned by the iterable.  The
    iterable may be NULL to create a new empty set.  Return the new set on
    success or NULL on failure.  Raise TypeError if iterable is not
    actually iterable.  The constructor is also useful for copying a set
    (c=set(s))."""
    if w_iterable is None:
        return space.call_function(space.w_set)
    else:
        return space.call_function(space.w_set, w_iterable)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PySet_Add(space, w_s, w_obj):
    """Add key to a set instance.  Does not apply to frozenset
    instances.  Return 0 on success or -1 on failure. Raise a TypeError if
    the key is unhashable. Raise a MemoryError if there is no room to grow.
    Raise a SystemError if set is an not an instance of set or its
    subtype.

    Now works with instances of frozenset or its subtypes.
    Like PyTuple_SetItem() in that it can be used to fill-in the
    values of brand new frozensets before they are exposed to other code."""
    if not PySet_Check(space, w_s):
        PyErr_BadInternalCall(space)
    space.call_method(w_s, 'add', w_obj)
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PySet_Discard(space, w_s, w_obj):
    """Return 1 if found and removed, 0 if not found (no action taken), and -1 if an
    error is encountered.  Does not raise KeyError for missing keys.  Raise a
    TypeError if the key is unhashable.  Unlike the Python discard()
    method, this function does not automatically convert unhashable sets into
    temporary frozensets. Raise PyExc_SystemError if set is an not an
    instance of set or its subtype."""
    if not PySet_Check(space, w_s):
        PyErr_BadInternalCall(space)
    space.call_method(w_s, 'discard', w_obj)
    return 0


@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PySet_GET_SIZE(space, w_s):
    """Macro form of PySet_Size() without error checking."""
    return space.int_w(space.len(w_s))

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PySet_Size(space, ref):
    """Return the length of a set or frozenset object. Equivalent to
    len(anyset).  Raises a PyExc_SystemError if anyset is not a set, frozenset,
    or an instance of a subtype."""
    if not PySet_Check(space, ref):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected set object"))
    return PySet_GET_SIZE(space, ref)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PySet_Contains(space, w_obj, w_key):
    """Return 1 if found, 0 if not found, and -1 if an error is encountered.  Unlike
    the Python __contains__() method, this function does not automatically
    convert unhashable sets into temporary frozensets.  Raise a TypeError if
    the key is unhashable. Raise PyExc_SystemError if anyset is not a
    set, frozenset, or an instance of a subtype."""
    w_res = space.contains(w_obj, w_key)
    return space.int_w(w_res)
