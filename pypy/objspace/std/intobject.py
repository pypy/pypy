"""The builtin int implementation

In order to have the same behavior running on CPython, and after RPython
translation this module uses rarithmetic.ovfcheck to explicitly check
for overflows, something CPython does not do anymore.
"""

from rpython.rlib import jit
from rpython.rlib.rarithmetic import LONG_BIT, is_valid_int, ovfcheck, r_uint
from rpython.rlib.rbigint import rbigint

from pypy.interpreter.error import OperationError
from pypy.objspace.std import newformat
from pypy.objspace.std.inttype import W_AbstractIntObject
from pypy.objspace.std.model import W_Object, registerimplementation
from pypy.objspace.std.multimethod import FailedToImplementArgs
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.register_all import register_all


class W_IntObject(W_AbstractIntObject):
    __slots__ = 'intval'
    _immutable_fields_ = ['intval']

    from pypy.objspace.std.inttype import int_typedef as typedef

    def __init__(self, intval):
        assert is_valid_int(intval)
        self.intval = intval

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%d)" % (self.__class__.__name__, self.intval)

    def unwrap(self, space):
        return int(self.intval)
    int_w = unwrap

    def uint_w(self, space):
        intval = self.intval
        if intval < 0:
            raise OperationError(
                space.w_ValueError,
                space.wrap("cannot convert negative integer to unsigned"))
        else:
            return r_uint(intval)

    def bigint_w(self, space):
        return rbigint.fromint(self.intval)

    def float_w(self, space):
        return float(self.intval)

    def int(self, space):
        if (type(self) is not W_IntObject and
            space.is_overloaded(self, space.w_int, '__int__')):
            return W_Object.int(self, space)
        if space.is_w(space.type(self), space.w_int):
            return self
        a = self.intval
        return space.newint(a)

registerimplementation(W_IntObject)

def repr__Int(space, w_int1):
    a = w_int1.intval
    res = str(a)
    return space.wrap(res)

str__Int = repr__Int

def format__Int_ANY(space, w_int, w_format_spec):
    return newformat.run_formatter(space, w_format_spec, "format_int_or_long",
                                   w_int, newformat.INT_KIND)

def declare_new_int_comparison(opname):
    import operator
    from rpython.tool.sourcetools import func_with_new_name
    op = getattr(operator, opname)
    def f(space, w_int1, w_int2):
        i = w_int1.intval
        j = w_int2.intval
        return space.newbool(op(i, j))
    name = "%s__Int_Int" % (opname,)
    return func_with_new_name(f, name), name

for op in ['lt', 'le', 'eq', 'ne', 'gt', 'ge']:
    func, name = declare_new_int_comparison(op)
    globals()[name] = func

def hash__Int(space, w_int1):
    # unlike CPython, we don't special-case the value -1 in most of our
    # hash functions, so there is not much sense special-casing it here either.
    # Make sure this is consistent with the hash of floats and longs.
    return w_int1.int(space)

# coerce
def coerce__Int_Int(space, w_int1, w_int2):
    return space.newtuple([w_int1, w_int2])


def add__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x + y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer addition"))
    return space.newint(z)

def sub__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x - y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer substraction"))
    return space.newint(z)

def mul__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x * y)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer multiplication"))
    return space.newint(z)

def floordiv__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer division by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer division"))
    return space.newint(z)
div__Int_Int = floordiv__Int_Int

def truediv__Int_Int(space, w_int1, w_int2):
    x = float(w_int1.intval)
    y = float(w_int2.intval)
    if y == 0.0:
        raise FailedToImplementArgs(space.w_ZeroDivisionError,
                                    space.wrap("float division"))
    return space.wrap(x / y)

def mod__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x % y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer modulo by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer modulo"))
    return space.newint(z)

def divmod__Int_Int(space, w_int1, w_int2):
    x = w_int1.intval
    y = w_int2.intval
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("integer divmod by zero"))
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer modulo"))
    # no overflow possible
    m = x % y
    w = space.wrap
    return space.newtuple([w(z), w(m)])


# helper for pow()
@jit.look_inside_iff(lambda space, iv, iw, iz:
                     jit.isconstant(iw) and jit.isconstant(iz))
def _impl_int_int_pow(space, iv, iw, iz):
    if iw < 0:
        if iz != 0:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        ## bounce it, since it always returns float
        raise FailedToImplementArgs(space.w_ValueError,
                                space.wrap("integer exponentiation"))
    temp = iv
    ix = 1
    try:
        while iw > 0:
            if iw & 1:
                ix = ovfcheck(ix*temp)
            iw >>= 1   #/* Shift exponent down by 1 bit */
            if iw==0:
                break
            temp = ovfcheck(temp*temp) #/* Square the value of temp */
            if iz:
                #/* If we did a multiplication, perform a modulo */
                ix = ix % iz;
                temp = temp % iz;
        if iz:
            ix = ix % iz
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer exponentiation"))
    return ix

def pow__Int_Int_Int(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    z = w_int3.intval
    if z == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("pow() 3rd argument cannot be 0"))
    return space.wrap(_impl_int_int_pow(space, x, y, z))

def pow__Int_Int_None(space, w_int1, w_int2, w_int3):
    x = w_int1.intval
    y = w_int2.intval
    return space.wrap(_impl_int_int_pow(space, x, y, 0))

def neg__Int(space, w_int1):
    a = w_int1.intval
    try:
        x = ovfcheck(-a)
    except OverflowError:
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer negation"))
    return space.newint(x)
get_negint = neg__Int


def abs__Int(space, w_int1):
    if w_int1.intval >= 0:
        return w_int1.int(space)
    else:
        return get_negint(space, w_int1)

def nonzero__Int(space, w_int1):
    return space.newbool(w_int1.intval != 0)

def invert__Int(space, w_int1):
    x = w_int1.intval
    a = ~x
    return space.newint(a)

def lshift__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if r_uint(b) < LONG_BIT: # 0 <= b < LONG_BIT
        try:
            c = ovfcheck(a << b)
        except OverflowError:
            raise FailedToImplementArgs(space.w_OverflowError,
                                    space.wrap("integer left shift"))
        return space.newint(c)
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    else: #b >= LONG_BIT
        if a == 0:
            return w_int1.int(space)
        raise FailedToImplementArgs(space.w_OverflowError,
                                space.wrap("integer left shift"))

def rshift__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    if r_uint(b) >= LONG_BIT: # not (0 <= b < LONG_BIT)
        if b < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("negative shift count"))
        else: # b >= LONG_BIT
            if a == 0:
                return w_int1.int(space)
            if a < 0:
                a = -1
            else:
                a = 0
    else:
        a = a >> b
    return space.newint(a)

def and__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a & b
    return space.newint(res)

def xor__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a ^ b
    return space.newint(res)

def or__Int_Int(space, w_int1, w_int2):
    a = w_int1.intval
    b = w_int2.intval
    res = a | b
    return space.newint(res)

def pos__Int(self, space):
    return self.int(space)
trunc__Int = pos__Int

def index__Int(space, w_int1):
    return w_int1.int(space)

def float__Int(space, w_int1):
    a = w_int1.intval
    x = float(a)
    return space.newfloat(x)

def oct__Int(space, w_int1):
    return space.wrap(oct(w_int1.intval))

def hex__Int(space, w_int1):
    return space.wrap(hex(w_int1.intval))

def getnewargs__Int(space, w_int1):
    return space.newtuple([space.newint(w_int1.intval)])


register_all(vars())
