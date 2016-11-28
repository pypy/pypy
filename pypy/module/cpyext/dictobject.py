from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, build_type_checkers, Py_ssize_t,
    Py_ssize_tP, CONST_STRING)
from pypy.module.cpyext.pyobject import PyObject, PyObjectP, as_pyobj
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.cpyext.dictproxyobject import W_DictProxyObject
from pypy.interpreter.error import OperationError

@cpython_api([], PyObject)
def PyDict_New(space):
    return space.newdict()

PyDict_Check, PyDict_CheckExact = build_type_checkers("Dict")

@cpython_api([PyObject, PyObject], PyObject, error=CANNOT_FAIL,
             result_borrowed=True)
def PyDict_GetItem(space, w_dict, w_key):
    try:
        w_res = space.getitem(w_dict, w_key)
    except:
        return None
    # NOTE: this works so far because all our dict strategies store
    # *values* as full objects, which stay alive as long as the dict is
    # alive and not modified.  So we can return a borrowed ref.
    # XXX this is wrong with IntMutableCell.  Hope it works...
    return w_res

@cpython_api([PyObject, PyObject, PyObject], rffi.INT_real, error=-1)
def PyDict_SetItem(space, w_dict, w_key, w_obj):
    if PyDict_Check(space, w_dict):
        space.setitem(w_dict, w_key, w_obj)
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyDict_DelItem(space, w_dict, w_key):
    if PyDict_Check(space, w_dict):
        space.delitem(w_dict, w_key)
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, CONST_STRING, PyObject], rffi.INT_real, error=-1)
def PyDict_SetItemString(space, w_dict, key_ptr, w_obj):
    if PyDict_Check(space, w_dict):
        key = rffi.charp2str(key_ptr)
        space.setitem_str(w_dict, key, w_obj)
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject, CONST_STRING], PyObject, error=CANNOT_FAIL,
             result_borrowed=True)
def PyDict_GetItemString(space, w_dict, key):
    """This is the same as PyDict_GetItem(), but key is specified as a
    char*, rather than a PyObject*."""
    try:
        w_res = space.finditem_str(w_dict, rffi.charp2str(key))
    except:
        w_res = None
    # NOTE: this works so far because all our dict strategies store
    # *values* as full objects, which stay alive as long as the dict is
    # alive and not modified.  So we can return a borrowed ref.
    # XXX this is wrong with IntMutableCell.  Hope it works...
    return w_res

@cpython_api([PyObject, CONST_STRING], rffi.INT_real, error=-1)
def PyDict_DelItemString(space, w_dict, key_ptr):
    """Remove the entry in dictionary p which has a key specified by the string
    key.  Return 0 on success or -1 on failure."""
    if PyDict_Check(space, w_dict):
        key = rffi.charp2str(key_ptr)
        # our dicts dont have a standardized interface, so we need
        # to go through the space
        space.delitem(w_dict, space.wrap(key))
        return 0
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyDict_Size(space, w_obj):
    """
    Return the number of items in the dictionary.  This is equivalent to
    len(p) on a dictionary."""
    return space.len_w(w_obj)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyDict_Contains(space, w_obj, w_value):
    """Determine if dictionary p contains key.  If an item in p is matches
    key, return 1, otherwise return 0.  On error, return -1.
    This is equivalent to the Python expression key in p.
    """
    w_res = space.contains(w_obj, w_value)
    return space.int_w(w_res)

@cpython_api([PyObject], lltype.Void)
def PyDict_Clear(space, w_obj):
    """Empty an existing dictionary of all key-value pairs."""
    space.call_method(space.w_dict, "clear", w_obj)

@cpython_api([PyObject], PyObject)
def PyDict_Copy(space, w_obj):
    """Return a new dictionary that contains the same key-value pairs as p.
    """
    return space.call_method(space.w_dict, "copy", w_obj)

def _has_val(space, w_dict, w_key):
    try:
        w_val = space.getitem(w_dict, w_key)
    except OperationError as e:
        if e.match(space, space.w_KeyError):
            return False
        else:
            raise
    return True

@cpython_api([PyObject, PyObject, rffi.INT_real], rffi.INT_real, error=-1)
def PyDict_Merge(space, w_a, w_b, override):
    """Iterate over mapping object b adding key-value pairs to dictionary a.
    b may be a dictionary, or any object supporting PyMapping_Keys()
    and PyObject_GetItem(). If override is true, existing pairs in a
    will be replaced if a matching key is found in b, otherwise pairs will
    only be added if there is not a matching key in a. Return 0 on
    success or -1 if an exception was raised.
    """
    override = rffi.cast(lltype.Signed, override)
    w_keys = space.call_method(w_b, "keys")
    for w_key  in space.iteriterable(w_keys):
        if not _has_val(space, w_a, w_key) or override != 0:
            space.setitem(w_a, w_key, space.getitem(w_b, w_key))
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyDict_Update(space, w_obj, w_other):
    """This is the same as PyDict_Merge(a, b, 1) in C, or a.update(b) in
    Python.  Return 0 on success or -1 if an exception was raised.
    """
    return PyDict_Merge(space, w_obj, w_other, 1)

@cpython_api([PyObject], PyObject)
def PyDict_Keys(space, w_obj):
    """Return a PyListObject containing all the keys from the dictionary,
    as in the dictionary method dict.keys()."""
    return space.call_function(space.w_list, space.call_method(space.w_dict, "keys", w_obj))

@cpython_api([PyObject], PyObject)
def PyDict_Values(space, w_obj):
    """Return a PyListObject containing all the values from the
    dictionary p, as in the dictionary method dict.values()."""
    return space.call_function(space.w_list, space.call_method(space.w_dict, "values", w_obj))

@cpython_api([PyObject], PyObject)
def PyDict_Items(space, w_obj):
    """Return a PyListObject containing all the items from the
    dictionary, as in the dictionary method dict.items()."""
    return space.call_function(space.w_list, space.call_method(space.w_dict, "items", w_obj))

@cpython_api([PyObject, Py_ssize_tP, PyObjectP, PyObjectP], rffi.INT_real, error=CANNOT_FAIL)
def PyDict_Next(space, w_dict, ppos, pkey, pvalue):
    """Iterate over all key-value pairs in the dictionary p.  The
    Py_ssize_t referred to by ppos must be initialized to 0
    prior to the first call to this function to start the iteration; the
    function returns true for each pair in the dictionary, and false once all
    pairs have been reported.  The parameters pkey and pvalue should either
    point to PyObject* variables that will be filled in with each key
    and value, respectively, or may be NULL.  Any references returned through
    them are borrowed.  ppos should not be altered during iteration. Its
    value represents offsets within the internal dictionary structure, and
    since the structure is sparse, the offsets are not consecutive.

    For example:

    PyObject *key, *value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(self->dict, &pos, &key, &value)) {
        /* do something interesting with the values... */
        ...
    }

    The dictionary p should not be mutated during iteration.  It is safe
    (since Python 2.1) to modify the values of the keys as you iterate over the
    dictionary, but only so long as the set of keys does not change.  For
    example:

    PyObject *key, *value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(self->dict, &pos, &key, &value)) {
        int i = PyLong_AS_LONG(value) + 1;
        PyObject *o = PyLong_FromLong(i);
        if (o == NULL)
            return -1;
        if (PyDict_SetItem(self->dict, key, o) < 0) {
            Py_DECREF(o);
            return -1;
        }
        Py_DECREF(o);
    }"""
    if w_dict is None:
        return 0

    # XXX XXX PyDict_Next is not efficient. Storing an iterator would probably
    # work, but we can't work out how to not leak it if iteration does
    # not complete.  Alternatively, we could add some RPython-only
    # dict-iterator method to move forward by N steps.

    w_dict.ensure_object_strategy()     # make sure both keys and values can
                                        # be borrwed
    try:
        w_iter = space.iter(space.call_method(space.w_dict, "items", w_dict))
        pos = ppos[0]
        while pos:
            space.next(w_iter)
            pos -= 1

        w_item = space.next(w_iter)
        w_key, w_value = space.fixedview(w_item, 2)
        if pkey:
            pkey[0]   = as_pyobj(space, w_key)
        if pvalue:
            pvalue[0] = as_pyobj(space, w_value)
        ppos[0] += 1
    except OperationError as e:
        if not e.match(space, space.w_StopIteration):
            raise
        return 0
    return 1

@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def _PyDict_HasOnlyStringKeys(space, w_dict):
    keys_w = space.unpackiterable(w_dict)
    for w_key in keys_w:
        if not space.isinstance_w(w_key, space.w_unicode):
            return 0
    return 1

