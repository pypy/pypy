from pypy.rpython.lltypesystem import lltype
from pypy.module.cpyext.api import cpython_api, PyObject, build_type_checkers
from pypy.objspace.std.complexobject import W_ComplexObject

PyComplex_Check, PyComplex_CheckExact = build_type_checkers("Complex")

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

