from pypy.interpreter.error import oefmt
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, Py_ssize_t, CANNOT_FAIL,
                                    build_type_checkers)
from pypy.module.cpyext.pyobject import (PyObject, PyObjectP, Py_DecRef,
    make_ref, from_ref)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.objspace.std.setobject import W_SetObject, W_FrozensetObject, newset


PySet_Check, PySet_CheckExact = build_type_checkers("Set")
PyFrozenSet_Check, PyFrozenSet_CheckExact = build_type_checkers("FrozenSet")

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyAnySet_Check(space, w_obj):
    """Return true if obj is a set object, a frozenset object, or an
    instance of a subtype."""
    return (space.isinstance_w(w_obj, space.gettypefor(W_SetObject)) or
            space.isinstance_w(w_obj, space.gettypefor(W_FrozensetObject)))

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyAnySet_CheckExact(space, w_obj):
    """Return true if obj is a set object or a frozenset object but
    not an instance of a subtype."""
    w_obj_type = space.type(w_obj)
    return (space.is_w(w_obj_type, space.gettypefor(W_SetObject)) or 
            space.is_w(w_obj_type, space.gettypefor(W_FrozensetObject)))

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
    space.call_method(space.w_set, 'add', w_s, w_obj)
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
    space.call_method(space.w_set, 'discard', w_s, w_obj)
    return 0


@cpython_api([PyObject], PyObject)
def PySet_Pop(space, w_set):
    """Return a new reference to an arbitrary object in the set, and removes the
    object from the set.  Return NULL on failure.  Raise KeyError if the
    set is empty. Raise a SystemError if set is an not an instance of
    set or its subtype."""
    return space.call_method(space.w_set, "pop", w_set)

@cpython_api([PyObject], rffi.INT_real, error=-1)
def PySet_Clear(space, w_set):
    """Empty an existing set of all elements."""
    space.call_method(space.w_set, 'clear', w_set)
    return 0

@cpython_api([rffi.VOIDP], Py_ssize_t, error=CANNOT_FAIL)
def PySet_GET_SIZE(space, w_s):
    """Macro form of PySet_Size() without error checking."""
    return space.int_w(space.len(w_s))

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PySet_Size(space, ref):
    """Return the length of a set or frozenset object. Equivalent to
    len(anyset).  Raises a PyExc_SystemError if anyset is not a set, frozenset,
    or an instance of a subtype."""
    if not PyAnySet_Check(space, ref):
        raise oefmt(space.w_TypeError, "expected set object")
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

@cpython_api([PyObject], PyObject)
def PyFrozenSet_New(space, w_iterable):
    """Return a new frozenset containing objects returned by the iterable.
    The iterable may be NULL to create a new empty frozenset.  Return the new
    set on success or NULL on failure.  Raise TypeError if iterable is
    not actually iterable.

    Now guaranteed to return a brand-new frozenset.  Formerly,
    frozensets of zero-length were a singleton.  This got in the way of
    building-up new frozensets with PySet_Add()."""
    if w_iterable is None:
        return space.call_function(space.w_frozenset)
    else:
        return space.call_function(space.w_frozenset, w_iterable)


