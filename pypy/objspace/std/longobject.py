import sys
from pypy.objspace.std.objspace import *
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.noneobject import W_NoneObject

class W_LongObject(W_Object):
    """This is a non-reimplementation of longs.
    It uses real CPython longs.
    XXX we must really choose another representation (e.g. list of ints)
    XXX and implement it in detail.
    """
    from pypy.objspace.std.longtype import long_typedef as typedef
    
    def __init__(w_self, space, longval=0L):
        W_Object.__init__(w_self, space)
        assert isinstance(longval, long)
        w_self.longval = longval

    def unwrap(w_self):
        return w_self.longval

registerimplementation(W_LongObject)


# bool-to-long
def delegate_Bool2Long(w_bool):
    return W_LongObject(w_bool.space, long(w_bool.boolval))

# int-to-long delegation
def delegate_Int2Long(w_intobj):
    return W_LongObject(w_intobj.space, long(w_intobj.intval))

# long-to-float delegation
def delegate_Long2Float(w_longobj):
    return W_FloatObject(w_longobj.space, float(w_longobj.longval))


# long__Long is supposed to do nothing, unless it has
# a derived long object, where it should return
# an exact one.
def long__Long(space, w_long1):
    if space.is_true(space.is_(space.type(w_long1), space.w_long)):
        return w_long1
    a = w_long1.longval
    return W_LongObject(space, a)

def long__Int(space, w_intobj):
    return W_LongObject(space, long(w_intobj.intval))

def int__Long(space, w_value):
    if -sys.maxint-1 <= w_value.longval <= sys.maxint:
        return space.newint(int(w_value.longval))
    else:
        return w_value   # 9999999999999L.__int__() == 9999999999999L

def float__Long(space, w_longobj):
    try:
        return space.newfloat(float(w_longobj.longval))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long int too large to convert to float"))

def long__Float(space, w_floatobj):
    # XXX cheating
    return W_LongObject(space, long(w_floatobj.floatval))

def int_w__Long(space, w_value):
    if -sys.maxint-1 <= w_value.longval <= sys.maxint:
        return int(w_value.longval)
    else:
        raise OperationError(space.w_OverflowError,
                             space.wrap("long int too large to convert to int"))        

def repr__Long(space, w_long):
    return space.wrap(repr(w_long.longval))

def str__Long(space, w_long):
    return space.wrap(str(w_long.longval))

def eq__Long_Long(space, w_long1, w_long2):
    i = w_long1.longval
    j = w_long2.longval
    return space.newbool( i == j )

def lt__Long_Long(space, w_long1, w_long2):
    i = w_long1.longval
    j = w_long2.longval
    return space.newbool( i < j )

def hash__Long(space,w_value):
    ## %reimplement%
    # real Implementation should be taken from _Py_HashDouble in object.c
    return space.wrap(hash(w_value.longval))

def add__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    z = x + y
    return W_LongObject(space, z)

def sub__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    z = x - y
    return W_LongObject(space, z)

def mul__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    z = x * y
    return W_LongObject(space, z)

def div__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    if not y:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division"))
    z = x / y
    return W_LongObject(space, z)

truediv__Long_Long = div__Long_Long

def floordiv__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    if not y:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long division"))
    z = x // y
    return W_LongObject(space, z)

def mod__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    if not y:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long modulo"))
    z = x % y
    return W_LongObject(space, z)

def divmod__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    if not y:
        raise OperationError(space.w_ZeroDivisionError,
                             space.wrap("long modulo"))
    z1, z2 = divmod(x, y)
    return space.newtuple([W_LongObject(space, z1),
                           W_LongObject(space, z2)])

def pow__Long_Long_None(space, w_long1, w_long2, w_none3):
    x = w_long1.longval
    y = w_long2.longval
    if y < 0:
        return space.pow(space.float(w_long1),
                         space.float(w_long2),
                         space.w_None)        
    z = x ** y
    return W_LongObject(space, z)

def pow__Long_Long_Long(space, w_long1, w_long2, w_long3):
    x = w_long1.longval
    y = w_long2.longval
    z = w_long3.longval
    try:
        t = pow(x, y, z)
    except TypeError, e:
        raise OperationError(space.w_TypeError,
                             space.wrap(e.args[0]))
    except ValueError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.args[0]))
    return W_LongObject(space, t)

def neg__Long(space, w_long1):
    return W_LongObject(space, -w_long1.longval)

def pos__Long(space, w_long):
    return long__Long(space, w_long)

def abs__Long(space, w_long):
    return W_LongObject(space, abs(w_long.longval))

def nonzero__Long(space, w_long):
    return space.newbool(w_long.longval != 0L)

def invert__Long(space, w_long):
    return W_LongObject(space, ~w_long.longval)

def lshift__Long_Int(space, w_long1, w_int2):
    a = w_long1.longval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    res = a << b
    return W_LongObject(space, res)

def rshift__Long_Int(space, w_long1, w_int2):
    a = w_long1.longval
    b = w_int2.intval
    if b < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("negative shift count"))
    res = a >> b
    return W_LongObject(space, res)

def and__Long_Long(space, w_long1, w_long2):
    a = w_long1.longval
    b = w_long2.longval
    res = a & b
    return W_LongObject(space, res)

def xor__Long_Long(space, w_long1, w_long2):
    a = w_long1.longval
    b = w_long2.longval
    res = a ^ b
    return W_LongObject(space, res)

def or__Long_Long(space, w_long1, w_long2):
    a = w_long1.longval
    b = w_long2.longval
    res = a | b
    return W_LongObject(space, res)

def oct__Long(space, w_long1):
    x = w_long1.longval
    return space.wrap(oct(x))

def hex__Long(space, w_long1):
    x = w_long1.longval
    return space.wrap(hex(x))


register_all(vars())

# register implementations of ops that recover int op overflows

# binary ops
for opname in ['add', 'sub', 'mul', 'div', 'floordiv', 'truediv', 'mod', 'divmod']:
    exec """
def %(opname)s_ovr__Int_Int(space, w_int1, w_int2):
    w_long1 = delegate_Int2Long(w_int1)
    w_long2 = delegate_Int2Long(w_int2)
    return %(opname)s__Long_Long(space, w_long1, w_long2)
""" % {'opname': opname}

    getattr(StdObjSpace.MM, opname).register(globals()['%s_ovr__Int_Int' %opname], W_IntObject, W_IntObject, order=1)

# unary ops
for opname in ['neg', 'abs']:
    exec """
def %(opname)s_ovr__Int(space, w_int1):
    w_long1 = delegate_Int2Long(w_int1)
    return %(opname)s__Long(space, w_long1)
""" % {'opname': opname}

    getattr(StdObjSpace.MM, opname).register(globals()['%s_ovr__Int' %opname], W_IntObject, order=1)

# lshift
def lshift_ovr__Int_Int(space, w_int1, w_cnt):
    w_long1 = delegate_Int2Long(w_int1)
    return lshift__Long_Int(space, w_long1, w_cnt)

StdObjSpace.MM.lshift.register(lshift_ovr__Int_Int, W_IntObject, W_IntObject, order=1)

# pow
def pow_ovr__Int_Int_None(space, w_int1, w_int2, w_none3):
    w_long1 = delegate_Int2Long(w_int1)
    w_long2 = delegate_Int2Long(w_int2)
    return pow__Long_Long_None(space, w_long1, w_long2, w_none3)

def pow_ovr__Int_Int_Int(space, w_int1, w_int2, w_int3):
    w_long1 = delegate_Int2Long(w_int1)
    w_long2 = delegate_Int2Long(w_int2)
    w_long3 = delegate_Int2Long(w_int3)
    return pow__Long_Long_Long(space, w_long1, w_long2, w_long3)

StdObjSpace.MM.pow.register(pow_ovr__Int_Int_None, W_IntObject, W_IntObject, W_NoneObject, order=1)
StdObjSpace.MM.pow.register(pow_ovr__Int_Int_Int , W_IntObject, W_IntObject, W_IntObject,  order=1)
