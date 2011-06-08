from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    PyObjectFields, CANNOT_FAIL,
    cpython_api, bootstrap_function, cpython_struct, build_type_checkers)
from pypy.module.cpyext.pyobject import PyObject, make_ref, from_ref, Py_DecRef, make_typedescr
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.__builtin__.interp_classobj import W_ClassObject, W_InstanceObject

PyClass_Check, PyClass_CheckExact = build_type_checkers("Class", W_ClassObject)
PyInstance_Check, PyInstance_CheckExact = build_type_checkers("Instance", W_InstanceObject)

@cpython_api([PyObject, PyObject], PyObject)
def PyInstance_NewRaw(space, w_class, w_dict):
    """Create a new instance of a specific class without calling its constructor.
    class is the class of new object.  The dict parameter will be used as the
    object's __dict__; if NULL, a new dictionary will be created for the
    instance."""
    if not isinstance(w_class, W_ClassObject):
        return PyErr_BadInternalCall(space)
    w_result = w_class.instantiate(space)
    if w_dict is not None:
        w_result.setdict(space, w_dict)
    return w_result

@cpython_api([PyObject, PyObject], PyObject, error=CANNOT_FAIL)
def _PyInstance_Lookup(space, w_instance, w_name):
    name = space.str_w(w_name)
    assert isinstance(w_instance, W_InstanceObject)
    w_result = w_instance.getdictvalue(space, name)
    if w_result is not None:
        return w_result
    return w_instance.w_class.lookup(space, name)

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyClass_New(space, w_bases, w_dict, w_name):
    w_classobj = space.gettypefor(W_ClassObject)
    return space.call_function(w_classobj,
                               w_name, w_bases, w_dict)

