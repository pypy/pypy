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

class Bool(SPLIObject):

    def __init__(self, value):
        self.value = value

    def is_true(self):
        return self.value

class Int(SPLIObject):

    def __init__(self, value):
        self.value = value

    def add(self, other):
        if not isinstance(other, Int):
            raise W_TypeError
        return Int(self.value + other.value)

    def cmp_lt(self, other):
        if not isinstance(other, Int):
            raise W_TypeError
        return Bool(self.value < other.value)

class Str(SPLIObject):

    def __init__(self, value):
        self.value = value

    def add(self, other):
        if not isinstance(other, Str):
            raise W_TypeError
        return Str(self.value + other.value)

class SPLINone(SPLIObject):
    pass

spli_None = SPLINone()


class Function(SPLIObject):

    def __init__(self, code):
        self.code = code

    def call(self, args):
        from pypy.jit.tl.spli import interpreter
        return interpreter.SPLIFrame(self.code).run()
