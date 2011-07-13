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
    if w_iterable is None:
        return space.call_function(space.w_set)
    else:
        return space.call_function(space.w_set, w_iterable)

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PySet_Add(space, w_s, w_obj):
    if not PySet_Check(space, w_s):
        PyErr_BadInternalCall(space)
    space.call_method(w_s, 'add', w_obj)
    return 0

@cpython_api([PyObject, PyObject], rffi.INT_real, error=-1)
def PySet_Discard(space, w_s, w_obj):
    if not PySet_Check(space, w_s):
        PyErr_BadInternalCall(space)
    space.call_method(w_s, 'discard', w_obj)
    return 0


@cpython_api([PyObject], Py_ssize_t, error=CANNOT_FAIL)
def PySet_GET_SIZE(space, w_s):
    return space.int_w(space.len(w_s))

@cpython_api([PyObject], Py_ssize_t, error=-1)
def PySet_Size(space, ref):
    if not PySet_Check(space, ref):
        raise OperationError(space.w_TypeError,
                             space.wrap("expected set object"))
    return PySet_GET_SIZE(space, ref)
