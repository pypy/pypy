import math

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.objspace.std import newformat
from pypy.objspace.std.floatobject import W_FloatObject, _hash_float
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.longobject import W_LongObject
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import GetSetProperty, StdTypeDef
from rpython.rlib import jit, rcomplex
from rpython.rlib.rarithmetic import intmask, r_ulonglong
from rpython.rlib.rbigint import rbigint
from rpython.rlib.rfloat import (
    formatd, DTSF_STR_PRECISION, isinf, isnan, copysign, string_to_float)
from rpython.rlib.rstring import ParseStringError


# ERRORCODES

ERR_WRONG_SECOND = "complex() can't take second arg if first is a string"
ERR_MALFORMED = "complex() arg is a malformed string"


class W_AbstractComplexObject(W_Object):
    __slots__ = ()

    def is_w(self, space, w_other):
        from rpython.rlib.longlong2float import float2longlong
        if not isinstance(w_other, W_AbstractComplexObject):
            return False
        if self.user_overridden_class or w_other.user_overridden_class:
            return self is w_other
        real1 = space.float_w(space.getattr(self,    space.wrap("real")))
        real2 = space.float_w(space.getattr(w_other, space.wrap("real")))
        imag1 = space.float_w(space.getattr(self,    space.wrap("imag")))
        imag2 = space.float_w(space.getattr(w_other, space.wrap("imag")))
        real1 = float2longlong(real1)
        real2 = float2longlong(real2)
        imag1 = float2longlong(imag1)
        imag2 = float2longlong(imag2)
        return real1 == real2 and imag1 == imag2

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        from rpython.rlib.longlong2float import float2longlong
        from pypy.objspace.std.model import IDTAG_COMPLEX as tag
        real = space.float_w(space.getattr(self, space.wrap("real")))
        imag = space.float_w(space.getattr(self, space.wrap("imag")))
        real_b = rbigint.fromrarith_int(float2longlong(real))
        imag_b = rbigint.fromrarith_int(r_ulonglong(float2longlong(imag)))
        val = real_b.lshift(64).or_(imag_b).lshift(3).or_(rbigint.fromint(tag))
        return space.newlong_from_rbigint(val)


def _split_complex(s):
    slen = len(s)
    if slen == 0:
        raise ValueError
    realstart = 0
    realstop = 0
    imagstart = 0
    imagstop = 0
    imagsign = ' '
    i = 0
    # ignore whitespace at beginning and end
    while i < slen and s[i] == ' ':
        i += 1
    while slen > 0 and s[slen-1] == ' ':
        slen -= 1

    if s[i] == '(' and s[slen-1] == ')':
        i += 1
        slen -= 1
        # ignore whitespace after bracket
        while i < slen and s[i] == ' ':
            i += 1

    # extract first number
    realstart = i
    pc = s[i]
    while i < slen and s[i] != ' ':
        if s[i] in ('+','-') and pc not in ('e','E') and i != realstart:
            break
        pc = s[i]
        i += 1

    realstop = i

    # ignore whitespace
    while i < slen and s[i] == ' ':
        i += 1

    # return appropriate strings is only one number is there
    if i >= slen:
        newstop = realstop - 1
        if newstop < 0:
            raise ValueError
        if s[newstop] in ('j', 'J'):
            if realstart == newstop:
                imagpart = '1.0'
            elif realstart == newstop-1 and s[realstart] == '+':
                imagpart = '1.0'
            elif realstart == newstop-1 and s[realstart] == '-':
                imagpart = '-1.0'
            else:
                imagpart = s[realstart:newstop]
            return '0.0', imagpart
        else:
            return s[realstart:realstop], '0.0'

    # find sign for imaginary part
    if s[i] == '-' or s[i] == '+':
        imagsign = s[i]
    if imagsign == ' ':
        raise ValueError

    i+=1
    # whitespace
    while i < slen and s[i] == ' ':
        i += 1
    if i >= slen:
        raise ValueError

    imagstart = i
    pc = s[i]
    while i < slen and s[i] != ' ':
        if s[i] in ('+','-') and pc not in ('e','E'):
            break
        pc = s[i]
        i += 1

    imagstop = i - 1
    if imagstop < 0:
        raise ValueError
    if s[imagstop] not in ('j','J'):
        raise ValueError
    if imagstop < imagstart:
        raise ValueError

    while i<slen and s[i] == ' ':
        i += 1
    if i <  slen:
        raise ValueError

    realpart = s[realstart:realstop]
    if imagstart == imagstop:
        imagpart = '1.0'
    else:
        imagpart = s[imagstart:imagstop]
    if imagsign == '-':
        imagpart = imagsign + imagpart

    return realpart, imagpart



def unpackcomplex(space, w_complex, strict_typing=True):
    """
    convert w_complex into a complex and return the unwrapped (real, imag)
    tuple. If strict_typing==True, we also typecheck the value returned by
    __complex__ to actually be a complex (and not e.g. a float).
    See test___complex___returning_non_complex.
    """
    from pypy.objspace.std.complexobject import W_ComplexObject
    if type(w_complex) is W_ComplexObject:
        return (w_complex.realval, w_complex.imagval)
    #
    # test for a '__complex__' method, and call it if found.
    # special case old-style instances, like CPython does.
    w_z = None
    if space.is_oldstyle_instance(w_complex):
        try:
            w_method = space.getattr(w_complex, space.wrap('__complex__'))
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
        else:
            w_z = space.call_function(w_method)
    else:
        w_method = space.lookup(w_complex, '__complex__')
        if w_method is not None:
            w_z = space.get_and_call_function(w_method, w_complex)
    #
    if w_z is not None:
        # __complex__() must return a complex or (float,int,long) object
        # (XXX should not use isinstance here)
        if not strict_typing and (space.isinstance_w(w_z, space.w_int) or
                                  space.isinstance_w(w_z, space.w_long) or
                                  space.isinstance_w(w_z, space.w_float)):
            return (space.float_w(w_z), 0.0)
        elif isinstance(w_z, W_ComplexObject):
            return (w_z.realval, w_z.imagval)
        raise OperationError(space.w_TypeError,
                             space.wrap("__complex__() must return"
                                        " a complex number"))

    #
    # no '__complex__' method, so we assume it is a float,
    # unless it is an instance of some subclass of complex.
    if space.isinstance_w(w_complex, space.gettypefor(W_ComplexObject)):
        real = space.float(space.getattr(w_complex, space.wrap("real")))
        imag = space.float(space.getattr(w_complex, space.wrap("imag")))
        return (space.float_w(real), space.float_w(imag))
    #
    # Check that it is not a string (on which space.float() would succeed).
    if (space.isinstance_w(w_complex, space.w_str) or
        space.isinstance_w(w_complex, space.w_unicode)):
        raise oefmt(space.w_TypeError,
                    "complex number expected, got '%T'", w_complex)
    #
    return (space.float_w(space.float(w_complex)), 0.0)


class W_ComplexObject(W_AbstractComplexObject):
    """This is a reimplementation of the CPython "PyComplexObject"
    """
    _immutable_fields_ = ['realval', 'imagval']

    def __init__(self, realval=0.0, imgval=0.0):
        self.realval = float(realval)
        self.imagval = float(imgval)

    def unwrap(self, space):   # for tests only
        return complex(self.realval, self.imagval)

    def __repr__(self):
        """ representation for debugging purposes """
        return "<W_ComplexObject(%f,%f)>" % (self.realval, self.imagval)

    def as_tuple(self):
        return (self.realval, self.imagval)

    def sub(self, other):
        return W_ComplexObject(self.realval - other.realval,
                               self.imagval - other.imagval)

    def mul(self, other):
        r = self.realval * other.realval - self.imagval * other.imagval
        i = self.realval * other.imagval + self.imagval * other.realval
        return W_ComplexObject(r, i)

    def div(self, other):
        rr, ir = rcomplex.c_div(self.as_tuple(), other.as_tuple())
        return W_ComplexObject(rr, ir)

    def divmod(self, space, other):
        space.warn(space.wrap("complex divmod(), // and % are deprecated"),
                   space.w_DeprecationWarning)
        w_div = self.div(other)
        div = math.floor(w_div.realval)
        w_mod = self.sub(
            W_ComplexObject(other.realval * div, other.imagval * div))
        return (W_ComplexObject(div, 0), w_mod)

    def pow(self, other):
        rr, ir = rcomplex.c_pow(self.as_tuple(), other.as_tuple())
        return W_ComplexObject(rr, ir)

    def pow_small_int(self, n):
        if n >= 0:
            if jit.isconstant(n) and n == 2:
                return self.mul(self)
            return self.pow_positive_int(n)
        else:
            return w_one.div(self.pow_positive_int(-n))

    def pow_positive_int(self, n):
        mask = 1
        w_result = w_one
        while mask > 0 and n >= mask:
            if n & mask:
                w_result = w_result.mul(self)
            mask <<= 1
            self = self.mul(self)

        return w_result

    def int(self, space):
        raise OperationError(space.w_TypeError, space.wrap("can't convert complex to int; use int(abs(z))"))

    @staticmethod
    @unwrap_spec(w_real = WrappedDefault(0.0))
    def descr__new__(space, w_complextype, w_real, w_imag=None):
        from pypy.objspace.std.complexobject import W_ComplexObject

        # if w_real is already a complex number and there is no second
        # argument, return it.  Note that we cannot return w_real if
        # it is an instance of a *subclass* of complex, or if w_complextype
        # is itself a subclass of complex.
        noarg2 = w_imag is None
        if (noarg2 and space.is_w(w_complextype, space.w_complex)
                   and space.is_w(space.type(w_real), space.w_complex)):
            return w_real

        if space.isinstance_w(w_real, space.w_str) or \
                space.isinstance_w(w_real, space.w_unicode):
            # a string argument
            if not noarg2:
                raise OperationError(space.w_TypeError,
                                     space.wrap("complex() can't take second arg"
                                                " if first is a string"))
            try:
                realstr, imagstr = _split_complex(space.str_w(w_real))
            except ValueError:
                raise OperationError(space.w_ValueError, space.wrap(ERR_MALFORMED))
            try:
                realval = string_to_float(realstr)
                imagval = string_to_float(imagstr)
            except ParseStringError:
                raise OperationError(space.w_ValueError, space.wrap(ERR_MALFORMED))

        else:
            # non-string arguments
            realval, imagval = unpackcomplex(space, w_real, strict_typing=False)

            # now take w_imag into account
            if not noarg2:
                # complex(x, y) == x+y*j, even if 'y' is already a complex.
                realval2, imagval2 = unpackcomplex(space, w_imag, strict_typing=False)

                # try to preserve the signs of zeroes of realval and realval2
                if imagval2 != 0.0:
                    realval -= imagval2

                if imagval != 0.0:
                    imagval += realval2
                else:
                    imagval = realval2
        # done
        w_obj = space.allocate_instance(W_ComplexObject, w_complextype)
        W_ComplexObject.__init__(w_obj, realval, imagval)
        return w_obj

    def descr___getnewargs__(self, space):
        return space.newtuple([space.newfloat(self.realval),
                               space.newfloat(self.imagval)])

    def descr_conjugate(self, space):
        """(A+Bj).conjugate() -> A-Bj"""
        return space.newcomplex(self.realval, -self.imagval)

    def descr_add(self, space, w_rhs):
        w_rhs = to_complex(space, w_rhs)
        return W_ComplexObject(self.realval + w_rhs.realval,
                               self.imagval + w_rhs.imagval)

    def descr_radd(self, space, w_lhs):
        w_lhs = to_complex(space, w_lhs)
        return W_ComplexObject(w_lhs.realval + self.realval,
                               w_lhs.imagval + self.imagval)

    def descr_sub(self, space, w_rhs):
        w_rhs = to_complex(space, w_rhs)
        return W_ComplexObject(self.realval - w_rhs.realval,
                               self.imagval - w_rhs.imagval)

    def descr_rsub(self, space, w_lhs):
        w_lhs = to_complex(space, w_lhs)
        return W_ComplexObject(w_lhs.realval - self.realval,
                               w_lhs.imagval - self.imagval)

    def descr_mul(self, space, w_rhs):
        w_rhs = to_complex(space, w_rhs)
        return self.mul(w_rhs)

    def descr_truediv(self, space, w_rhs):
        w_rhs = to_complex(space, w_rhs)
        try:
            return self.div(w_rhs)
        except ZeroDivisionError, e:
            raise OperationError(space.w_ZeroDivisionError, space.wrap(str(e)))

    def descr_floordiv(self, space, w_rhs):
        w_rhs = to_complex(space, w_rhs)
        w_rhs = to_complex(space, w_rhs)
        # don't care about the slight slowdown you get from using divmod
        try:
            return self.divmod(space, w_rhs)[0]
        except ZeroDivisionError, e:
            raise OperationError(space.w_ZeroDivisionError, space.wrap(str(e)))

    def descr_mod(self, space, w_rhs):
        w_rhs = to_complex(space, w_rhs)
        try:
            return self.divmod(space, w_rhs)[1]
        except ZeroDivisionError, e:
            raise OperationError(space.w_ZeroDivisionError, space.wrap(str(e)))

    def descr_divmod(self, space, w_rhs):
        w_rhs = to_complex(space, w_rhs)
        try:
            div, mod = self.divmod(space, w_rhs)
        except ZeroDivisionError, e:
            raise OperationError(space.w_ZeroDivisionError, space.wrap(str(e)))
        return space.newtuple([div, mod])

    @unwrap_spec(w_third_arg=WrappedDefault(None))
    def descr_pow(self, space, w_exponent, w_third_arg):
        w_exponent = to_complex(space, w_exponent)
        if not space.is_w(w_third_arg, space.w_None):
            raise OperationError(space.w_ValueError, space.wrap('complex modulo'))
        try:
            r = w_exponent.realval
            if w_exponent.imagval == 0.0 and -100.0 <= r <= 100.0 and r == int(r):
                w_p = self.pow_small_int(int(r))
            else:
                w_p = self.pow(w_exponent)
        except ZeroDivisionError:
            raise OperationError(space.w_ZeroDivisionError, space.wrap("0.0 to a negative or complex power"))
        except OverflowError:
            raise OperationError(space.w_OverflowError, space.wrap("complex exponentiation"))
        return w_p

registerimplementation(W_ComplexObject)

w_one = W_ComplexObject(1, 0)


def to_complex(space, w_obj):
    if isinstance(w_obj, W_ComplexObject):
        return w_obj
    if space.isinstance_w(w_obj, space.w_bool):
        return W_ComplexObject(w_obj.intval, 0.0)
    if space.isinstance_w(w_obj, space.w_int):
        return W_ComplexObject(w_obj.intval, 0.0)
    if space.isinstance_w(w_obj, space.w_long):
        dval = w_obj.tofloat(space)
        return W_ComplexObject(dval, 0.0)
    if space.isinstance_w(w_obj, space.w_float):
        return W_ComplexObject(w_obj.floatval, 0.0)

def hash__Complex(space, w_value):
    hashreal = _hash_float(space, w_value.realval)
    hashimg = _hash_float(space, w_value.imagval)
    combined = intmask(hashreal + 1000003 * hashimg)
    return space.newint(combined)

def neg__Complex(space, w_complex):
    return W_ComplexObject(-w_complex.realval, -w_complex.imagval)

def pos__Complex(space, w_complex):
    return W_ComplexObject(w_complex.realval, w_complex.imagval)

def abs__Complex(space, w_complex):
    try:
        return space.newfloat(math.hypot(w_complex.realval, w_complex.imagval))
    except OverflowError, e:
        raise OperationError(space.w_OverflowError, space.wrap(str(e)))

def eq__Complex_Complex(space, w_complex1, w_complex2):
    return space.newbool((w_complex1.realval == w_complex2.realval) and
            (w_complex1.imagval == w_complex2.imagval))

def ne__Complex_Complex(space, w_complex1, w_complex2):
    return space.newbool((w_complex1.realval != w_complex2.realval) or
            (w_complex1.imagval != w_complex2.imagval))

def eq__Complex_Long(space, w_complex1, w_long2):
    if w_complex1.imagval:
        return space.w_False
    return space.eq(space.newfloat(w_complex1.realval), w_long2)
eq__Complex_Int = eq__Complex_Long

def eq__Long_Complex(space, w_long1, w_complex2):
    return eq__Complex_Long(space, w_complex2, w_long1)
eq__Int_Complex = eq__Long_Complex

def ne__Complex_Long(space, w_complex1, w_long2):
    if w_complex1.imagval:
        return space.w_True
    return space.ne(space.newfloat(w_complex1.realval), w_long2)
ne__Complex_Int = ne__Complex_Long

def ne__Long_Complex(space, w_long1, w_complex2):
    return ne__Complex_Long(space, w_complex2, w_long1)
ne__Int_Complex = ne__Long_Complex

def lt__Complex_Complex(space, w_complex1, w_complex2):
    raise OperationError(space.w_TypeError, space.wrap('cannot compare complex numbers using <, <=, >, >='))

gt__Complex_Complex = lt__Complex_Complex
ge__Complex_Complex = lt__Complex_Complex
le__Complex_Complex = lt__Complex_Complex

def nonzero__Complex(space, w_complex):
    return space.newbool((w_complex.realval != 0.0) or
                         (w_complex.imagval != 0.0))

def coerce__Complex_ANY(space, w_complex1, w_complex2):
    w_complex2 = to_complex(space, w_complex2)
    return space.newtuple([w_complex1, w_complex2])

def float__Complex(space, w_complex):
    raise OperationError(space.w_TypeError, space.wrap("can't convert complex to float; use abs(z)"))

def format_float(x, code, precision):
    # like float2string, except that the ".0" is not necessary
    if isinf(x):
        if x > 0.0:
            return "inf"
        else:
            return "-inf"
    elif isnan(x):
        return "nan"
    else:
        return formatd(x, code, precision)

def repr_format(x):
    return format_float(x, 'r', 0)
def str_format(x):
    return format_float(x, 'g', DTSF_STR_PRECISION)

def repr__Complex(space, w_complex):
    if w_complex.realval == 0 and copysign(1., w_complex.realval) == 1.:
        return space.wrap(repr_format(w_complex.imagval) + 'j')
    sign = (copysign(1., w_complex.imagval) == 1. or
            isnan(w_complex.imagval)) and '+' or ''
    return space.wrap('(' + repr_format(w_complex.realval)
                      + sign + repr_format(w_complex.imagval) + 'j)')

def str__Complex(space, w_complex):
    if w_complex.realval == 0 and copysign(1., w_complex.realval) == 1.:
        return space.wrap(str_format(w_complex.imagval) + 'j')
    sign = (copysign(1., w_complex.imagval) == 1. or
            isnan(w_complex.imagval)) and '+' or ''
    return space.wrap('(' + str_format(w_complex.realval)
                      + sign + str_format(w_complex.imagval) + 'j)')

def format__Complex_ANY(space, w_complex, w_format_spec):
    return newformat.run_formatter(space, w_format_spec, "format_complex", w_complex)

def complexwprop(name):
    def fget(space, w_obj):
        from pypy.objspace.std.complexobject import W_ComplexObject
        if not isinstance(w_obj, W_ComplexObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("descriptor is for 'complex'"))
        return space.newfloat(getattr(w_obj, name))
    return GetSetProperty(fget)

W_ComplexObject.typedef = StdTypeDef("complex",
    __doc__ = """complex(real[, imag]) -> complex number

Create a complex number from a real part and an optional imaginary part.
This is equivalent to (real + imag*1j) where imag defaults to 0.""",
    __new__ = interp2app(W_ComplexObject.descr__new__),
    __getnewargs__ = interp2app(W_ComplexObject.descr___getnewargs__),
    real = complexwprop('realval'),
    imag = complexwprop('imagval'),
    conjugate = interp2app(W_ComplexObject.descr_conjugate),

    __add__ = interp2app(W_ComplexObject.descr_add),
    __radd__ = interp2app(W_ComplexObject.descr_radd),
    __sub__ = interp2app(W_ComplexObject.descr_sub),
    __rsub__ = interp2app(W_ComplexObject.descr_rsub),
    __mul__ = interp2app(W_ComplexObject.descr_mul),
    __div__ = interp2app(W_ComplexObject.descr_truediv),
    __truediv__ = interp2app(W_ComplexObject.descr_truediv),
    __floordiv__ = interp2app(W_ComplexObject.descr_floordiv),
    __mod__ = interp2app(W_ComplexObject.descr_mod),
    __divmod__ = interp2app(W_ComplexObject.descr_divmod),
    __pow__ = interp2app(W_ComplexObject.descr_pow),
    )

W_ComplexObject.typedef.registermethods(globals())
register_all(vars(), globals())
