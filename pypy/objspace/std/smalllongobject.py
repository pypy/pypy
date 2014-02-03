"""
Implementation of 'small' longs, stored as a r_longlong.
Useful for 32-bit applications manipulating values a bit larger than
fits in an 'int'.
"""
import operator

from rpython.rlib.rarithmetic import LONGLONG_BIT, intmask, r_longlong, r_uint
from rpython.rlib.rbigint import rbigint
from rpython.tool.sourcetools import func_renamer, func_with_new_name

from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import WrappedDefault, unwrap_spec
from pypy.objspace.std.intobject import W_AbstractIntObject
from pypy.objspace.std.longobject import W_AbstractLongObject, W_LongObject
from pypy.objspace.std.model import COMMUTATIVE_OPS

# XXX: breaks translation
#LONGLONG_MIN = r_longlong(-1 << (LONGLONG_BIT - 1))


class W_SmallLongObject(W_AbstractLongObject):

    _immutable_fields_ = ['longlong']

    def __init__(self, value):
        assert isinstance(value, r_longlong)
        self.longlong = value

    @staticmethod
    def fromint(value):
        return W_SmallLongObject(r_longlong(value))

    @staticmethod
    def frombigint(bigint):
        return W_SmallLongObject(bigint.tolonglong())

    def asbigint(self):
        return rbigint.fromrarith_int(self.longlong)

    def longval(self):
        return self.longlong

    def __repr__(self):
        return '<W_SmallLongObject(%d)>' % self.longlong

    def int_w(self, space):
        a = self.longlong
        b = intmask(a)
        if b == a:
            return b
        raise oefmt(space.w_OverflowError,
                    "long int too large to convert to int")

    def uint_w(self, space):
        a = self.longlong
        if a < 0:
            raise oefmt(space.w_ValueError,
                        "cannot convert negative integer to unsigned int")
        b = r_uint(a)
        if r_longlong(b) == a:
            return b
        raise oefmt(space.w_OverflowError,
                    "long int too large to convert to unsigned int")

    def bigint_w(self, space):
        return self.asbigint()

    def float_w(self, space):
        return float(self.longlong)

    def int(self, space):
        a = self.longlong
        b = intmask(a)
        return space.newint(b) if b == a else self

    def descr_long(self, space):
        if space.is_w(space.type(self), space.w_long):
            return self
        return W_SmallLongObject(self.longlong)
    descr_index = descr_trunc = descr_pos = descr_long

    def descr_float(self, space):
        return space.newfloat(float(self.longlong))

    def descr_neg(self, space):
        a = self.longlong
        try:
            if a == r_longlong(-1 << (LONGLONG_BIT-1)):
                raise OverflowError
            x = -a
        except OverflowError:
            self = _small2long(space, self)
            return self.descr_neg(space)
        return W_SmallLongObject(x)

    def descr_abs(self, space):
        return self if self.longlong >= 0 else self.descr_neg(space)

    def descr_nonzero(self, space):
        return space.newbool(bool(self.longlong))

    def descr_invert(self, space):
        x = ~self.longlong
        return W_SmallLongObject(x)

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_pow(self, space, w_exponent, w_modulus=None):
        if isinstance(w_exponent, W_AbstractLongObject):
            self = _small2long(space, self)
            return self.descr_pow(space, w_exponent, w_modulus)
        elif not isinstance(w_exponent, W_AbstractIntObject):
            return space.w_NotImplemented

        if space.is_none(w_modulus):
            try:
                return _pow_impl(space, self.longlong, w_exponent,
                                 r_longlong(0))
            except ValueError:
                self = self.descr_float(space)
                return space.pow(self, w_exponent, space.w_None)
            except OverflowError:
                self = _small2long(space, self)
                return self.descr_pow(space, w_exponent, w_modulus)
        elif isinstance(w_modulus, W_AbstractIntObject):
            w_modulus = _int2small(space, w_modulus)
        elif not isinstance(w_modulus, W_AbstractLongObject):
            return space.w_NotImplemented
        elif not isinstance(w_modulus, W_SmallLongObject):
            self = _small2long(space, self)
            return self.descr_pow(space, w_exponent, w_modulus)

        z = w_modulus.longlong
        if z == 0:
            raise oefmt(space.w_ValueError, "pow() 3rd argument cannot be 0")
        try:
            return _pow_impl(space, self.longlong, w_exponent, z)
        except ValueError:
            self = self.descr_float(space)
            return space.pow(self, w_exponent, w_modulus)
        except OverflowError:
            self = _small2long(space, self)
            return self.descr_pow(space, w_exponent, w_modulus)

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_rpow(self, space, w_base, w_modulus=None):
        if isinstance(w_base, W_AbstractIntObject):
            # Defer to w_base<W_SmallLongObject>.descr_pow
            w_base = _int2small(space, w_base)
        elif not isinstance(w_base, W_AbstractLongObject):
            return space.w_NotImplemented
        return w_base.descr_pow(space, self, w_modulus)

    def _make_descr_cmp(opname):
        op = getattr(operator, opname)
        bigint_op = getattr(rbigint, opname)
        @func_renamer('descr_' + opname)
        def descr_cmp(self, space, w_other):
            if isinstance(w_other, W_AbstractIntObject):
                result = op(self.longlong, w_other.int_w(space))
            elif not isinstance(w_other, W_AbstractLongObject):
                return space.w_NotImplemented
            elif isinstance(w_other, W_SmallLongObject):
                result = op(self.longlong, w_other.longlong)
            else:
                result = bigint_op(self.asbigint(), w_other.asbigint())
            return space.newbool(result)
        return descr_cmp

    descr_lt = _make_descr_cmp('lt')
    descr_le = _make_descr_cmp('le')
    descr_eq = _make_descr_cmp('eq')
    descr_ne = _make_descr_cmp('ne')
    descr_gt = _make_descr_cmp('gt')
    descr_ge = _make_descr_cmp('ge')

    def _make_descr_binop(func, ovf=True):
        opname = func.__name__[1:]
        descr_name, descr_rname = 'descr_' + opname, 'descr_r' + opname
        long_op = getattr(W_LongObject, descr_name)

        @func_renamer(descr_name)
        def descr_binop(self, space, w_other):
            if isinstance(w_other, W_AbstractIntObject):
                w_other = _int2small(space, w_other)
            elif not isinstance(w_other, W_AbstractLongObject):
                return space.w_NotImplemented
            elif not isinstance(w_other, W_SmallLongObject):
                self = _small2long(space, self)
                return long_op(self, space, w_other)

            if ovf:
                try:
                    return func(self, space, w_other)
                except OverflowError:
                    self = _small2long(space, self)
                    w_other = _small2long(space, w_other)
                    return long_op(self, space, w_other)
            else:
                return func(self, space, w_other)

        if opname in COMMUTATIVE_OPS:
            descr_rbinop = func_with_new_name(descr_binop, descr_rname)
        else:
            long_rop = getattr(W_LongObject, descr_rname)
            @func_renamer(descr_rname)
            def descr_rbinop(self, space, w_other):
                if isinstance(w_other, W_AbstractIntObject):
                    w_other = _int2small(space, w_other)
                elif not isinstance(w_other, W_AbstractLongObject):
                    return space.w_NotImplemented
                elif not isinstance(w_other, W_SmallLongObject):
                    self = _small2long(space, self)
                    return long_rop(self, space, w_other)

                if ovf:
                    try:
                        return func(w_other, space, self)
                    except OverflowError:
                        self = _small2long(space, self)
                        w_other = _small2long(space, w_other)
                        return long_rop(self, space, w_other)
                else:
                    return func(w_other, space, self)

        return descr_binop, descr_rbinop

    def _add(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        z = x + y
        if ((z ^ x) & (z ^ y)) < 0:
            raise OverflowError
        return W_SmallLongObject(z)
    descr_add, descr_radd = _make_descr_binop(_add)

    def _sub(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        z = x - y
        if ((z ^ x) & (z ^ ~y)) < 0:
            raise OverflowError
        return W_SmallLongObject(z)
    descr_sub, descr_rsub = _make_descr_binop(_sub)

    def _mul(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        z = _llong_mul_ovf(x, y)
        return W_SmallLongObject(z)
    descr_mul, descr_rmul = _make_descr_binop(_mul)

    def _floordiv(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        try:
            if y == -1 and x == r_longlong(-1 << (LONGLONG_BIT-1)):
                raise OverflowError
            z = x // y
        except ZeroDivisionError:
            raise oefmt(space.w_ZeroDivisionError, "integer division by zero")
        return W_SmallLongObject(z)
    descr_floordiv, descr_rfloordiv = _make_descr_binop(_floordiv)

    _div = func_with_new_name(_floordiv, '_div')
    descr_div, descr_rdiv = _make_descr_binop(_div)

    def _mod(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        try:
            if y == -1 and x == r_longlong(-1 << (LONGLONG_BIT-1)):
                raise OverflowError
            z = x % y
        except ZeroDivisionError:
            raise oefmt(space.w_ZeroDivisionError, "integer modulo by zero")
        return W_SmallLongObject(z)
    descr_mod, descr_rmod = _make_descr_binop(_mod)

    def _divmod(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        try:
            if y == -1 and x == r_longlong(-1 << (LONGLONG_BIT-1)):
                raise OverflowError
            z = x // y
        except ZeroDivisionError:
            raise oefmt(space.w_ZeroDivisionError, "integer divmod by zero")
        # no overflow possible
        m = x % y
        return space.newtuple([W_SmallLongObject(z), W_SmallLongObject(m)])
    descr_divmod, descr_rdivmod = _make_descr_binop(_divmod)

    def _lshift(self, space, w_other):
        a = self.longlong
        # May overflow
        b = space.int_w(w_other)
        if r_uint(b) < LONGLONG_BIT: # 0 <= b < LONGLONG_BIT
            c = a << b
            if a != (c >> b):
                raise OverflowError
            return W_SmallLongObject(c)
        if b < 0:
            raise oefmt(space.w_ValueError, "negative shift count")
        # b >= LONGLONG_BIT
        if a == 0:
            return self
        raise OverflowError
    descr_lshift, descr_rlshift = _make_descr_binop(_lshift)

    def _rshift(self, space, w_other):
        a = self.longlong
        # May overflow
        b = space.int_w(w_other)
        if r_uint(b) >= LONGLONG_BIT: # not (0 <= b < LONGLONG_BIT)
            if b < 0:
                raise oefmt(space.w_ValueError, "negative shift count")
            # b >= LONGLONG_BIT
            if a == 0:
                return self
            a = -1 if a < 0 else 0
        else:
            a = a >> b
        return W_SmallLongObject(a)
    descr_rshift, descr_rrshift = _make_descr_binop(_rshift, ovf=False)

    def _and(self, space, w_other):
        a = self.longlong
        b = w_other.longlong
        res = a & b
        return W_SmallLongObject(res)
    descr_and, descr_rand = _make_descr_binop(_and, ovf=False)

    def _or(self, space, w_other):
        a = self.longlong
        b = w_other.longlong
        res = a | b
        return W_SmallLongObject(res)
    descr_or, descr_ror = _make_descr_binop(_or, ovf=False)

    def _xor(self, space, w_other):
        a = self.longlong
        b = w_other.longlong
        res = a ^ b
        return W_SmallLongObject(res)
    descr_xor, descr_rxor = _make_descr_binop(_xor, ovf=False)


def _llong_mul_ovf(a, b):
    # xxx duplication of the logic from translator/c/src/int.h
    longprod = a * b
    doubleprod = float(a) * float(b)
    doubled_longprod = float(longprod)

    # Fast path for normal case:  small multiplicands, and no info
    # is lost in either method.
    if doubled_longprod == doubleprod:
        return longprod

    # Somebody somewhere lost info.  Close enough, or way off?  Note
    # that a != 0 and b != 0 (else doubled_longprod == doubleprod == 0).
    # The difference either is or isn't significant compared to the
    # true value (of which doubleprod is a good approximation).
    diff = doubled_longprod - doubleprod
    absdiff = abs(diff)
    absprod = abs(doubleprod)
    # absdiff/absprod <= 1/32 iff
    # 32 * absdiff <= absprod -- 5 good bits is "close enough"
    if 32.0 * absdiff <= absprod:
        return longprod
    raise OverflowError("integer multiplication")


def delegate_SmallLong2Float(space, w_small):
    return space.newfloat(float(w_small.longlong))


def delegate_SmallLong2Complex(space, w_small):
    return space.newcomplex(float(w_small.longlong), 0.0)


def _int2small(space, w_int):
    # XXX: W_IntObject.descr_long should probably return W_SmallLongs
    return W_SmallLongObject(r_longlong(w_int.int_w(space)))


def _small2long(space, w_small):
    return W_LongObject(w_small.asbigint())


def _pow_impl(space, iv, w_int2, iz):
    iw = space.int_w(w_int2)
    if iw < 0:
        if iz != 0:
            raise oefmt(space.w_TypeError,
                        "pow() 2nd argument cannot be negative when 3rd "
                        "argument specified")
        raise ValueError
    temp = iv
    ix = r_longlong(1)
    while iw > 0:
        if iw & 1:
            ix = _llong_mul_ovf(ix, temp)
        iw >>= 1   # Shift exponent down by 1 bit
        if iw == 0:
            break
        temp = _llong_mul_ovf(temp, temp) # Square the value of temp
        if iz:
            # If we did a multiplication, perform a modulo
            ix %= iz
            temp %= iz
    if iz:
        ix %= iz
    return W_SmallLongObject(ix)


def add_ovr(space, w_int1, w_int2):
    x = r_longlong(space.int_w(w_int1))
    y = r_longlong(space.int_w(w_int2))
    return W_SmallLongObject(x + y)

def sub_ovr(space, w_int1, w_int2):
    x = r_longlong(space.int_w(w_int1))
    y = r_longlong(space.int_w(w_int2))
    return W_SmallLongObject(x - y)

def mul_ovr(space, w_int1, w_int2):
    x = r_longlong(space.int_w(w_int1))
    y = r_longlong(space.int_w(w_int2))
    return W_SmallLongObject(x * y)

def floordiv_ovr(space, w_int1, w_int2):
    x = r_longlong(space.int_w(w_int1))
    y = r_longlong(space.int_w(w_int2))
    return W_SmallLongObject(x // y)
div_ovr = floordiv_ovr

def mod_ovr(space, w_int1, w_int2):
    x = r_longlong(space.int_w(w_int1))
    y = r_longlong(space.int_w(w_int2))
    return W_SmallLongObject(x % y)

def divmod_ovr(space, w_int1, w_int2):
    return space.newtuple([div_ovr(space, w_int1, w_int2),
                           mod_ovr(space, w_int1, w_int2)])

def pow_ovr(space, w_int1, w_int2):
    try:
        return _pow_impl(space, r_longlong(space.int_w(w_int1)), w_int2,
                         r_longlong(0))
    except (OverflowError, ValueError):
        w_a = _small2long(space, w_int1)
        w_b = _small2long(space, w_int2)
        return w_a.descr_pow(space, w_b, space.w_None)

def neg_ovr(space, w_int):
    a = r_longlong(space.int_w(w_int))
    return W_SmallLongObject(-a)

def abs_ovr(space, w_int):
    a = r_longlong(space.int_w(w_int))
    if a < 0:
        a = -a
    return W_SmallLongObject(a)

def lshift_ovr(space, w_int1, w_int2):
    w_a = _int2small(space, w_int1)
    return w_a.descr_lshift(space, w_int2)
