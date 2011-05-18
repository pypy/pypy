from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    cpython_api, CANNOT_FAIL, build_type_checkers, Py_ssize_t,
    Py_ssize_tP, CONST_STRING)
from pypy.module.cpyext.pyobject import PyObject, PyObjectP, borrow_from
from pypy.module.cpyext.pyobject import RefcountState
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.interpreter.error import OperationError

@cpython_api([], PyObject)
def PyDict_New(space):
    return space.newdict()

PyDict_Check, PyDict_CheckExact = build_type_checkers("Dict")

@cpython_api([PyObject, PyObject], PyObject, error=CANNOT_FAIL)
def PyDict_GetItem(space, w_dict, w_key):
    try:
        w_res = space.getitem(w_dict, w_key)
    except:
        return None
    return borrow_from(w_dict, w_res)

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

@cpython_api([PyObject, CONST_STRING], PyObject, error=CANNOT_FAIL)
def PyDict_GetItemString(space, w_dict, key):
    """This is the same as PyDict_GetItem(), but key is specified as a
    char*, rather than a PyObject*."""
    try:
        w_res = space.finditem_str(w_dict, rffi.charp2str(key))
    except:
        w_res = None
    if w_res is None:
        return None
    return borrow_from(w_dict, w_res)

@cpython_api([PyObject, rffi.CCHARP], rffi.INT_real, error=-1)
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
    space.call_method(w_obj, "clear")

@cpython_api([PyObject], PyObject)
def PyDict_Copy(space, w_obj):
    """Return a new dictionary that contains the same key-value pairs as p.
    """
    return space.call_method(w_obj, "copy")

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PyDict_Update(space, w_obj, w_other):
    """This is the same as PyDict_Merge(a, b, 1) in C, or a.update(b) in
    Python.  Return 0 on success or -1 if an exception was raised.
    """
    space.call_method(w_obj, "update", w_other)
    return 0

@cpython_api([PyObject], PyObject)
def PyDict_Keys(space, w_obj):
    """Return a PyListObject containing all the keys from the dictionary,
    as in the dictionary method dict.keys()."""
    return space.call_method(w_obj, "keys")

@cpython_api([PyObject], PyObject)
def PyDict_Values(space, w_obj):
    """Return a PyListObject containing all the values from the
    dictionary p, as in the dictionary method dict.values()."""
    return space.call_method(w_obj, "values")

@cpython_api([PyObject], PyObject)
def PyDict_Items(space, w_obj):
    """Return a PyListObject containing all the items from the
    dictionary, as in the dictionary method dict.items()."""
    return space.call_method(w_obj, "items")

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
        int i = PyInt_AS_LONG(value) + 1;
        PyObject *o = PyInt_FromLong(i);
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

    # Note: this is not efficient. Storing an iterator would probably
    # work, but we can't work out how to not leak it if iteration does
    # not complete.

    try:
        w_iter = space.call_method(w_dict, "iteritems")
        pos = ppos[0]
        while pos:
            space.call_method(w_iter, "next")
            pos -= 1

        w_item = space.call_method(w_iter, "next")
        w_key, w_value = space.fixedview(w_item, 2)
        state = space.fromcache(RefcountState)
        pkey[0]   = state.make_borrowed(w_dict, w_key)
        pvalue[0] = state.make_borrowed(w_dict, w_value)
        ppos[0] += 1
    except OperationError, e:
        if not e.match(space, space.w_StopIteration):
            raise
        return 0
    return 1
