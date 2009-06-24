from pypy.interpreter.baseobjspace import ObjSpace
from pypy.rlib.objectmodel import specialize

class DumbObjSpace(ObjSpace):
    """Implement just enough of the ObjSpace API to satisfy PyCode."""

    @specialize.argtype(1)
    def wrap(self, x):
        if isinstance(x, int):
            return Int(x)
        elif isinstance(x, str):
            return Str(x)
        elif x is None:
            return spli_None
        else:
            raise NotImplementedError("Wrapping %s" % x)

    def new_interned_str(self, x):
        return self.wrap(x)

class InvalidOperation(Exception):
    pass

class SPLIException(Exception):
    pass

class W_TypeError(SPLIException):
    pass

class SPLIObject(object):

    def add(self, other):
        raise InvalidOperation

    def call(self, args):
        raise InvalidOperation

    def cmp_lt(self, other):
        raise InvalidOperation

    def cmp_gt(self, other):
        raise InvalidOperation

    def cmp_eq(self, other):
        raise InvalidOperation

    def cmp_ne(self, other):
        raise InvalidOperation

    def cmp_ge(self, other):
        raise InvalidOperation

    def cmp_le(self, other):
        raise InvalidOperation

    def as_int(self):
        raise W_TypeError

    def as_str(self):
        raise W_TypeError


class Bool(SPLIObject):

    def __init__(self, value):
        self.value = value

    def is_true(self):
        return self.value


class Int(SPLIObject):

    def __init__(self, value):
        self.value = value

    def add(self, other):
        return Int(self.value + other.as_int())

    def cmp_lt(self, other):
        return Bool(self.value < other.as_int())

    def as_int(self):
        return self.value


class Str(SPLIObject):

    def __init__(self, value):
        self.value = value

    def as_str(self):
        return self.value

    def add(self, other):
        return Str(self.value + other.as_str())


class SPLINone(SPLIObject):
    pass

spli_None = SPLINone()


class Function(SPLIObject):

    def __init__(self, code):
        self.code = code

    def call(self, args):
        from pypy.jit.tl.spli import interpreter
        return interpreter.SPLIFrame(self.code).run()
