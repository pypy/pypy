from pypy.interpreter.error import OperationError
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, Py_ssize_t, CANNOT_FAIL,
                                    build_type_checkers, PyObjectFields,
                                    cpython_struct, bootstrap_function)
from pypy.module.cpyext.pyobject import (PyObject, PyObjectP, Py_DecRef,
    make_ref, from_ref, decref,
    track_reference, make_typedescr, get_typedescr)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.objspace.std.tupleobject import W_TupleObject

##
## Implementation of PyTupleObject
## ===============================
##
## Similar to stringobject.py.  The reason is only the existance of
## W_SpecialisedTupleObject_ii and W_SpecialisedTupleObject_ff.
## These two PyPy classes implement getitem() by returning a freshly
## constructed W_IntObject or W_FloatObject.  This is not compatible
## with PyTuple_GetItem, which returns a borrowed reference.
##
## So we use this more advanced (but also likely faster) solution:
## tuple_attach makes a real PyTupleObject with an array of N
## 'PyObject *', which are created immediately and own a reference.
## Then the macro PyTuple_GET_ITEM can be implemented like CPython.
##

PyTupleObjectStruct = lltype.ForwardReference()
PyTupleObject = lltype.Ptr(PyTupleObjectStruct)
ObjectItems = rffi.CArray(PyObject)
PyTupleObjectFields = PyObjectFields + \
    (("ob_size", Py_ssize_t), ("ob_item", lltype.Ptr(ObjectItems)))
cpython_struct("PyTupleObject", PyTupleObjectFields, PyTupleObjectStruct)

@bootstrap_function
def init_stringobject(space):
    "Type description of PyTupleObject"
    make_typedescr(space.w_tuple.layout.typedef,
                   basestruct=PyTupleObject.TO,
                   attach=tuple_attach,
                   dealloc=tuple_dealloc,
                   realize=tuple_realize)

PyTuple_Check, PyTuple_CheckExact = build_type_checkers("Tuple")

def tuple_check_ref(space, ref):
    w_type = from_ref(space, rffi.cast(PyObject, ref.c_ob_type))
    return (w_type is space.w_tuple or
            space.is_true(space.issubtype(w_type, space.w_tuple)))

def new_empty_tuple(space, length):
    """
    Allocate a PyTupleObject and its array of PyObject *, but without a
    corresponding interpreter object.  The array may be mutated, until
    tuple_realize() is called.  Refcount of the result is 1.
    """
    typedescr = get_typedescr(space.w_tuple.layout.typedef)
    py_obj = typedescr.allocate(space, space.w_tuple)
    py_tup = rffi.cast(PyTupleObject, py_obj)

    py_tup.c_ob_item = lltype.malloc(ObjectItems, length,
                                     flavor='raw', zero=True)
    py_tup.c_ob_size = length
    return py_tup

def tuple_attach(space, py_obj, w_obj):
    """
    Fills a newly allocated PyTupleObject with the given tuple object. The
    buffer must not be modified.
    """
    items_w = space.fixedview(w_obj)
    l = len(items_w)
    p = lltype.malloc(ObjectItems, l, flavor='raw')
    i = 0
    try:
        while i < l:
            p[i] = make_ref(space, items_w[i])
            i += 1
    except:
        while i > 0:
            i -= 1
            decref(space, p[i])
        lltype.free(p, flavor='raw')
        raise
    py_tup = rffi.cast(PyTupleObject, py_obj)
    py_tup.c_ob_size = l
    py_tup.c_ob_item = p

def tuple_realize(space, py_obj):
    """
    Creates the tuple in the interpreter. The PyTupleObject must not
    be modified after this call.
    """
    py_tup = rffi.cast(PyTupleObject, py_obj)
    l = py_tup.c_ob_size
    p = py_tup.c_ob_item
    items_w = [None] * l
    for i in range(l):
        items_w[i] = from_ref(space, p[i])
    w_obj = space.newtuple(items_w)
    track_reference(space, py_obj, w_obj)
    return w_obj

@cpython_api([PyObject], lltype.Void, header=None)
def tuple_dealloc(space, py_obj):
    """Frees allocated PyTupleObject resources.
    """
    py_tup = rffi.cast(PyTupleObject, py_obj)
    p = py_tup.c_ob_item
    if p:
        for i in range(py_tup.c_ob_size):
            decref(space, p[i])
        lltype.free(p, flavor="raw")
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)

#_______________________________________________________________________

@cpython_api([Py_ssize_t], PyObject)
def PyTuple_New(space, size):
    return rffi.cast(PyObject, new_empty_tuple(space, size))

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyTuple_SetItem(space, ref, index, py_obj):
    # XXX this will not complain when changing tuples that have
    # already been realized as a W_TupleObject, but won't update the
    # W_TupleObject
    if not tuple_check_ref(space, ref):
        decref(space, py_obj)
        PyErr_BadInternalCall(space)
    ref = rffi.cast(PyTupleObject, ref)
    size = ref.c_ob_size
    if index < 0 or index >= size:
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple assignment index out of range"))
    old_ref = ref.c_ob_item[index]
    ref.c_ob_item[index] = py_obj    # consumes a reference
    if old_ref:
        decref(space, old_ref)
    return 0

@cpython_api([PyObject, Py_ssize_t], PyObject, result_borrowed=True)
def PyTuple_GetItem(space, ref, index):
    if not tuple_check_ref(space, ref):
        PyErr_BadInternalCall(space)
    ref = rffi.cast(PyTupleObject, ref)
    size = ref.c_ob_size
    if index < 0 or index >= size:
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple index out of range"))
    return ref.c_ob_item[index]     # borrowed ref

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyTuple_Size(space, ref):
    """Take a pointer to a tuple object, and return the size of that tuple."""
    if not tuple_check_ref(space, ref):
        PyErr_BadInternalCall(space)
    ref = rffi.cast(PyTupleObject, ref)
    return ref.c_ob_size


@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real, error=-1)
def _PyTuple_Resize(space, p_ref, newsize):
    """Can be used to resize a tuple.  newsize will be the new length of the tuple.
    Because tuples are supposed to be immutable, this should only be used if there
    is only one reference to the object.  Do not use this if the tuple may already
    be known to some other part of the code.  The tuple will always grow or shrink
    at the end.  Think of this as destroying the old tuple and creating a new one,
    only more efficiently.  Returns 0 on success. Client code should never
    assume that the resulting value of *p will be the same as before calling
    this function. If the object referenced by *p is replaced, the original
    *p is destroyed.  On failure, returns -1 and sets *p to NULL, and
    raises MemoryError or SystemError."""
    ref = p_ref[0]
    if not tuple_check_ref(space, ref):
        PyErr_BadInternalCall(space)
    ref = rffi.cast(PyTupleObject, ref)
    oldsize = ref.c_ob_size
    oldp = ref.c_ob_item
    newp = lltype.malloc(ObjectItems, newsize, zero=True, flavor='raw')
    try:
        if oldsize < newsize:
            to_cp = oldsize
        else:
            to_cp = newsize
        for i in range(to_cp):
            newp[i] = oldp[i]
    except:
        lltype.free(newp, flavor='raw')
        raise
    ref.c_ob_item = newp
    ref.c_ob_size = newsize
    lltype.free(oldp, flavor='raw')
    # in this version, p_ref[0] never needs to be updated
    return 0

@cpython_api([PyObject, Py_ssize_t, Py_ssize_t], PyObject)
def PyTuple_GetSlice(space, w_obj, low, high):
    """Take a slice of the tuple pointed to by p from low to high and return it
    as a new tuple.
    """
    return space.getslice(w_obj, space.wrap(low), space.wrap(high))
