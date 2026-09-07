from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import rfloat
from pypy.module.cpyext.api import (PyObjectFields, bootstrap_function,
    cpython_struct, build_type_checkers, init_function,
    CANNOT_FAIL, cpython_api, PyObject, CONST_STRING)
from pypy.module.cpyext.pyobject import (
    make_typedescr, track_reference, from_ref)
from rpython.rlib.rstruct import runpack
from pypy.objspace.std.floatobject import W_FloatObject, call_float_method
from pypy.module.cpyext.state import State
from pypy.interpreter.error import OperationError, oefmt
from pypy.module.cpyext.pyerrors import PyErr_BadArgument

PyFloatObjectStruct = lltype.ForwardReference()
PyFloatObject = lltype.Ptr(PyFloatObjectStruct)
PyFloatObjectFields = PyObjectFields + \
    (("ob_fval", rffi.DOUBLE),)
cpython_struct("PyFloatObject", PyFloatObjectFields, PyFloatObjectStruct)

PyFloat_Check, PyFloat_CheckExact = build_type_checkers(
    "Float", "w_float", export=False)

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

@cpython_api([lltype.Float], PyObject, abi3=True)
def PyFloat_FromDouble(space, value):
    return space.newfloat(value)

@cpython_api([PyObject], lltype.Float, error=-1, abi3=True)
def PyFloat_AsDouble(space, w_obj):
    if w_obj is None:
        raise PyErr_BadArgument(space)
    if not space.isinstance_w(w_obj, space.w_float):
        # Replicate CPython's PyFloat_AsDouble: try __float__, then __index__,
        # then raise "must be real number, not <type>" - not the broader
        # float() error which also accepts strings.
        w_float_method = space.lookup(w_obj, '__float__')
        if w_float_method is not None:
            w_value = call_float_method(space, w_obj)
        else:
            w_index_method = space.lookup(w_obj, '__index__')
            if w_index_method is not None:
                return space.float_w(space.float(space.index(w_obj)))
            raise oefmt(space.w_TypeError,
                        "must be real number, not %T", w_obj)
    else:
        w_value = w_obj
    return space.float_w(w_value)

@cpython_api([rffi.VOIDP], lltype.Float, error=CANNOT_FAIL)
def PyFloat_AS_DOUBLE(space, w_float):
    """Return a C double representation of the contents of w_float, but
    without error checking."""
    return space.float_w(w_float)

@cpython_api([], PyObject, abi3=True)
def PyFloat_GetInfo(space):
    """Return a structseq instance which contains information about the
    precision, minimum and maximum values of a float."""
    from pypy.module.sys.system import get_float_info
    return get_float_info(space)

@cpython_api([], lltype.Float, error=CANNOT_FAIL, abi3=True)
def PyFloat_GetMax(space):
    """Return the maximum representable finite float DBL_MAX as C double."""
    return rfloat.DBL_MAX

@cpython_api([], lltype.Float, error=CANNOT_FAIL, abi3=True)
def PyFloat_GetMin(space):
    """Return the minimum normalized positive float DBL_MIN as C double."""
    return rfloat.DBL_MIN

@cpython_api([PyObject], PyObject, abi3=True)
def PyNumber_Float(space, w_obj):
    """
    Returns the o converted to a float object on success, or NULL on failure.
    This is the equivalent of the Python expression float(o)."""
    if w_obj is None:
        raise oefmt(space.w_SystemError, "null argument to internal routine")
    return space.call_function(space.w_float, w_obj)

@cpython_api([PyObject], PyObject, abi3=True)
def PyFloat_FromString(space, w_obj):
    """
    Create a PyFloatObject object based on the string value in str, or
    NULL on failure.
    """
    if space.isinstance_w(w_obj, space.w_unicode):
        return space.call_function(space.w_float, w_obj)
    try:
        s = space.bufferstr_w(w_obj)
    except OperationError:
        raise oefmt(space.w_TypeError,
            "float() argument must be a string or a real number, not '%T'",
            w_obj)
    return space.call_function(space.w_float, space.newbytes(s))
