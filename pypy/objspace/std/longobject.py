"""
Reviewed 03-06-21
This isn't used at all, nor tested, and is totally cheating.
There isn't even any corresponding longtype.  Should perhaps
be just removed.
"""


from pypy.objspace.std.objspace import *



class W_LongObject(W_Object):
    
    def __init__(w_self, space, longval):
        W_Object.__init__(w_self, space)
        w_self.longval = longval

    def getattr(w_self, space, w_attrname):
        return applicationfile.call(space, "long_getattr", [w_self, w_attrname])


def long(space,w_value):
    return applicationfile.call(space,"long_long",[w_value])

def add__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x + y
    except OverflowError:
        raise OperationError(OverflowError, "long addition")
    return W_LongObject(space, z)

def sub__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x - y
    except Error,e:
        raise OperationError(Error, e)
    return W_LongObject(space, z)

def mul__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x * y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(space, z)

def floordiv__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x // y
    except ZeroDivisionError:
		raise   # we have to implement the exception or it will be ignored
	# no overflow
    return W_LongObject(space, z)

def truediv__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x / y   # XXX make sure this is the new true division
    except ZeroDivisionError:
		raise   # we have to implement the exception or it will be ignored
	# no overflow
    return W_LongObject(space, z)

if 1L / 2L == 1L // 2L:
	long_long_div = long_long_floordiv
else:
	long_long_div = long_long_truediv

def mod__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x % y
    except ZeroDivisionError:
		raise   # we have to implement the exception or it will be ignored
	# no overflow
    return W_LongObject(space, z)

def divmod__Long_Long(space, w_long1, w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
		z = x // y
		m = x % y
    except ZeroDivisionError:
		raise   # we have to implement the exception or it will be ignored
	# no overflow
    return W_TupleObject(space, [W_LongObject(space, z),
                                 W_LongObject(space, m)])

def pow__Long_Long(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x ** y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(space, z)

def pow__Long_Long_ANY(space, w_long1,w_long2,w_long3):
    x = w_long1.longval
    y = w_long2.longval
    z = w_long3.longval
    try:
        z = (x ** y) % z
    except Error,e:
        raise OperationError(Error(e), "long multiplication")
    return W_LongObject(space, z)

def lshift__Long_Long(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x << y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(space, z)

def rshift__Long_Long(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x >> y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(space, z)

def and__Long_Long(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x & y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(space, z)

def xor__Long_Long(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x ^ y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(space, z)

def or__Long_Long(space, w_long1,w_long2):
    x = w_long1.longval
    y = w_long2.longval
    try:
        z = x | y
    except OverflowError:
        raise OperationError(OverflowError, "long multiplication")
    return W_LongObject(space, z)


register_all(vars())
