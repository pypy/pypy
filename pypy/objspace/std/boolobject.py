import operator

from rpython.rlib.objectmodel import import_from_mixin
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.rbigint import rbigint
from rpython.tool.sourcetools import func_renamer, func_with_new_name

from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.objspace.std.intobject import (
    IntMethods, W_AbstractIntObject, W_IntObject)
from pypy.objspace.std.stdtypedef import StdTypeDef


class W_BoolObject(W_AbstractIntObject):
    import_from_mixin(IntMethods)

    _immutable_fields_ = ['boolval']

    def __init__(self, boolval):
        self.boolval = not not boolval

    def __nonzero__(self):
        raise Exception("you cannot do that, you must use space.is_true()")

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%s)" % (self.__class__.__name__, self.boolval)

    def unwrap(self, space):
        return self.boolval

    def int_w(self, space):
        return int(self.boolval)

    def uint_w(self, space):
        intval = int(self.boolval)
        return r_uint(intval)

    def bigint_w(self, space):
        return rbigint.fromint(int(self.boolval))

    def float_w(self, space):
        return float(self.boolval)

    def int(self, space):
        return space.newint(int(self.boolval))

    def descr_repr(self, space):
        return space.wrap('True' if self.boolval else 'False')
    descr_str = descr_repr

    def descr_nonzero(self, space):
        return self

    def make_bitwise_binop(opname):
        descr_name = 'descr_' + opname
        int_op = getattr(W_IntObject, descr_name)
        op = getattr(operator,
                     opname + '_' if opname in ('and', 'or') else opname)
        @func_renamer(descr_name)
        def descr_binop(self, space, w_other):
            if not isinstance(w_other, W_BoolObject):
                return int_op(self.int(space), space, w_other)
            return space.newbool(op(self.boolval, w_other.boolval))
        return descr_binop, func_with_new_name(descr_binop, 'descr_r' + opname)

    descr_and, descr_rand = make_bitwise_binop('and')
    descr_or, descr_ror = make_bitwise_binop('or')
    descr_xor, descr_rxor = make_bitwise_binop('xor')

W_BoolObject.w_False = W_BoolObject(False)
W_BoolObject.w_True = W_BoolObject(True)

@unwrap_spec(w_obj=WrappedDefault(False))
def descr__new__(space, w_booltype, w_obj):
    space.w_bool.check_user_subclass(w_booltype)
    return space.newbool(space.is_true(w_obj))

# ____________________________________________________________

W_BoolObject.typedef = StdTypeDef("bool", W_AbstractIntObject.typedef,
    __doc__ = """bool(x) -> bool

Returns True when the argument x is true, False otherwise.
The builtins True and False are the only two instances of the class bool.
The class bool is a subclass of the class int, and cannot be subclassed.""",
    __new__ = interp2app(descr__new__),
    __repr__ = interp2app(W_BoolObject.descr_repr),
    __str__ = interp2app(W_BoolObject.descr_str),
    __nonzero__ = interp2app(W_BoolObject.descr_nonzero),

    __and__ = interp2app(W_BoolObject.descr_and),
    __rand__ = interp2app(W_BoolObject.descr_rand),
    __or__ = interp2app(W_BoolObject.descr_or),
    __ror__ = interp2app(W_BoolObject.descr_ror),
    __xor__ = interp2app(W_BoolObject.descr_xor),
    __rxor__ = interp2app(W_BoolObject.descr_rxor),
    )
W_BoolObject.typedef.acceptable_as_base_class = False
