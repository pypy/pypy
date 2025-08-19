from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cts
from pypy.module.cpyext.pyobject import PyObject
from rpython.rlib.rarithmetic import widen


_HEADER = 'pypy_marshal_decl.h'

@cts.decl("PyObject *<>(const char *, Py_ssize_t)", header=_HEADER)
def PyMarshal_ReadObjectFromString(space, p, size):
    from pypy.module.marshal.interp_marshal import loads
    s = rffi.constcharpsize2str(p, size)
    return loads(space, space.newbytes(s))

@cpython_api([PyObject, rffi.INT_real], PyObject, header=_HEADER)
def PyMarshal_WriteObjectToString(space, w_x, version):
    from pypy.module.marshal.interp_marshal import dumps
    return dumps(space, w_x, space.newint(version))
