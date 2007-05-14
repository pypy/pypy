import sys
from pypy.objspace.std.objspace import *
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.rlib.rbigint import rbigint, SHIFT

class W_LongObject(W_Object):
    """This is a wrapper of rbigint."""
    from pypy.objspace.std.longtype import long_typedef as typedef
    
    def __init__(w_self, l):
        w_self.num = l # instance of rbigint

    def fromint(space, intval):
        return W_LongObject(rbigint.fromint(intval))
    fromint = staticmethod(fromint)

    def longval(self):
        return self.num.tolong()

    def unwrap(w_self, space): #YYYYYY
        return w_self.longval()

    def tofloat(self):
        return self.num.tofloat()

    def toint(self):
        return self.num.toint()

    def fromfloat(f):
        return W_LongObject(rbigint.fromfloat(f))
    fromfloat = staticmethod(fromfloat)

    def fromlong(l):
        return W_LongObject(rbigint.fromlong(l))
    fromlong = staticmethod(fromlong)

    def fromrarith_int(i):
        return W_LongObject(rbigint.fromrarith_int(i))
    fromrarith_int._annspecialcase_ = "specialize:argtype(0)"
    fromrarith_int = staticmethod(fromrarith_int)

    def fromdecimalstr(s):
        return W_LongObject(rbigint.fromdecimalstr(s))
    fromdecimalstr = staticmethod(fromdecimalstr)

    def _count_bits(self):
        return self.num._count_bits()

    def is_odd(self):
        return self.num.is_odd()

    def get_sign(self):
        return self.num.sign

registerimplementation(W_LongObject)

# bool-to-long
def delegate_Bool2Long(space, w_bool):
    return W_LongObject(rbigint.frombool(space.is_true(w_bool)))

# int-to-long delegation
def delegate_Int2Long(space, w_intobj):
    return long__Int(space, w_intobj)


# long__Long is supposed to do nothing, unless it has
# a derived long object, where it should return
# an exact one.
def long__Long(space, w_long1):
    if space.is_w(space.type(w_long1), space.w_long):
        return w_long1
    l = w_long1.num
    return W_LongObject(l)

def long__Int(space, w_intobj):
    return W_LongObject.fromint(space, w_intobj.intval)

def int__Long(space, w_value):
    try:
        return space.newint(w_value.num.toint())
    except OverflowError:
        return long__Long(space, w_value)

def index__Long(space, w_value):
    return long__Long(space, w_value)

def float__Long(space, w_longobj):
    try:
        return space.newfloat(w_longobj.num.tofloat())
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long int too large to convert to float"))

def int_w__Long(space, w_value):
    try:
        return w_value.num.toint()
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.wrap(
            "long int too large to convert to int"))


def uint_w__Long(space, w_value):
    try:
        return w_value.num.touint()
    except ValueError:
        raise OperationError(space.w_ValueError, space.wrap(
            "cannot convert negative integer to unsigned int"))
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.wrap(
            "long int too large to convert to unsigned int"))

def bigint_w__Long(space, w_value):
    return w_value.num

def repr__Long(space, w_long):
    return space.wrap(w_long.num.repr())

def str__Long(space, w_long):
    return space.wrap(w_long.num.str())

def eq__Long_Long(space, w_long1, w_long2):
    return space.newbool(w_long1.num.eq(w_long2.num))

def lt__Long_Long(space, w_long1, w_long2):
    return space.newbool(w_long1.num.lt(w_long2.num))

def hash__Long(space, w_value):
    return space.wrap(w_value.num.hash())

# coerce
def coerce__Long_Long(space, w_long1, w_long2):
    return space.newtuple([w_long1, w_long2])


def add__Long_Long(space, w_long1, w_long2):
    return W_LongObject(w_long1.num.add(w_long2.num))

def sub__Long_Long(space, w_long1, w_long2):
    return W_LongObject(w_long1.num.sub(w_long2.num))

def mul__Long_Long(space, w_long1, w_long2):
    return W_LongObject(w_long1.num.mul(w_long2.num))

def truediv__Long_Long(space, w_long1, w_long2):
    try:
        return space.newfloat(w_long1.num.truediv(w_long2.num))
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division or modulo by zero"))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long/long too large for a float"))

def floordiv__Long_Long(space, w_long1, w_long2):
    try:
        return W_LongObject(w_long1.num.floordiv(w_long2.num))
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division or modulo by zero"))

def div__Long_Long(space, w_long1, w_long2):
    return floordiv__Long_Long(space, w_long1, w_long2)

def mod__Long_Long(space, w_long1, w_long2):
    try:
        return W_LongObject(w_long1.num.mod(w_long2.num))
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division or modulo by zero"))

def divmod__Long_Long(space, w_long1, w_long2):
    try:
        div, mod = w_long1.num.divmod(w_long2.num)
        return space.newtuple([W_LongObject(div), W_LongObject(mod)])
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division or modulo by zero"))

def pow__Long_Long_Long(space, w_long1, w_long2, w_long3):
    # XXX need to replicate some of the logic, to get the errors right
    if w_long2.num.lt(rbigint.fromint(0)):
        raise OperationError(
            space.w_TypeError,
            space.wrap(
                "pow() 2nd argument "
                "cannot be negative when 3rd argument specified"))
    try:
        return W_LongObject(w_long1.num.pow(w_long2.num, w_long3.num))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("pow 3rd argument cannot be 0"))

def pow__Long_Long_None(space, w_long1, w_long2, w_long3):
    # XXX need to replicate some of the logic, to get the errors right
    if w_long2.num.lt(rbigint.fromint(0)):
        raise FailedToImplement(
            space.w_ValueError,
            space.wrap("long pow() too negative"))
    return W_LongObject(w_long1.num.pow(w_long2.num, None))

def neg__Long(space, w_long1):
    return W_LongObject(w_long1.num.neg())

def pos__Long(space, w_long):
    return long__Long(space, w_long)

def abs__Long(space, w_long):
    return W_LongObject(w_long.num.abs())

def nonzero__Long(space, w_long):
    return space.newbool(w_long.num.tobool())

def invert__Long(space, w_long):
    return W_LongObject(w_long.num.invert())

def lshift__Long_Long(space, w_long1, w_long2):
    # XXX need to replicate some of the logic, to get the errors right
    if w_long2.num.lt(rbigint.fromint(0)):
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    try:
        return W_LongObject(w_long1.num.lshift(w_long2.num))
    except OverflowError:   # b too big
        raise OperationError(space.w_OverflowError,
                             space.wrap("shift count too large"))

def rshift__Long_Long(space, w_long1, w_long2):
    # XXX need to replicate some of the logic, to get the errors right
    if w_long2.num.lt(rbigint.fromint(0)):
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    try:
        return W_LongObject(w_long1.num.rshift(w_long2.num))
    except OverflowError:   # b too big # XXX maybe just return 0L instead?
        raise OperationError(space.w_OverflowError,
                             space.wrap("shift count too large"))

def and__Long_Long(space, w_long1, w_long2):
    return W_LongObject(w_long1.num.and_(w_long2.num))

def xor__Long_Long(space, w_long1, w_long2):
    return W_LongObject(w_long1.num.xor(w_long2.num))

def or__Long_Long(space, w_long1, w_long2):
    return W_LongObject(w_long1.num.or_(w_long2.num))

def oct__Long(space, w_long1):
    return space.wrap(w_long1.num.oct())

def hex__Long(space, w_long1):
    return space.wrap(w_long1.num.hex())

def getnewargs__Long(space, w_long1):
    return space.newtuple([W_LongObject(w_long1.num)])

register_all(vars())

# register implementations of ops that recover int op overflows

# binary ops
for opname in ['add', 'sub', 'mul', 'div', 'floordiv', 'truediv', 'mod', 'divmod', 'lshift']:
    exec compile("""
def %(opname)s_ovr__Int_Int(space, w_int1, w_int2):
    w_long1 = delegate_Int2Long(space, w_int1)
    w_long2 = delegate_Int2Long(space, w_int2)
    return %(opname)s__Long_Long(space, w_long1, w_long2)
""" % {'opname': opname}, '', 'exec')

    getattr(StdObjSpace.MM, opname).register(globals()['%s_ovr__Int_Int' % opname], W_IntObject, W_IntObject, order=1)

# unary ops
for opname in ['neg', 'abs']:
    exec """
def %(opname)s_ovr__Int(space, w_int1):
    w_long1 = delegate_Int2Long(space, w_int1)
    return %(opname)s__Long(space, w_long1)
""" % {'opname': opname}

    getattr(StdObjSpace.MM, opname).register(globals()['%s_ovr__Int' % opname], W_IntObject, order=1)

# pow
def pow_ovr__Int_Int_None(space, w_int1, w_int2, w_none3):
    w_long1 = delegate_Int2Long(space, w_int1)
    w_long2 = delegate_Int2Long(space, w_int2)
    return pow__Long_Long_None(space, w_long1, w_long2, w_none3)

def pow_ovr__Int_Int_Long(space, w_int1, w_int2, w_long3):
    w_long1 = delegate_Int2Long(space, w_int1)
    w_long2 = delegate_Int2Long(space, w_int2)
    return pow__Long_Long_Long(space, w_long1, w_long2, w_long3)

StdObjSpace.MM.pow.register(pow_ovr__Int_Int_None, W_IntObject, W_IntObject, W_NoneObject, order=1)
StdObjSpace.MM.pow.register(pow_ovr__Int_Int_Long, W_IntObject, W_IntObject, W_LongObject, order=1)


