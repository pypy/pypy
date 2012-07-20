from pypy.interpreter.baseobjspace import ObjSpace, Wrappable
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
        elif isinstance(x, Wrappable):
            return x.__spacebind__(self)
        elif isinstance(x, SPLIObject):
            return x # Already done.
        else:
            raise NotImplementedError("Wrapping %s" % x)

    def new_interned_str(self, x):
        return self.wrap(x)


class SPLIException(Exception):
    pass


class W_TypeError(SPLIException):
    pass


class SPLIObject(object):

    def add(self, other):
        raise W_TypeError

    def sub(self, other):
        raise W_TypeError    

    def and_(self, other):
        raise W_TypeError    

    def call(self, args):
        raise W_TypeError

    def cmp_lt(self, other):
        raise W_TypeError

    def cmp_gt(self, other):
        raise W_TypeError

    def cmp_eq(self, other):
        raise W_TypeError

    def cmp_ne(self, other):
        raise W_TypeError

    def cmp_ge(self, other):
        raise W_TypeError

    def cmp_le(self, other):
        raise W_TypeError

    def as_int(self):
        raise W_TypeError

    def as_str(self):
        raise W_TypeError

    def repr(self):
        return Str("<SPLI object>")

    def is_true(self):
        raise W_TypeError

    def as_interp_class(self, cls):
        if not isinstance(self, cls):
            raise W_TypeError
        return self


class Bool(SPLIObject):

    def __init__(self, value):
        self.value = value

    def is_true(self):
        return self.value

    def repr(self):
        if self.is_true():
            name = "True"
        else:
            name = "False"
        return Str(name)


class Int(SPLIObject):

    def __init__(self, value):
        self.value = value

    def add(self, other):
        return Int(self.value + other.as_int())

    def sub(self, other):
        return Int(self.value - other.as_int())

    def and_(self, other):
        return Int(self.value & other.as_int())

    def cmp_lt(self, other):
        return Bool(self.value < other.as_int())

    def as_int(self):
        return self.value

    def is_true(self):
        return bool(self.value)

    def repr(self):
        return Str(str(self.value))


class Str(SPLIObject):

    def __init__(self, value):
        self.value = value

    def as_str(self):
        return self.value

    def add(self, other):
        return Str(self.value + other.as_str())

    def repr(self):
        return Str("'" + self.value + "'")


class SPLINone(SPLIObject):

    def repr(self):
        return Str('None')

spli_None = SPLINone()


class Function(SPLIObject):

    def __init__(self, code, globs):
        self.code = code
        self.globs = globs

    def call(self, args):
        from pypy.jit.tl.spli import execution
        return execution.run(self.code, args, None, self.globs)
