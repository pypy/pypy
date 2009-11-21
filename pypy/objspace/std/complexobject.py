from pypy.interpreter import gateway
from pypy.objspace.std.objspace import W_Object, OperationError
from pypy.objspace.std.objspace import registerimplementation, register_all
from pypy.objspace.std.floatobject import W_FloatObject, _hash_float

import math

class W_ComplexObject(W_Object):
    """This is a reimplementation of the CPython "PyComplexObject"
    """
    from pypy.objspace.std.complextype import complex_typedef as typedef
    _immutable_ = True

    def __init__(w_self, realval=0.0, imgval=0.0):
        w_self.realval = float(realval)
        w_self.imagval = float(imgval)

    def unwrap(w_self, space):   # for tests only
        return complex(w_self.realval, w_self.imagval)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "<W_ComplexObject(%f,%f)>" % (w_self.realval, w_self.imagval)

registerimplementation(W_ComplexObject)

c_1 = (1.0, 0.0)

def _sum(c1, c2):
    return (c1[0]+c2[0],c1[1]+c2[1])

def _diff(c1, c2):
    return (c1[0]-c2[0],c1[1]-c2[1])

def _prod(c1, c2):
    r = c1[0]*c2[0] - c1[1]*c2[1]
    i = c1[0]*c2[1] + c1[1]*c2[0]
    return (r,i)

def _quot(c1,c2):
    r1, i1 = c1
    r2, i2 = c2
    if r2 < 0:
        abs_r2 = - r2
    else:
        abs_r2 = r2
    if i2 < 0:
        abs_i2 = - i2
    else:
        abs_i2 = i2
    if abs_r2 >= abs_i2:
        if abs_r2 == 0.0:
            raise ZeroDivisionError
        else:
            ratio = i2 / r2
            denom = r2 + i2 * ratio
            rr = (r1 + i1 * ratio) / denom
            ir = (i1 - r1 * ratio) / denom
    else:
        ratio = r2 / i2
        denom = r2 * ratio + i2
        assert i2 != 0.0
        rr = (r1 * ratio + i1) / denom
        ir = (i1 * ratio - r1) / denom
    return (rr,ir)

def _pow(c1,c2):
    r1, i1 = c1
    r2, i2 = c2
    if r2 == 0.0 and i2 == 0.0:
        rr, ir = c_1
    elif r1 == 0.0 and i1 == 0.0:
        if i2 != 0.0 or r2 < 0.0:
            raise ZeroDivisionError
        rr, ir = (0.0, 0.0)
    else:
        vabs = math.hypot(r1,i1)
        len = math.pow(vabs,r2)
        at = math.atan2(i1,r1)
        phase = at * r2
        if i2 != 0.0:
            len /= math.exp(at * i2)
            phase += i2 * math.log(vabs)
        rr = len * math.cos(phase)
        ir = len * math.sin(phase)
    return (rr, ir)

def _powu(c,n):
    mask = 1;
    rr, ir = c_1
    rp = c[0]
    ip = c[1]
    while mask > 0 and n >= mask:
        if n & mask:
            rr, ir = _prod((rr, ir), (rp, ip))
        mask <<= 1
        rp, ip = _prod((rp, ip), (rp, ip))

    return (rr, ir)

def _powi(c,n):
    if n > 100 or n < -100:
        return _pow(c,(1.0 * n, 0.0))
    elif n > 0:
        return _powu(c, n)
    else:
        return _quot(c_1, _powu(c, -n))



def delegate_Bool2Complex(space, w_bool):
    return W_ComplexObject(w_bool.boolval, 0.0)

def delegate_Int2Complex(space, w_int):
    return W_ComplexObject(w_int.intval, 0.0)

def delegate_Long2Complex(space, w_long):
    try:
        dval =  w_long.tofloat()
    except OverflowError, e:
        raise OperationError(space.w_OverflowError, space.wrap(str(e)))
    return W_ComplexObject(dval, 0.0)

def delegate_Float2Complex(space, w_float):
    return W_ComplexObject(w_float.floatval, 0.0)

def hash__Complex(space, w_value):
    #this is straight out of CPython complex implementation

    hashreal = _hash_float(space, w_value.realval)
    if hashreal == -1:
        return space.newint(-1)
    hashimg = _hash_float(space, w_value.imagval)
    if hashimg == -1:
        return space.newint(-1)
    combined = hashreal + 1000003 * hashimg
    if (combined == -1):
        combined = -2
    return space.newint(combined)

def _w2t(space, w_complex):
    "convert an interplevel complex object to a tuple representation"
    return w_complex.realval, w_complex.imagval

def _t2w(space, c):
    return W_ComplexObject(c[0], c[1])

def add__Complex_Complex(space, w_complex1, w_complex2):
    return _t2w(space, _sum(_w2t(space, w_complex1), _w2t(space, w_complex2)))

def sub__Complex_Complex(space, w_complex1, w_complex2):
    return _t2w(space, _diff(_w2t(space, w_complex1), _w2t(space, w_complex2)))

def mul__Complex_Complex(space, w_complex1, w_complex2):
    return _t2w(space, _prod(_w2t(space, w_complex1), _w2t(space, w_complex2)))

def div__Complex_Complex(space, w_complex1, w_complex2):
    try:
        return _t2w(space, _quot(_w2t(space, w_complex1), _w2t(space, w_complex2)))
    except ZeroDivisionError, e:
        raise OperationError(space.w_ZeroDivisionError, space.wrap(str(e)))

truediv__Complex_Complex = div__Complex_Complex

def mod__Complex_Complex(space, w_complex1, w_complex2):
    try:
        div = _quot(_w2t(space, w_complex1), _w2t(space, w_complex2))
    except ZeroDivisionError, e:
        raise OperationError(space.w_ZeroDivisionError, space.wrap("complex remainder"))
    div = (math.floor(div[0]), 0.0)
    mod = _diff(_w2t(space, w_complex1), _prod(_w2t(space, w_complex2), div))

    return _t2w(space, mod)

def divmod__Complex_Complex(space, w_complex1, w_complex2):
    try:
        div = _quot(_w2t(space, w_complex1), _w2t(space, w_complex2))
    except ZeroDivisionError, e:
        raise OperationError(space.w_ZeroDivisionError, space.wrap("complex divmod()"))
    div = (math.floor(div[0]), 0.0)
    mod = _diff(_w2t(space, w_complex1), _prod(_w2t(space, w_complex2), div))
    w_div = _t2w(space, div)
    w_mod = _t2w(space, mod)
    return space.newtuple([w_div, w_mod])

def floordiv__Complex_Complex(space, w_complex1, w_complex2):
    try:
        div = _quot(_w2t(space, w_complex1), _w2t(space, w_complex2))
    except ZeroDivisionError, e:
        raise OperationError(space.w_ZeroDivisionError, space.wrap("complex floordiv()"))
    div = (math.floor(div[0]), 0.0)
    return _t2w(space, div)

def pow__Complex_Complex_ANY(space, w_complex1, w_complex2, thirdArg):
    if not space.is_w(thirdArg, space.w_None):
        raise OperationError(space.w_ValueError, space.wrap('complex modulo'))
    try:
        v = _w2t(space, w_complex1)
        exponent = _w2t(space, w_complex2)
        int_exponent = int(exponent[0])
        if exponent[1] == 0.0 and exponent[0] == int_exponent:
            p = _powi(v, int_exponent)
        else:
            p = _pow(v, exponent)
    except ZeroDivisionError:
        raise OperationError(space.w_ZeroDivisionError, space.wrap("0.0 to a negative or complex power"))
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.wrap("complex exponentiation"))
    return _t2w(space, p)

def neg__Complex(space, w_complex):
    return W_ComplexObject(-w_complex.realval, -w_complex.imagval)

def pos__Complex(space, w_complex):
    return W_ComplexObject(w_complex.realval, w_complex.imagval)

def abs__Complex(space, w_complex):
    return space.newfloat(math.hypot(w_complex.realval, w_complex.imagval))

def eq__Complex_Complex(space, w_complex1, w_complex2):
    return space.newbool((w_complex1.realval == w_complex2.realval) and 
            (w_complex1.imagval == w_complex2.imagval))

def ne__Complex_Complex(space, w_complex1, w_complex2):
    return space.newbool((w_complex1.realval != w_complex2.realval) or 
            (w_complex1.imagval != w_complex2.imagval))

def lt__Complex_Complex(space, w_complex1, w_complex2):
    raise OperationError(space.w_TypeError, space.wrap('cannot compare complex numbers using <, <=, >, >='))

gt__Complex_Complex = lt__Complex_Complex
ge__Complex_Complex = lt__Complex_Complex
le__Complex_Complex = lt__Complex_Complex

def nonzero__Complex(space, w_complex):
    return space.newbool((w_complex.realval != 0.0) or
                         (w_complex.imagval != 0.0))

def coerce__Complex_Complex(space, w_complex1, w_complex2):
    return space.newtuple([w_complex1, w_complex2])

def float__Complex(space, w_complex):
    raise OperationError(space.w_TypeError, space.wrap("can't convert complex to float; use abs(z)"))

def int__Complex(space, w_complex):
    raise OperationError(space.w_TypeError, space.wrap("can't convert complex to int; use int(abs(z))"))

def complex_conjugate__Complex(space, w_self):
    #w_real = space.call_function(space.w_float,space.wrap(w_self.realval))
    #w_imag = space.call_function(space.w_float,space.wrap(-w_self.imagval))
    return space.newcomplex(w_self.realval,-w_self.imagval)

app = gateway.applevel(""" 
    import math
    def possint(f):
        ff = math.floor(f)
        if f == ff:
            return int(ff)
        return f

    def repr__Complex(f):
        if not f.real:
            return repr(possint(f.imag))+'j'
        imag = f.imag
        sign = ((imag >= 0) and '+') or ''
        return '('+repr(possint(f.real)) + sign + repr(possint(f.imag))+'j)'

    def str__Complex(f):
        if not f.real:
            return str(possint(f.imag))+'j'
        imag = f.imag
        sign = ((imag >= 0) and '+') or ''
        return '('+str(possint(f.real)) + sign + str(possint(f.imag))+'j)'

""", filename=__file__) 

repr__Complex = app.interphook('repr__Complex') 
str__Complex = app.interphook('str__Complex') 

from pypy.objspace.std import complextype
register_all(vars(), complextype)
