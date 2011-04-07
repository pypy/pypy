from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (cpython_api, Py_ssize_t, CANNOT_FAIL,
                                    build_type_checkers)
from pypy.module.cpyext.pyobject import (PyObject, PyObjectP, Py_DecRef,
    borrow_from, make_ref, from_ref)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.smalltupleobject import W_SmallTupleObject

PyTuple_Check, PyTuple_CheckExact = build_type_checkers("Tuple")

@cpython_api([Py_ssize_t], PyObject)
def PyTuple_New(space, size):
    return space.newtuple([space.w_None] * size)

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real, error=-1)
def PyTuple_SetItem(space, w_t, pos, w_obj):
    if not PyTuple_Check(space, w_t):
        # XXX this should also steal a reference, test it!!!
        PyErr_BadInternalCall(space)
    _setitem_tuple(w_t, pos, w_obj)
    Py_DecRef(space, w_obj) # SetItem steals a reference!
    return 0

def _setitem_tuple(w_t, pos, w_obj):
    if isinstance(w_t, W_TupleObject):
        w_t.wrappeditems[pos] = w_obj
    elif isinstance(w_t, W_SmallTupleObject):
        w_t.setitem(pos, w_obj)
    else:
        assert False

@cpython_api([PyObject, Py_ssize_t], PyObject)
def PyTuple_GetItem(space, w_t, pos):
    if not PyTuple_Check(space, w_t):
        PyErr_BadInternalCall(space)
    w_obj = space.getitem(w_t, space.wrap(pos))
    return borrow_from(w_t, w_obj)

@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PyTuple_GET_SIZE(space, w_t):
    """Return the size of the tuple p, which must be non-NULL and point to a tuple;
    no error checking is performed. """
    return space.int_w(space.len(w_t))

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PyTuple_Size(space, ref):
    """Take a pointer to a tuple object, and return the size of that tuple."""
    if not PyTuple_Check(space, ref):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected tuple object"))
    return PyTuple_GET_SIZE(space, ref)


@cpython_api([PyObjectP, Py_ssize_t], rffi.INT_real, error=-1)
def _PyTuple_Resize(space, ref, newsize):
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
    py_tuple = from_ref(space, ref[0])
    if not PyTuple_Check(space, py_tuple):
        PyErr_BadInternalCall(space)
    py_newtuple = PyTuple_New(space, newsize)
    
    to_cp = newsize
    oldsize = space.int_w(space.len(py_tuple))
    if oldsize < newsize:
        to_cp = oldsize
    for i in range(to_cp):
        _setitem_tuple(py_newtuple, i, space.getitem(py_tuple, space.wrap(i)))
    Py_DecRef(space, ref[0])
    ref[0] = make_ref(space, py_newtuple)
    return 0
