from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.cpyext.api import (
    cpython_api, cpython_struct, PyObject, build_type_checkers)
from pypy.module.cpyext.floatobject import PyFloat_AsDouble
from pypy.objspace.std.complexobject import W_ComplexObject
from pypy.interpreter.error import OperationError

PyComplex_Check, PyComplex_CheckExact = build_type_checkers("Complex")

Py_complex_t = lltype.ForwardReference()
Py_complex_ptr = lltype.Ptr(Py_complex_t)
Py_complex_fields = (("real", rffi.DOUBLE), ("imag", rffi.DOUBLE))
cpython_struct("Py_complex", Py_complex_fields, Py_complex_t)

@cpython_api([lltype.Float, lltype.Float], PyObject)
def PyComplex_FromDoubles(space, real, imag):
    return space.newcomplex(real, imag)

@cpython_api([PyObject], lltype.Float, error=-1)
def PyComplex_RealAsDouble(space, w_obj):
    if space.is_true(space.isinstance(w_obj, space.w_complex)):
        assert isinstance(w_obj, W_ComplexObject)
        return w_obj.realval
    else:
        return space.float_w(w_obj)

@cpython_api([PyObject], lltype.Float, error=-1)
def PyComplex_ImagAsDouble(space, w_obj):
    if space.is_true(space.isinstance(w_obj, space.w_complex)):
        assert isinstance(w_obj, W_ComplexObject)
        return w_obj.imagval
    else:
        # CPython also accepts anything
        return 0.0

# lltype does not handle functions returning a structure.  This implements a
# helper function, which takes as argument a reference to the return value.
@cpython_api([PyObject, Py_complex_ptr], lltype.Void)
def _PyComplex_AsCComplex(space, w_obj, result):
    """Return the Py_complex value of the complex number op.

    If op is not a Python complex number object but has a __complex__()
    method, this method will first be called to convert op to a Python complex
    number object."""
    # return -1 on failure
    result.c_real = -1.0
    result.c_imag = 0.0
    if not PyComplex_Check(space, w_obj):
        try:
            w_obj = space.call_method(w_obj, "__complex__")
        except:
            # if the above did not work, interpret obj as a float giving the
            # real part of the result, and fill in the imaginary part as 0.
            result.c_real = PyFloat_AsDouble(space, w_obj) # -1 on failure
            return

        if not PyComplex_Check(space, w_obj):
            raise OperationError(space.w_TypeError, space.wrap(
                "__complex__ should return a complex object"))

    assert isinstance(w_obj, W_ComplexObject)
    result.c_real = w_obj.realval
    result.c_imag = w_obj.imagval
