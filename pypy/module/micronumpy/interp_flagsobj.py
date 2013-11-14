from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError


class W_FlagsObject(W_Root):
    def __init__(self, arr):
        self.arr = arr

    def descr_get_contiguous(self, space):
        return space.w_True

    def descr_get_fortran(self, space):
        return space.w_False

    def descr_get_writeable(self, space):
        return space.w_True

    def descr_getitem(self, space, w_item):
        key = space.str_w(w_item)
        if key == "C" or key == "CONTIGUOUS" or key == "C_CONTIGUOUS":
            return self.descr_get_contiguous(space)
        if key == "F" or key == "FORTRAN" or key == "F_CONTIGUOUS":
            return self.descr_get_fortran(space)
        if key == "W" or key == "WRITEABLE":
            return self.descr_get_writeable(space)
        raise OperationError(space.w_KeyError, space.wrap(
            "Unknown flag"))

    def descr_setitem(self, space, w_item, w_value):
        raise OperationError(space.w_KeyError, space.wrap(
            "Unknown flag"))

W_FlagsObject.typedef = TypeDef("flagsobj",
    __module__ = "numpy",
    __getitem__ = interp2app(W_FlagsObject.descr_getitem),
    __setitem__ = interp2app(W_FlagsObject.descr_setitem),

    contiguous = GetSetProperty(W_FlagsObject.descr_get_contiguous),
    c_contiguous = GetSetProperty(W_FlagsObject.descr_get_contiguous),
    f_contiguous = GetSetProperty(W_FlagsObject.descr_get_fortran),
    fortran = GetSetProperty(W_FlagsObject.descr_get_fortran),
    writeable = GetSetProperty(W_FlagsObject.descr_get_writeable),
)
