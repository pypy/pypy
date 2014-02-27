from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError


class W_FlagsObject(W_Root):
    def __init__(self, arr):
        self.arr = arr
        self.flags = 0

    def descr_get_contiguous(self, space):
        return space.w_True

    def descr_get_fortran(self, space):
        return space.w_False

    def descr_get_writeable(self, space):
        return space.w_True

    def descr_get_fnc(self, space):
        return space.wrap(
            space.is_true(self.descr_get_fortran(space)) and not
            space.is_true(self.descr_get_contiguous(space)))

    def descr_get_forc(self, space):
        return space.wrap(
            space.is_true(self.descr_get_fortran(space)) or
            space.is_true(self.descr_get_contiguous(space)))

    def descr_getitem(self, space, w_item):
        key = space.str_w(w_item)
        if key == "C" or key == "CONTIGUOUS" or key == "C_CONTIGUOUS":
            return self.descr_get_contiguous(space)
        if key == "F" or key == "FORTRAN" or key == "F_CONTIGUOUS":
            return self.descr_get_fortran(space)
        if key == "W" or key == "WRITEABLE":
            return self.descr_get_writeable(space)
        if key == "FNC":
            return self.descr_get_fnc(space)
        if key == "FORC":
            return self.descr_get_forc(space)
        raise OperationError(space.w_KeyError, space.wrap(
            "Unknown flag"))

    def descr_setitem(self, space, w_item, w_value):
        raise OperationError(space.w_KeyError, space.wrap(
            "Unknown flag"))

    def eq(self, space, w_other):
        if not isinstance(w_other, W_FlagsObject):
            return False
        return self.flags == w_other.flags

    def descr_eq(self, space, w_other):
        return space.wrap(self.eq(space, w_other))

    def descr_ne(self, space, w_other):
        return space.wrap(not self.eq(space, w_other))

W_FlagsObject.typedef = TypeDef("flagsobj",
    __module__ = "numpy",
    __getitem__ = interp2app(W_FlagsObject.descr_getitem),
    __setitem__ = interp2app(W_FlagsObject.descr_setitem),
    __eq__ = interp2app(W_FlagsObject.descr_eq),
    __ne__ = interp2app(W_FlagsObject.descr_ne),

    contiguous = GetSetProperty(W_FlagsObject.descr_get_contiguous),
    c_contiguous = GetSetProperty(W_FlagsObject.descr_get_contiguous),
    f_contiguous = GetSetProperty(W_FlagsObject.descr_get_fortran),
    fortran = GetSetProperty(W_FlagsObject.descr_get_fortran),
    writeable = GetSetProperty(W_FlagsObject.descr_get_writeable),
    fnc = GetSetProperty(W_FlagsObject.descr_get_fnc),
    forc = GetSetProperty(W_FlagsObject.descr_get_forc),
)
