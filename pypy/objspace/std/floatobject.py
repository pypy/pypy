import math
import operator
import sys

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault, interpindirect2app
from pypy.interpreter.typedef import GetSetProperty
from pypy.objspace.std import newformat
from pypy.objspace.std.longobject import W_LongObject
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from rpython.rlib import rarithmetic, rfloat
from rpython.rlib.rarithmetic import ovfcheck_float_to_int, intmask, LONG_BIT
from rpython.rlib.rfloat import (
    isinf, isnan, isfinite, INFINITY, NAN, copysign, formatd,
    DTSF_ADD_DOT_0, DTSF_STR_PRECISION, float_as_rbigint_ratio)
from rpython.rlib.rbigint import rbigint
from rpython.rlib.rstring import ParseStringError
from rpython.tool.sourcetools import func_with_new_name
from rpython.rlib.unroll import unrolling_iterable

from pypy.objspace.std.intobject import W_IntObject


float_as_integer_ratio = SMM("as_integer_ratio", 1)
float_is_integer = SMM("is_integer", 1)
float_hex = SMM("hex", 1)


class W_AbstractFloatObject(W_Object):
    __slots__ = ()

    def is_w(self, space, w_other):
        from rpython.rlib.longlong2float import float2longlong
        if not isinstance(w_other, W_AbstractFloatObject):
            return False
        if self.user_overridden_class or w_other.user_overridden_class:
            return self is w_other
        one = float2longlong(space.float_w(self))
        two = float2longlong(space.float_w(w_other))
        return one == two

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        from rpython.rlib.longlong2float import float2longlong
        from pypy.objspace.std.model import IDTAG_FLOAT as tag
        val = float2longlong(space.float_w(self))
        b = rbigint.fromrarith_int(val)
        b = b.lshift(3).or_(rbigint.fromint(tag))
        return space.newlong_from_rbigint(b)

    def int(self, space):
        raise NotImplementedError


def detect_floatformat():
    from rpython.rtyper.lltypesystem import rffi, lltype
    buf = lltype.malloc(rffi.CCHARP.TO, 8, flavor='raw')
    rffi.cast(rffi.DOUBLEP, buf)[0] = 9006104071832581.0
    packed = rffi.charpsize2str(buf, 8)
    if packed == "\x43\x3f\xff\x01\x02\x03\x04\x05":
        double_format = 'IEEE, big-endian'
    elif packed == "\x05\x04\x03\x02\x01\xff\x3f\x43":
        double_format = 'IEEE, little-endian'
    else:
        double_format = 'unknown'
    lltype.free(buf, flavor='raw')
    #
    buf = lltype.malloc(rffi.CCHARP.TO, 4, flavor='raw')
    rffi.cast(rffi.FLOATP, buf)[0] = rarithmetic.r_singlefloat(16711938.0)
    packed = rffi.charpsize2str(buf, 4)
    if packed == "\x4b\x7f\x01\x02":
        float_format = 'IEEE, big-endian'
    elif packed == "\x02\x01\x7f\x4b":
        float_format = 'IEEE, little-endian'
    else:
        float_format = 'unknown'
    lltype.free(buf, flavor='raw')

    return double_format, float_format

_double_format, _float_format = detect_floatformat()


def _string_to_float(space, w_source, string):
    try:
        return rfloat.string_to_float(string)
    except ParseStringError as e:
        from pypy.objspace.std.intobject import wrap_parsestringerror
        raise wrap_parsestringerror(space, e, w_source)


_alpha = zip("abcdef", range(10, 16)) + zip("ABCDEF", range(10, 16))
_hex_to_int = zip("0123456789", range(10)) + _alpha
_hex_to_int_iterable = unrolling_iterable(_hex_to_int)

def _hex_from_char(c):
    for h, v in _hex_to_int_iterable:
        if h == c:
            return v
    return -1

def _hex_digit(s, j, co_end, float_digits):
    if j < float_digits:
        i = co_end - j
    else:
        i = co_end - 1 - j
    return _hex_from_char(s[i])


class W_FloatObject(W_AbstractFloatObject):
    """This is a implementation of the app-level 'float' type.
    The constructor takes an RPython float as an argument."""
    _immutable_fields_ = ['floatval']

    def __init__(self, floatval):
        self.floatval = floatval

    def unwrap(self, space):
        return self.floatval

    def float_w(self, space):
        return self.floatval

    def int(self, space):
        if (type(self) is not W_FloatObject and
            space.is_overloaded(self, space.w_float, '__int__')):
            return W_Object.int(self, space)
        try:
            value = ovfcheck_float_to_int(self.floatval)
        except OverflowError:
            return space.long(self)
        else:
            return space.newint(value)

    def __repr__(self):
        return "<W_FloatObject(%f)>" % self.floatval

    @staticmethod
    @unwrap_spec(w_x=WrappedDefault(0.0))
    def descr__new__(space, w_floattype, w_x):
        from pypy.objspace.std.floatobject import W_FloatObject
        w_value = w_x     # 'x' is the keyword argument name in CPython
        if space.lookup(w_value, "__float__") is not None:
            w_obj = space.float(w_value)
            if space.is_w(w_floattype, space.w_float):
                return w_obj
            value = space.float_w(w_obj)
        elif (space.isinstance_w(w_value, space.w_str) or
              space.isinstance_w(w_value, space.w_bytearray)):
            value = _string_to_float(space, w_value, space.bufferstr_w(w_value))
        elif space.isinstance_w(w_value, space.w_unicode):
            from unicodeobject import unicode_to_decimal_w
            value = _string_to_float(space, w_value,
                                     unicode_to_decimal_w(space, w_value))
        else:
            value = space.float_w(w_x)
        w_obj = space.allocate_instance(W_FloatObject, w_floattype)
        W_FloatObject.__init__(w_obj, value)
        return w_obj

    @staticmethod
    @unwrap_spec(s=str)
    def descr_fromhex(space, w_cls, s):
        length = len(s)
        i = 0
        value = 0.0
        while i < length and s[i].isspace():
            i += 1
        if i == length:
            raise OperationError(space.w_ValueError,
                                 space.wrap("invalid hex string"))
        sign = 1
        if s[i] == "-":
            sign = -1
            i += 1
        elif s[i] == "+":
            i += 1
        if length == i:
            raise OperationError(space.w_ValueError,
                                 space.wrap("invalid hex string"))
        if s[i] == "i" or s[i] == "I":
            i += 1
            if length - i >= 2 and s[i:i + 2].lower() == "nf":
                i += 2
                value = rfloat.INFINITY
                if length - i >= 5 and s[i:i + 5].lower() == "inity":
                    i += 5
        elif s[i] == "n" or s[i] == "N":
            i += 1
            if length - i >= 2 and s[i:i + 2].lower() == "an":
                i += 2
                value = rfloat.NAN
        else:
            if (s[i] == "0" and length - i > 1 and
                (s[i + 1] == "x" or s[i + 1] == "X")):
                i += 2
            co_start = i
            while i < length and _hex_from_char(s[i]) >= 0:
                i += 1
            whole_end = i
            if i < length and s[i] == ".":
                i += 1
                while i < length and _hex_from_char(s[i]) >= 0:
                    i += 1
                co_end = i - 1
            else:
                co_end = i
            total_digits = co_end - co_start
            float_digits = co_end - whole_end
            if not total_digits:
                raise OperationError(space.w_ValueError,
                                     space.wrap("invalid hex string"))
            const_one = rfloat.DBL_MIN_EXP - rfloat.DBL_MANT_DIG + sys.maxint // 2
            const_two = sys.maxint // 2 + 1 - rfloat.DBL_MAX_EXP
            if total_digits > min(const_one, const_two) // 4:
                raise OperationError(space.w_ValueError, space.wrap("way too long"))
            if i < length and (s[i] == "p" or s[i] == "P"):
                i += 1
                if i == length:
                    raise OperationError(space.w_ValueError,
                                         space.wrap("invalid hex string"))
                exp_sign = 1
                if s[i] == "-" or s[i] == "+":
                    if s[i] == "-":
                        exp_sign = -1
                    i += 1
                    if i == length:
                        raise OperationError(space.w_ValueError,
                                             space.wrap("invalid hex string"))
                if not s[i].isdigit():
                    raise OperationError(space.w_ValueError,
                                         space.wrap("invalid hex string"))
                exp = ord(s[i]) - ord('0')
                i += 1
                while i < length and s[i].isdigit():
                    exp = exp * 10 + (ord(s[i]) - ord('0'))
                    if exp >= (sys.maxint-9) // 10:
                        if exp_sign > 0:
                            exp_sign = 2    # overflow in positive numbers
                        else:
                            exp_sign = -2   # overflow in negative numbers
                    i += 1
                if exp_sign == -1:
                    exp = -exp
                elif exp_sign == -2:
                    exp = -sys.maxint / 2
                elif exp_sign == 2:
                    exp = sys.maxint / 2
            else:
                exp = 0
            while (total_digits and
                   _hex_digit(s, total_digits - 1, co_end, float_digits) == 0):
                total_digits -= 1
            if not total_digits or exp <= -sys.maxint / 2:
                value = 0.0
            elif exp >= sys.maxint // 2:
                raise OperationError(space.w_OverflowError, space.wrap("too large"))
            else:
                exp -=  4 * float_digits
                top_exp = exp + 4 * (total_digits - 1)
                digit = _hex_digit(s, total_digits - 1, co_end, float_digits)
                while digit:
                    top_exp += 1
                    digit //= 2
                if top_exp < rfloat.DBL_MIN_EXP - rfloat.DBL_MANT_DIG:
                    value = 0.0
                elif top_exp > rfloat.DBL_MAX_EXP:
                    raise OperationError(space.w_OverflowError,
                                         space.wrap("too large"))
                else:
                    lsb = max(top_exp, rfloat.DBL_MIN_EXP) - rfloat.DBL_MANT_DIG
                    value = 0
                    if exp >= lsb:
                        for j in range(total_digits - 1, -1, -1):
                            value = 16.0 * value + _hex_digit(s, j, co_end,
                                                              float_digits)
                        value = math.ldexp(value, exp)
                    else:
                        half_eps = 1 << ((lsb - exp - 1) % 4)
                        key_digit = (lsb - exp - 1) // 4
                        for j in range(total_digits - 1, key_digit, -1):
                            value = 16.0 * value + _hex_digit(s, j, co_end,
                                                              float_digits)
                        digit = _hex_digit(s, key_digit, co_end, float_digits)
                        value = 16.0 * value + (digit & (16 - 2*half_eps))
                        if digit & half_eps:
                            round_up = False
                            if (digit & (3 * half_eps - 1) or
                                (half_eps == 8 and
                                 _hex_digit(s, key_digit + 1, co_end, float_digits) & 1)):
                                round_up = True
                            else:
                                for j in range(key_digit - 1, -1, -1):
                                    if _hex_digit(s, j, co_end, float_digits):
                                        round_up = True
                                        break
                            if round_up:
                                value += 2 * half_eps
                                mant_dig = rfloat.DBL_MANT_DIG
                                if (top_exp == rfloat.DBL_MAX_EXP and
                                    value == math.ldexp(2 * half_eps, mant_dig)):
                                    raise OperationError(space.w_OverflowError,
                                                         space.wrap("too large"))
                        value = math.ldexp(value, (exp + 4*key_digit))
        while i < length and s[i].isspace():
            i += 1
        if i != length:
            raise OperationError(space.w_ValueError,
                                 space.wrap("invalid hex string"))
        w_float = space.wrap(sign * value)
        return space.call_function(w_cls, w_float)

    def _to_float(self, space, w_obj):
        if isinstance(w_obj, W_FloatObject):
            return w_obj
        if space.isinstance_w(w_obj, space.w_int):
            return W_FloatObject(float(w_obj.intval))
        if space.isinstance_w(w_obj, space.w_long):
            return W_FloatObject(w_obj.tofloat(space))

    def descr_coerce(self, space, w_other):
        w_other = self._to_float(space, w_other)
        if w_other is None:
            return space.w_NotImplemented
        return space.newtuple([self, w_other])

    def descr_add(self, space, w_rhs):
        w_rhs = self._to_float(space, w_rhs)
        if w_rhs is None:
            return space.w_NotImplemented
        return W_FloatObject(self.floatval + w_rhs.floatval)

    def descr_radd(self, space, w_lhs):
        w_lhs = self._to_float(space, w_lhs)
        if w_lhs is None:
            return space.w_NotImplemented
        return W_FloatObject(w_lhs.floatval + self.floatval)

    def descr_sub(self, space, w_rhs):
        w_rhs = self._to_float(space, w_rhs)
        if w_rhs is None:
            return space.w_NotImplemented
        return W_FloatObject(self.floatval - w_rhs.floatval)

    def descr_rsub(self, space, w_lhs):
        w_lhs = self._to_float(space, w_lhs)
        if w_lhs is None:
            return space.w_NotImplemented
        return W_FloatObject(w_lhs.floatval - self.floatval)

    def descr_mul(self, space, w_rhs):
        w_rhs = self._to_float(space, w_rhs)
        if w_rhs is None:
            return space.w_NotImplemented
        return W_FloatObject(self.floatval * w_rhs.floatval)

    def descr_rmul(self, space, w_lhs):
        w_lhs = self._to_float(space, w_lhs)
        if w_lhs is None:
            return space.w_NotImplemented
        return W_FloatObject(w_lhs.floatval * self.floatval)

    def descr_div(self, space, w_rhs):
        w_rhs = self._to_float(space, w_rhs)
        if w_rhs is None:
            return space.w_NotImplemented
        rhs = w_rhs.floatval
        if rhs == 0.0:
            raise OperationError(space.w_ZeroDivisionError, space.wrap("float division"))
        return W_FloatObject(self.floatval / rhs)

    def descr_rdiv(self, space, w_lhs):
        w_lhs = self._to_float(space, w_lhs)
        if w_lhs is None:
            return space.w_NotImplemented
        lhs = w_lhs.floatval
        if lhs == 0.0:
            raise OperationError(space.w_ZeroDivisionError, space.wrap("float division"))
        return W_FloatObject(lhs / self.floatval)

    def descr_floordiv(self, space, w_rhs):
        w_rhs = self._to_float(space, w_rhs)
        if w_rhs is None:
            return space.w_NotImplemented
        return _divmod_w(space, self, w_rhs)[0]

    def descr_rfloordiv(self, space, w_lhs):
        w_lhs = self._to_float(space, w_lhs)
        if w_lhs is None:
            return space.w_NotImplemented
        return _divmod_w(space, w_lhs, self)[0]

    def descr_mod(self, space, w_rhs):
        w_rhs = self._to_float(space, w_rhs)
        if w_rhs is None:
            return space.w_NotImplemented
        x = self.floatval
        y = w_rhs.floatval
        if y == 0.0:
            raise OperationError(space.w_ZeroDivisionError, space.wrap("float modulo"))
        try:
            mod = math.fmod(x, y)
        except ValueError:
            mod = rfloat.NAN
        else:
            if mod:
                # ensure the remainder has the same sign as the denominator
                if (y < 0.0) != (mod < 0.0):
                    mod += y
            else:
                # the remainder is zero, and in the presence of signed zeroes
                # fmod returns different results across platforms; ensure
                # it has the same sign as the denominator; we'd like to do
                # "mod = y * 0.0", but that may get optimized away
                mod = copysign(0.0, y)

        return W_FloatObject(mod)

    def descr_rmod(self, space, w_lhs):
        w_lhs = self._to_float(space, w_lhs)
        if w_lhs is None:
            return space.w_NotImplemented
        return w_lhs.descr_mod(space, self)

    def descr_divmod(self, space, w_rhs):
        w_rhs = self._to_float(space, w_rhs)
        if w_rhs is None:
            return space.w_NotImplemented
        return space.newtuple(_divmod_w(space, self, w_rhs))

    def descr_rdivmod(self, space, w_lhs):
        w_lhs = self._to_float(space, w_lhs)
        if w_lhs is None:
            return space.w_NotImplemented
        return space.newtuple(_divmod_w(space, w_lhs, self))

    @unwrap_spec(w_third_arg=WrappedDefault(None))
    def descr_pow(self, space, w_rhs, w_third_arg):
        # This raises FailedToImplement in cases like overflow where a
        # (purely theoretical) big-precision float implementation would have
        # a chance to give a result, and directly OperationError for errors
        # that we want to force to be reported to the user.

        w_rhs = self._to_float(space, w_rhs)
        if w_rhs is None:
            return space.w_NotImplemented
        if not space.is_w(w_third_arg, space.w_None):
            raise OperationError(space.w_TypeError, space.wrap(
                "pow() 3rd argument not allowed unless all arguments are integers"))
        x = self.floatval
        y = w_rhs.floatval

        try:
            result = _pow(space, x, y)
        except PowDomainError:
            raise oefmt(space.w_ValueError,
                        "negative number cannot be raised to a fractional power")
        return W_FloatObject(result)

    @unwrap_spec(w_third_arg=WrappedDefault(None))
    def descr_rpow(self, space, w_lhs, w_third_arg):
        w_lhs = self._to_float(space, w_lhs)
        if w_lhs is None:
            return space.w_NotImplemented
        return w_lhs.descr_pow(space, self, w_third_arg)

    def descr_conjugate(self, space):
        return space.float(self)

    def descr_get_real(self, space):
        return space.float(self)

    def descr_get_imag(self, space):
        return space.wrap(0.0)

    @staticmethod
    @unwrap_spec(kind=str)
    def descr___getformat__(space, w_cls, kind):
        if kind == "float":
            return space.wrap(_float_format)
        elif kind == "double":
            return space.wrap(_double_format)
        raise OperationError(space.w_ValueError,
                             space.wrap("only float and double are valid"))


registerimplementation(W_FloatObject)

W_FloatObject.typedef = StdTypeDef("float",
    __doc__ = '''float(x) -> floating point number

Convert a string or number to a floating point number, if possible.''',
    __new__ = interp2app(W_FloatObject.descr__new__),
    __getformat__ = interp2app(W_FloatObject.descr___getformat__, as_classmethod=True),
    fromhex = interp2app(W_FloatObject.descr_fromhex, as_classmethod=True),
    __coerce__ = interp2app(W_FloatObject.descr_coerce),

    __add__ = interp2app(W_FloatObject.descr_add),
    __radd__ = interp2app(W_FloatObject.descr_radd),
    __sub__ = interp2app(W_FloatObject.descr_sub),
    __rsub__ = interp2app(W_FloatObject.descr_rsub),
    __mul__ = interp2app(W_FloatObject.descr_mul),
    __rmul__ = interp2app(W_FloatObject.descr_rmul),
    __div__ = interp2app(W_FloatObject.descr_div),
    __rdiv__ = interp2app(W_FloatObject.descr_rdiv),
    __truediv__ = interp2app(W_FloatObject.descr_div),
    __rtruediv__ = interp2app(W_FloatObject.descr_rdiv),
    __floordiv__ = interp2app(W_FloatObject.descr_floordiv),
    __rfloordiv__ = interp2app(W_FloatObject.descr_rfloordiv),
    __mod__ = interp2app(W_FloatObject.descr_mod),
    __rmod__ = interp2app(W_FloatObject.descr_rmod),
    __divmod__ = interp2app(W_FloatObject.descr_divmod),
    __rdivmod__ = interp2app(W_FloatObject.descr_rdivmod),
    __pow__ = interp2app(W_FloatObject.descr_pow),
    __rpow__ = interp2app(W_FloatObject.descr_rpow),

    conjugate = interp2app(W_FloatObject.descr_conjugate),
    real = GetSetProperty(W_FloatObject.descr_get_real),
    imag = GetSetProperty(W_FloatObject.descr_get_imag),
    __int__ = interpindirect2app(W_AbstractFloatObject.int),
)
W_FloatObject.typedef.registermethods(globals())


# float__Float is supposed to do nothing, unless it has
# a derived float object, where it should return
# an exact one.
def float__Float(space, w_float1):
    if space.is_w(space.type(w_float1), space.w_float):
        return w_float1
    a = w_float1.floatval
    return W_FloatObject(a)

def long__Float(space, w_floatobj):
    try:
        return W_LongObject.fromfloat(space, w_floatobj.floatval)
    except OverflowError:
        raise OperationError(
            space.w_OverflowError,
            space.wrap("cannot convert float infinity to integer"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("cannot convert float NaN to integer"))

def trunc__Float(space, w_floatobj):
    whole = math.modf(w_floatobj.floatval)[1]
    try:
        value = ovfcheck_float_to_int(whole)
    except OverflowError:
        return long__Float(space, w_floatobj)
    else:
        return space.newint(value)

def _char_from_hex(number):
    return "0123456789abcdef"[number]

TOHEX_NBITS = rfloat.DBL_MANT_DIG + 3 - (rfloat.DBL_MANT_DIG + 2) % 4

def float_hex__Float(space, w_float):
    value = w_float.floatval
    if not isfinite(value):
        return str__Float(space, w_float)
    if value == 0.0:
        if copysign(1., value) == -1.:
            return space.wrap("-0x0.0p+0")
        else:
            return space.wrap("0x0.0p+0")
    mant, exp = math.frexp(value)
    shift = 1 - max(rfloat.DBL_MIN_EXP - exp, 0)
    mant = math.ldexp(mant, shift)
    mant = abs(mant)
    exp -= shift
    result = ['\0'] * ((TOHEX_NBITS - 1) // 4 + 2)
    result[0] = _char_from_hex(int(mant))
    mant -= int(mant)
    result[1] = "."
    for i in range((TOHEX_NBITS - 1) // 4):
        mant *= 16.0
        result[i + 2] = _char_from_hex(int(mant))
        mant -= int(mant)
    if exp < 0:
        sign = "-"
    else:
        sign = "+"
    exp = abs(exp)
    s = ''.join(result)
    if value < 0.0:
        return space.wrap("-0x%sp%s%d" % (s, sign, exp))
    else:
        return space.wrap("0x%sp%s%d" % (s, sign, exp))

def float2string(x, code, precision):
    # we special-case explicitly inf and nan here
    if isfinite(x):
        s = formatd(x, code, precision, DTSF_ADD_DOT_0)
    elif isinf(x):
        if x > 0.0:
            s = "inf"
        else:
            s = "-inf"
    else:  # isnan(x):
        s = "nan"
    return s

def repr__Float(space, w_float):
    return space.wrap(float2string(w_float.floatval, 'r', 0))

def str__Float(space, w_float):
    return space.wrap(float2string(w_float.floatval, 'g', DTSF_STR_PRECISION))

def format__Float_ANY(space, w_float, w_spec):
    return newformat.run_formatter(space, w_spec, "format_float", w_float)

# ____________________________________________________________
# A mess to handle all cases of float comparison without relying
# on delegation, which can unfortunately loose precision when
# casting an int or a long to a float.

def list_compare_funcs(declarator):
    for op in ['lt', 'le', 'eq', 'ne', 'gt', 'ge']:
        func, name = declarator(op)
        globals()[name] = func_with_new_name(func, name)

def _reverse(opname):
    if opname[0] == 'l': return 'g' + opname[1:]
    elif opname[0] == 'g': return 'l' + opname[1:]
    else: return opname


def declare_compare_bigint(opname):
    """Return a helper function that implements a float-bigint comparison."""
    op = getattr(operator, opname)
    #
    if opname == 'eq' or opname == 'ne':
        def do_compare_bigint(f1, b2):
            """f1 is a float.  b2 is a bigint."""
            if not isfinite(f1) or math.floor(f1) != f1:
                return opname == 'ne'
            b1 = rbigint.fromfloat(f1)
            res = b1.eq(b2)
            if opname == 'ne':
                res = not res
            return res
    else:
        def do_compare_bigint(f1, b2):
            """f1 is a float.  b2 is a bigint."""
            if not isfinite(f1):
                return op(f1, 0.0)
            if opname == 'gt' or opname == 'le':
                # 'float > long'   <==>  'ceil(float) > long'
                # 'float <= long'  <==>  'ceil(float) <= long'
                f1 = math.ceil(f1)
            else:
                # 'float < long'   <==>  'floor(float) < long'
                # 'float >= long'  <==>  'floor(float) >= long'
                f1 = math.floor(f1)
            b1 = rbigint.fromfloat(f1)
            return getattr(b1, opname)(b2)
    #
    return do_compare_bigint, 'compare_bigint_' + opname
list_compare_funcs(declare_compare_bigint)


def declare_cmp_float_float(opname):
    op = getattr(operator, opname)
    def f(space, w_float1, w_float2):
        f1 = w_float1.floatval
        f2 = w_float2.floatval
        return space.newbool(op(f1, f2))
    return f, opname + "__Float_Float"
list_compare_funcs(declare_cmp_float_float)

def declare_cmp_float_int(opname):
    op = getattr(operator, opname)
    compare = globals()['compare_bigint_' + opname]
    def f(space, w_float1, w_int2):
        f1 = w_float1.floatval
        i2 = w_int2.intval
        f2 = float(i2)
        if LONG_BIT > 32 and int(f2) != i2:
            res = compare(f1, rbigint.fromint(i2))
        else:
            res = op(f1, f2)
        return space.newbool(res)
    return f, opname + "__Float_Int"
list_compare_funcs(declare_cmp_float_int)

def declare_cmp_float_long(opname):
    compare = globals()['compare_bigint_' + opname]
    def f(space, w_float1, w_long2):
        f1 = w_float1.floatval
        b2 = w_long2.num
        return space.newbool(compare(f1, b2))
    return f, opname + "__Float_Long"
list_compare_funcs(declare_cmp_float_long)

def declare_cmp_int_float(opname):
    op = getattr(operator, opname)
    revcompare = globals()['compare_bigint_' + _reverse(opname)]
    def f(space, w_int1, w_float2):
        f2 = w_float2.floatval
        i1 = w_int1.intval
        f1 = float(i1)
        if LONG_BIT > 32 and int(f1) != i1:
            res = revcompare(f2, rbigint.fromint(i1))
        else:
            res = op(f1, f2)
        return space.newbool(res)
    return f, opname + "__Int_Float"
list_compare_funcs(declare_cmp_int_float)

def declare_cmp_long_float(opname):
    revcompare = globals()['compare_bigint_' + _reverse(opname)]
    def f(space, w_long1, w_float2):
        f2 = w_float2.floatval
        b1 = w_long1.num
        return space.newbool(revcompare(f2, b1))
    return f, opname + "__Long_Float"
list_compare_funcs(declare_cmp_long_float)


# ____________________________________________________________

def hash__Float(space, w_value):
    return space.wrap(_hash_float(space, w_value.floatval))

def _hash_float(space, v):
    if isnan(v):
        return 0

    # This is designed so that Python numbers of different types
    # that compare equal hash to the same value; otherwise comparisons
    # of mapping keys will turn out weird.
    fractpart, intpart = math.modf(v)

    if fractpart == 0.0:
        # This must return the same hash as an equal int or long.
        try:
            x = ovfcheck_float_to_int(intpart)
            # Fits in a C long == a Python int, so is its own hash.
            return x
        except OverflowError:
            # Convert to long and use its hash.
            try:
                w_lval = W_LongObject.fromfloat(space, v)
            except (OverflowError, ValueError):
                # can't convert to long int -- arbitrary
                if v < 0:
                    return -271828
                else:
                    return 314159
            return space.int_w(space.hash(w_lval))

    # The fractional part is non-zero, so we don't have to worry about
    # making this match the hash of some other type.
    # Use frexp to get at the bits in the double.
    # Since the VAX D double format has 56 mantissa bits, which is the
    # most of any double format in use, each of these parts may have as
    # many as (but no more than) 56 significant bits.
    # So, assuming sizeof(long) >= 4, each part can be broken into two
    # longs; frexp and multiplication are used to do that.
    # Also, since the Cray double format has 15 exponent bits, which is
    # the most of any double format in use, shifting the exponent field
    # left by 15 won't overflow a long (again assuming sizeof(long) >= 4).

    v, expo = math.frexp(v)
    v *= 2147483648.0  # 2**31
    hipart = int(v)    # take the top 32 bits
    v = (v - hipart) * 2147483648.0 # get the next 32 bits
    x = intmask(hipart + int(v) + (expo << 15))
    return x


def _divmod_w(space, w_float1, w_float2):
    x = w_float1.floatval
    y = w_float2.floatval
    if y == 0.0:
        raise OperationError(space.w_ZeroDivisionError, space.wrap("float modulo"))
    try:
        mod = math.fmod(x, y)
    except ValueError:
        return [W_FloatObject(rfloat.NAN), W_FloatObject(rfloat.NAN)]
    # fmod is typically exact, so vx-mod is *mathematically* an
    # exact multiple of wx.  But this is fp arithmetic, and fp
    # vx - mod is an approximation; the result is that div may
    # not be an exact integral value after the division, although
    # it will always be very close to one.
    div = (x - mod) / y
    if (mod):
        # ensure the remainder has the same sign as the denominator
        if ((y < 0.0) != (mod < 0.0)):
            mod += y
            div -= 1.0
    else:
        # the remainder is zero, and in the presence of signed zeroes
        # fmod returns different results across platforms; ensure
        # it has the same sign as the denominator; we'd like to do
        # "mod = wx * 0.0", but that may get optimized away
        mod *= mod  # hide "mod = +0" from optimizer
        if y < 0.0:
            mod = -mod
    # snap quotient to nearest integral value
    if div:
        floordiv = math.floor(div)
        if (div - floordiv > 0.5):
            floordiv += 1.0
    else:
        # div is zero - get the same sign as the true quotient
        div *= div  # hide "div = +0" from optimizers
        floordiv = div * x / y  # zero w/ sign of vx/wx

    return [W_FloatObject(floordiv), W_FloatObject(mod)]

class PowDomainError(ValueError):
    """Signals a negative number raised to a fractional power"""

def _pow(space, x, y):
    # Sort out special cases here instead of relying on pow()
    if y == 2.0:       # special case for performance:
        return x * x   # x * x is always correct
    if y == 0.0:
        # x**0 is 1, even 0**0
        return 1.0
    if isnan(x):
        # nan**y = nan, unless y == 0
        return x
    if isnan(y):
        # x**nan = nan, unless x == 1; x**nan = x
        if x == 1.0:
            return 1.0
        else:
            return y
    if isinf(y):
        # x**inf is: 0.0 if abs(x) < 1; 1.0 if abs(x) == 1; inf if
        # abs(x) > 1 (including case where x infinite)
        #
        # x**-inf is: inf if abs(x) < 1; 1.0 if abs(x) == 1; 0.0 if
        # abs(x) > 1 (including case where v infinite)
        x = abs(x)
        if x == 1.0:
            return 1.0
        elif (y > 0.0) == (x > 1.0):
            return INFINITY
        else:
            return 0.0
    if isinf(x):
        # (+-inf)**w is: inf for w positive, 0 for w negative; in oth
        # cases, we need to add the appropriate sign if w is an odd
        # integer.
        y_is_odd = math.fmod(abs(y), 2.0) == 1.0
        if y > 0.0:
            if y_is_odd:
                return x
            else:
                return abs(x)
        else:
            if y_is_odd:
                return copysign(0.0, x)
            else:
                return 0.0

    if x == 0.0:
        if y < 0.0:
            raise OperationError(space.w_ZeroDivisionError,
                                 space.wrap("0.0 cannot be raised to "
                                            "a negative power"))

    negate_result = False
    # special case: "(-1.0) ** bignum" should not raise PowDomainError,
    # unlike "math.pow(-1.0, bignum)".  See http://mail.python.org/
    # -           pipermail/python-bugs-list/2003-March/016795.html
    if x < 0.0:
        if isnan(y):
            return NAN
        if math.floor(y) != y:
            raise PowDomainError
        # y is an exact integer, albeit perhaps a very large one.
        # Replace x by its absolute value and remember to negate the
        # pow result if y is odd.
        x = -x
        negate_result = math.fmod(abs(y), 2.0) == 1.0

    if x == 1.0:
        # (-1) ** large_integer also ends up here
        if negate_result:
            return -1.0
        else:
            return 1.0

    try:
        # We delegate to our implementation of math.pow() the error detection.
        z = math.pow(x,y)
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                                    space.wrap("float power"))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("float power"))

    if negate_result:
        z = -z
    return z


def neg__Float(space, w_float1):
    return W_FloatObject(-w_float1.floatval)

def pos__Float(space, w_float):
    return float__Float(space, w_float)

def abs__Float(space, w_float):
    return W_FloatObject(abs(w_float.floatval))

def nonzero__Float(space, w_float):
    return space.newbool(w_float.floatval != 0.0)

def getnewargs__Float(space, w_float):
    return space.newtuple([W_FloatObject(w_float.floatval)])

def float_as_integer_ratio__Float(space, w_float):
    value = w_float.floatval
    try:
        num, den = float_as_rbigint_ratio(value)
    except OverflowError:
        w_msg = space.wrap("cannot pass infinity to as_integer_ratio()")
        raise OperationError(space.w_OverflowError, w_msg)
    except ValueError:
        w_msg = space.wrap("cannot pass nan to as_integer_ratio()")
        raise OperationError(space.w_ValueError, w_msg)

    w_num = space.newlong_from_rbigint(num)
    w_den = space.newlong_from_rbigint(den)
    # Try to return int
    return space.newtuple([space.int(w_num), space.int(w_den)])

def float_is_integer__Float(space, w_float):
    v = w_float.floatval
    if not rfloat.isfinite(v):
        return space.w_False
    return space.wrap(math.floor(v) == v)

register_all(vars(), globals())
