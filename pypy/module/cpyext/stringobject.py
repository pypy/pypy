from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref, Py_ssize_t

@cpython_api([rffi.CCHARP, Py_ssize_t], PyObject)
def PyString_FromStringAndSize(char_p, length):
    l = []
    i = 0
    while length > 0:
        l.append(cp[i])
        i += 1
        length -= 1
    return "".join(l)

