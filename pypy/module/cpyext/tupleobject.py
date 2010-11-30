from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, Py_ssize_t, CANNOT_FAIL,
                                    build_type_checkers, PyObjectFields,
                                    cpython_struct, bootstrap_function)
from pypy.module.cpyext.pyobject import (PyObject, PyObjectP, Py_DecRef,
    borrow_from, make_ref, from_ref, make_typedescr, get_typedescr, Reference,
    track_reference)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall

##
## Implementation of PyTupleObject
## ===============================
##
## We have the same problem as PyStringObject: a PyTupleObject can be
## initially used in a read-write way with PyTuple_New(), PyTuple_SetItem()
## and _PyTuple_Resize().
##
## The 'size' and 'items' fields of a PyTupleObject are always valid.
## Apart from that detail, see the big comment in stringobject.py for
## more information.
##

ARRAY_OF_PYOBJ = rffi.CArrayPtr(PyObject)
PyTupleObjectStruct = lltype.ForwardReference()
PyTupleObject = lltype.Ptr(PyTupleObjectStruct)
PyTupleObjectFields = PyObjectFields + \
    (("items", ARRAY_OF_PYOBJ), ("size", Py_ssize_t))
cpython_struct("PyTupleObject", PyTupleObjectFields, PyTupleObjectStruct)

@bootstrap_function
def init_tupleobject(space):
    "Type description of PyTupleObject"
    make_typedescr(space.w_tuple.instancetypedef,
                   basestruct=PyTupleObject.TO,
                   attach=tuple_attach,
                   dealloc=tuple_dealloc,
                   realize=tuple_realize)

PyTuple_Check, PyTuple_CheckExact = build_type_checkers("Tuple")

def new_empty_tuple(space, length):
    """
    Allocate a PyTupleObject and its array, but without a corresponding
    interpreter object.  The array items may be mutated, until
    tuple_realize() is called.
    """
    typedescr = get_typedescr(space.w_tuple.instancetypedef)
    py_obj = typedescr.allocate(space, space.w_tuple)
    py_tup = rffi.cast(PyTupleObject, py_obj)

    py_tup.c_items = lltype.malloc(ARRAY_OF_PYOBJ.TO, length,
                                   flavor='raw', zero=True)
    py_tup.c_size = length
    return py_tup

def tuple_attach(space, py_obj, w_obj):
    """
    Fills a newly allocated PyTupleObject with the given tuple object.
    """
    items_w = space.fixedview(w_obj)
    py_tup = rffi.cast(PyTupleObject, py_obj)
    py_tup.c_items = lltype.nullptr(ARRAY_OF_PYOBJ.TO)
    py_tup.c_size = len(items_w)

def tuple_realize(space, py_obj):
    """
    Creates the tuple in the interpreter. The PyTupleObject items array
    must not be modified after this call.
    """
    py_tup = rffi.cast(PyTupleObject, py_obj)
    # If your CPython extension creates a self-referential tuple
    # with PyTuple_SetItem(), you loose.
    c_items = py_tup.c_items
    items_w = [from_ref(space, c_items[i]) for i in range(py_tup.c_size)]
    w_obj = space.newtuple(items_w)
    track_reference(space, py_obj, w_obj)
    return w_obj

@cpython_api([PyObject], lltype.Void, external=False)
def tuple_dealloc(space, py_obj):
    """Frees allocated PyTupleObject resources.
    """
    py_tup = rffi.cast(PyTupleObject, py_obj)
    if py_tup.c_items:
        for i in range(py_tup.c_size):
            Py_DecRef(space, py_tup.c_items[i])
        lltype.free(py_tup.c_items, flavor="raw")
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)

#_______________________________________________________________________

@cpython_api([Py_ssize_t], PyObject)
def PyTuple_New(space, size):
    return rffi.cast(PyObject, new_empty_tuple(space, size))

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyTuple_SetItem(space, ref, pos, ref_item):
    # XXX steals a reference at the level of PyObjects.  Don't try to
    # XXX call this function with an interpreter object as ref_item!

    # XXX do PyTuple_Check, without forcing ref as an interpreter object
    # XXX -- then if it fails it should also steal a reference, test it!!!
    ref_tup = rffi.cast(PyTupleObject, ref)
    if not ref_tup.c_items:
        msg = "PyTuple_SetItem() called on an already-escaped tuple object"
        raise OperationError(space.w_SystemError, space.wrap(msg))
    ref_old = ref_tup.c_items[pos]
    ref_tup.c_items[pos] = ref_item      # SetItem steals a reference!
    Py_DecRef(space, ref_old)
    return 0

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PyTuple_GetItem(space, ref, pos):
    # XXX do PyTuple_Check, without forcing ref as an interpreter object
    ref_tup = rffi.cast(PyTupleObject, ref)
    if ref_tup.c_items:
        return Reference(ref_tup.c_items[pos])     # borrowed reference
    else:
        w_t = from_ref(space, ref)
        w_obj = space.getitem(w_t, space.wrap(pos))
        return borrow_from(w_t, w_obj)

@cpython_api([PyObject], Py_ssize_t, error=-1)
def _PyTuple_Size_Fast(space, ref):
    # custom version: it's not a macro, so it can be called from other .py
    # files; but it doesn't include PyTuple_Check()
    ref_tup = rffi.cast(PyTupleObject, ref)
    return ref_tup.c_size

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyTuple_Size(space, ref):
    """Take a pointer to a tuple object, and return the size of that tuple."""
    # XXX do PyTuple_Check, without forcing ref as an interpreter object
    ref_tup = rffi.cast(PyTupleObject, ref)
    return ref_tup.c_size


@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real, error=-1)
def _PyTuple_Resize(space, refp, newsize):
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
    # XXX do PyTuple_Check, without forcing ref as an interpreter object
    # XXX -- then if it fails it should reset refp[0] to null
    ref_tup = rffi.cast(PyTupleObject, refp[0])
    c_newitems = lltype.malloc(ARRAY_OF_PYOBJ.TO, newsize,
                               flavor='raw', zero=True)
    c_olditems = ref_tup.c_items
    if not c_olditems:
        msg = "_PyTuple_Resize() called on an already-escaped tuple object"
        raise OperationError(space.w_SystemError, space.wrap(msg))
    oldsize = ref_tup.c_size
    for i in range(min(oldsize, newsize)):
        c_newitems[i] = c_olditems[i]
    # decref items deleted by shrinkage
    for i in range(newsize, oldsize):
        Py_DecRef(space, c_olditems[i])
    ref_tup.c_items = c_newitems
    ref_tup.c_size = newsize
    lltype.free(c_olditems, flavor='raw')
    return 0
