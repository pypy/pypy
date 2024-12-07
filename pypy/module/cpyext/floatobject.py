from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (PyObjectFields, bootstrap_function,
    cpython_struct, build_type_checkers, init_function,
    CANNOT_FAIL, cpython_api, PyObject, CONST_STRING)
from pypy.module.cpyext.pyobject import (
    make_typedescr, track_reference, from_ref)
from rpython.rlib.rstruct import runpack
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.module.cpyext.state import State

PyFloatObjectStruct = lltype.ForwardReference()
PyFloatObject = lltype.Ptr(PyFloatObjectStruct)
PyFloatObjectFields = PyObjectFields + \
    (("ob_fval", rffi.DOUBLE),)
cpython_struct("PyFloatObject", PyFloatObjectFields, PyFloatObjectStruct)

PyFloat_Check, PyFloat_CheckExact = build_type_checkers("Float", "w_float")

@bootstrap_function
def init_floatobject(space):
    "Type description of PyFloatObject"
    make_typedescr(space.w_float.layout.typedef,
                   basestruct=PyFloatObject.TO,
                   attach=float_attach,
                   realize=float_realize)

@init_function
def call_init(space):
    state = space.fromcache(State)
    state.C.float_init()

def float_attach(space, py_obj, w_obj, w_userdata=None):
    """
    Fills a newly allocated PyFloatObject with the given float object. The
    value must not be modified.
    """
    py_float = rffi.cast(PyFloatObject, py_obj)
    py_float.c_ob_fval = space.float_w(w_obj)

def float_realize(space, obj):
    floatval = rffi.cast(lltype.Float, rffi.cast(PyFloatObject, obj).c_ob_fval)
    w_type = from_ref(space, rffi.cast(PyObject, obj.c_ob_type))
    w_obj = space.allocate_instance(W_FloatObject, w_type)
    w_obj.__init__(floatval)
    track_reference(space, obj, w_obj)
    return w_obj

@cpython_api([lltype.Float], PyObject)
def PyFloat_FromDouble(space, value):
    return space.newfloat(value)

@cpython_api([PyObject], lltype.Float, error=-1)
def PyFloat_AsDouble(space, w_obj):
    if not space.isinstance_w(w_obj, space.w_float):
        w_value = space.float(w_obj)
        w_value_type = space.type(w_value)
        if not space.is_w(w_value_type, space.w_float):
            space.warn(space.newtext(
                "%s.__float__ returned non-float (type %s).  "
                "The ability to return an instance of a strict subclass "
                "of float is deprecated, and may be removed "
                "in a future version of Python." %
                (space.type(w_obj).name, w_value_type.name)),
                space.w_DeprecationWarning)
    else:
        w_value = w_obj
    return space.float_w(w_value)

@cpython_api([rffi.VOIDP], lltype.Float, error=CANNOT_FAIL)
def PyFloat_AS_DOUBLE(space, w_float):
    """Return a C double representation of the contents of w_float, but
    without error checking."""
    return space.float_w(w_float)

@cpython_api([PyObject], PyObject)
def PyNumber_Float(space, w_obj):
    """
    Returns the o converted to a float object on success, or NULL on failure.
    This is the equivalent of the Python expression float(o)."""
    return space.call_function(space.w_float, w_obj)

@cpython_api([PyObject], PyObject)
def PyFloat_FromString(space, w_obj):
    """
    Create a PyFloatObject object based on the string value in str, or
    NULL on failure.
    """
    return space.call_function(space.w_float, w_obj)
