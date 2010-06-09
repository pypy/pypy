from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.gateway import cpython_api, CANNOT_FAIL
from pypy.module.cpyext.api import (
    PyObjectFields, bootstrap_function, cpython_struct, build_type_checkers)
from pypy.module.cpyext.pyobject import (
    PyObject, make_ref, from_ref, Py_DecRef, make_typedescr)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.__builtin__.interp_classobj import (
    W_ClassObject, W_InstanceObject)

PyClass_Check, PyClass_CheckExact = build_type_checkers("Class", W_ClassObject)
PyInstance_Check, PyInstance_CheckExact = build_type_checkers("Instance", W_InstanceObject)

@cpython_api([PyObject, PyObject], PyObject)
def PyInstance_NewRaw(space, w_class, w_dict):
    """Create a new instance of a specific class without calling its constructor.
    class is the class of new object.  The dict parameter will be used as the
    object's __dict__; if NULL, a new dictionary will be created for the
    instance."""
    if not PyClass_Check(space, w_class):
        return PyErr_BadInternalCall(space)
    return W_InstanceObject(space, w_class, w_dict)

@cpython_api([PyObject, PyObject], PyObject, error=CANNOT_FAIL)
def _PyInstance_Lookup(space, w_instance, w_name):
    assert isinstance(w_instance, W_InstanceObject)
    w_result = space.finditem(w_instance.w_dict, w_name)
    if w_result is not None:
        return w_result
    return w_instance.w_class.lookup(space, w_name)


