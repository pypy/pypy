from pypy.objspace.std.objspace import *



class W_LongObject(W_Object):
    
    def __init__(w_self, space, longval):
        W_Object.__init__(w_self, space)
        w_self.longval = longval

    def getattr(w_self, space, w_attrname):
        return applicationfile.call(space, "long_getattr", [w_self, w_attrname])


def long(space,w_value):
    return applicationfile.call(space,"long_long",[w_value])

def long_long_add(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x + y
    except OverflowError:
        raise OperationError(OverflowError, "long addition")
    return W_LongObject(z)

def long_long_sub(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x - y
    except Error,e:
        raise OperationError(Error, e)
    return W_LongObject(z)

def long_long_mul(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x * y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(z)

def long_long_floordiv(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x // y
    except ZeroDivisionError:
		raise   # we have to implement the exception or it will be ignored
	# no overflow
    return W_LongObject(z)

def long_long_truediv(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x / y   # XXX make sure this is the new true division
    except ZeroDivisionError:
		raise   # we have to implement the exception or it will be ignored
	# no overflow
    return W_LongObject(z)

if 1L / 2L == 1L // 2L:
	long_long_div = long_long_floordiv
else:
	long_long_div = long_long_truediv

def long_long_mod(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x % y
    except ZeroDivisionError:
		raise   # we have to implement the exception or it will be ignored
	# no overflow
    return W_LongObject(z)

def long_long_divmod(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
		z = x // y
		m = x % y
    except ZeroDivisionError:
		raise   # we have to implement the exception or it will be ignored
	# no overflow
    return W_TupleObject([z, m])

def long_long_pow(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x ** y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(z)

def long_long_long_pow(space, w_long1,w_long2,w_long3):
    x = w_long1.longval
    y = w_long2.longval
    z = w_long3.longval
    try:
        z = (x ** y) % z
    except Error,e:
        raise OperationError(Error(e), "long multiplication")
    return W_LongObject(z)

def long_long_lshift(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x << y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(z)

def long_long_rshift(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x >> y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(z)

def long_long_and(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x & y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(z)

def long_long_xor(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x ^ y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(z)

def long_long_or(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x | y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(z)



StdObjSpace.add.register(long_long_add, W_LongObject, W_LongObject)
StdObjSpace.sub.register(long_long_sub, W_LongObject, W_LongObject)
StdObjSpace.mul.register(long_long_mul, W_LongObject, W_LongObject)
StdObjSpace.div.register(long_long_div, W_LongObject, W_LongObject)
StdObjSpace.floordiv.register(long_long_floordiv, W_LongObject, W_LongObject)
StdObjSpace.truediv.register(long_long_truediv, W_LongObject, W_LongObject)
StdObjSpace.mod.register(long_long_mod, W_LongObject, W_LongObject)
StdObjSpace.divmod.register(long_long_divmod, W_LongObject, W_LongObject)
StdObjSpace.pow.register(long_long_pow, W_LongObject, W_LongObject)
StdObjSpace.pow.register(long_long_long_mod, W_LongObject, W_LongObject, W_LongObject)
StdObjSpace.lshift.register(long_long_lshift, W_LongObject, W_LongObject)
StdObjSpace.rshift.register(long_long_rshift, W_LongObject, W_LongObject)
StdObjSpace.and_.register(long_long_and, W_LongObject, W_LongObject)
StdObjSpace.xor.register(long_long_xor, W_LongObject, W_LongObject)
StdObjSpace.or_.register(long_long_or, W_LongObject, W_LongObject)

