from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import oefmt
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, CONST_STRING, Py_ssize_t)
from pypy.module.cpyext.pyobject import (
    PyObject, hack_for_result_often_existing_obj)


@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL, abi3=True)
def PyMapping_Check(space, w_obj):
    """Return 1 if the object provides mapping protocol, and 0 otherwise.  This
    function always succeeds."""
    if w_obj is None:
        return 0
    # Matches CPython's tp_as_mapping->mp_subscript check: any type with
    # __getitem__ counts, including sequences like list.
    return int(space.lookup(w_obj, '__getitem__') is not None)

@cpython_api([PyObject], Py_ssize_t, error=-1, abi3=True)
def PyMapping_Size(space, w_obj):
    if w_obj is None:
        raise oefmt(space.w_SystemError, "null argument to internal routine")
    return space.len_w(w_obj)

@cpython_api([PyObject], Py_ssize_t, error=-1, abi3=True)
def PyMapping_Length(space, w_obj):
    if w_obj is None:
        raise oefmt(space.w_SystemError, "null argument to internal routine")
    return space.len_w(w_obj)

@cpython_api([PyObject], PyObject, abi3=True)
def PyMapping_Keys(space, w_obj):
    """On success, return a list of the keys in object o.  On failure, return NULL.
    This is equivalent to the Python expression o.keys()."""
    if w_obj is None:
        raise oefmt(space.w_SystemError, "null argument to internal routine")
    return space.call_function(space.w_list,
                               space.call_method(w_obj, "keys"))

@cpython_api([PyObject], PyObject, abi3=True)
def PyMapping_Values(space, w_obj):
    """On success, return a list of the values in object o.  On failure, return
    NULL. This is equivalent to the Python expression o.values()."""
    if w_obj is None:
        raise oefmt(space.w_SystemError, "null argument to internal routine")
    return space.call_function(space.w_list,
                               space.call_method(w_obj, "values"))

@cpython_api([PyObject], PyObject, abi3=True)
def PyMapping_Items(space, w_obj):
    """On success, return a list of the items in object o, where each item is a tuple
    containing a key-value pair.  On failure, return NULL. This is equivalent to
    the Python expression o.items()."""
    if w_obj is None:
        raise oefmt(space.w_SystemError, "null argument to internal routine")
    return space.call_function(space.w_list,
                               space.call_method(w_obj, "items"))

@cpython_api([PyObject, CONST_STRING], PyObject, result_is_ll=True, abi3=True)
def PyMapping_GetItemString(space, w_obj, key):
    """Return element of o corresponding to the object key or NULL on failure.
    This is the equivalent of the Python expression o[key]."""
    if w_obj is None or not key:
        raise oefmt(space.w_SystemError, "null argument to internal routine")
    w_bytes = space.newbytes(rffi.charp2str(key))
    w_key = space.call_method(w_bytes, 'decode', space.newtext("utf-8"))
    w_res = space.getitem(w_obj, w_key)
    return hack_for_result_often_existing_obj(space, w_res)

@cpython_api([PyObject, CONST_STRING, PyObject], rffi.INT_real, error=-1, abi3=True)
def PyMapping_SetItemString(space, w_obj, key, w_value):
    """Map the object key to the value v in object o. Returns -1 on failure.
    This is the equivalent of the Python statement o[key] = v."""
    if w_obj is None or not key or w_value is None:
        raise oefmt(space.w_SystemError, "null argument to internal routine")
    w_bytes = space.newbytes(rffi.charp2str(key))
    w_key = space.call_method(w_bytes, 'decode', space.newtext("utf-8"))
    space.setitem(w_obj, w_key, w_value)
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=CANNOT_FAIL, abi3=True)
def PyMapping_HasKey(space, w_obj, w_key):
    """Return 1 if the mapping object has the key key and 0 otherwise.
    This is equivalent to o[key], returning True on success and False
    on an exception.  This function always succeeds."""
    if w_obj is None or w_key is None:
        return 0
    try:
        space.getitem(w_obj, w_key)
        return 1
    except:
        return 0

@cpython_api([PyObject, CONST_STRING], rffi.INT_real, error=CANNOT_FAIL, abi3=True)
def PyMapping_HasKeyString(space, w_obj, key):
    """Return 1 if the mapping object has the key key and 0 otherwise.
    This is equivalent to o[key], returning True on success and False
    on an exception.  This function always succeeds."""
    if w_obj is None or not key:
        return 0
    try:
        w_bytes = space.newbytes(rffi.charp2str(key))
        w_key = space.call_method(w_bytes, 'decode', space.newtext("utf-8"))
        space.getitem(w_obj, w_key)
        return 1
    except:
        return 0
