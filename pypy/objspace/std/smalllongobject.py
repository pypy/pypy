"""
Implementation of 'small' longs, stored as a r_longlong.
Useful for 32-bit applications manipulating values a bit larger than
fits in an 'int'.
"""
import operator

from rpython.rlib.rarithmetic import LONGLONG_BIT, intmask, r_longlong, r_uint
from rpython.rlib.rbigint import rbigint
from rpython.tool.sourcetools import func_with_new_name

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import WrappedDefault, unwrap_spec
from pypy.objspace.std.multimethod import FailedToImplementArgs
from pypy.objspace.std.longobject import W_AbstractLongObject, W_LongObject
from pypy.objspace.std.intobject import _delegate_Int2Long

LONGLONG_MIN = r_longlong((-1) << (LONGLONG_BIT-1))


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
        else:
            raise OperationError(space.w_OverflowError, space.wrap(
                "long int too large to convert to int"))

    def uint_w(self, space):
        a = self.longlong
        if a < 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot convert negative integer to unsigned int"))
        b = r_uint(a)
        if r_longlong(b) == a:
            return b
        else:
            raise OperationError(space.w_OverflowError, space.wrap(
                "long int too large to convert to unsigned int"))

    def bigint_w(self, space):
        return self.asbigint()

    def float_w(self, space):
        return float(self.longlong)

    def int(self, space):
        a = self.longlong
        b = intmask(a)
        if b == a:
            return space.newint(b)
        else:
            return self

    def descr_long(self, space):
        # XXX: do subclasses never apply here?
        return self
    descr_index = func_with_new_name(descr_long, 'descr_index')
    descr_trunc = func_with_new_name(descr_long, 'descr_trunc')
    descr_pos = func_with_new_name(descr_long, 'descr_pos')

    def descr_index(self, space):
        return self

    def descr_float(self, space):
        return space.newfloat(float(self.longlong))

    def _make_descr_cmp(opname):
        op = getattr(operator, opname)
        def descr_impl(self, space, w_other):
            if space.isinstance_w(w_other, space.w_int):
                result = op(self.longlong, w_other.int_w(space))
            elif not space.isinstance_w(w_other, space.w_long):
                return space.w_NotImplemented
            elif isinstance(w_other, W_SmallLongObject):
                result = op(self.longlong, w_other.longlong)
            else:
                result = getattr(self.asbigint(), opname)(w_other.num)
            return space.newbool(result)
        return func_with_new_name(descr_impl, "descr_" + opname)

    descr_lt = _make_descr_cmp('lt')
    descr_le = _make_descr_cmp('le')
    descr_eq = _make_descr_cmp('eq')
    descr_ne = _make_descr_cmp('ne')
    descr_gt = _make_descr_cmp('gt')
    descr_ge = _make_descr_cmp('ge')

    def _make_descr_binop(func):
        # XXX: so if w_other is Long, what do we do? sigh
        # how to handle delegation with descr_add on longobject?
        opname = func.__name__[1:]
        methname = opname + '_' if opname in ('and', 'or') else opname

        def descr_impl(self, space, w_other):
            if space.isinstance_w(w_other, space.w_int):
                w_other = delegate_Int2SmallLong(space, w_other)
            elif not space.isinstance_w(w_other, space.w_long):
                return space.w_NotImplemented
            elif not isinstance(w_other, W_SmallLongObject):
                self = delegate_SmallLong2Long(space, self)
                return getattr(space, methname)(self, w_other)

            try:
                return func(self, space, w_other)
            except OverflowError:
                self = delegate_SmallLong2Long(space, self)
                w_other = delegate_SmallLong2Long(space, w_other)
                return getattr(space, methname)(self, w_other)

        def descr_rimpl(self, space, w_other):
            if space.isinstance_w(w_other, space.w_int):
                w_other = delegate_Int2SmallLong(space, w_other)
            elif not space.isinstance_w(w_other, space.w_long):
                return space.w_NotImplemented
            elif not isinstance(w_other, W_SmallLongObject):
                self = delegate_SmallLong2Long(space, self)
                return getattr(space, methname)(w_other, self)

            try:
                return func(w_other, space, self)
            except OverflowError:
                self = delegate_SmallLong2Long(space, self)
                w_other = delegate_SmallLong2Long(space, w_other)
                return getattr(space, methname)(w_other, self)

        return descr_impl, descr_rimpl

    def _add(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        z = x + y
        if ((z^x)&(z^y)) < 0:
            raise OverflowError
        return W_SmallLongObject(z)
    descr_add, descr_radd = _make_descr_binop(_add)

    def _sub(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        z = x - y
        if ((z^x)&(z^~y)) < 0:
            raise OverflowError
        return W_SmallLongObject(z)
    descr_sub, descr_rsub = _make_descr_binop(_sub)

    def _mul(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        z = llong_mul_ovf(x, y)
        return W_SmallLongObject(z)
    descr_mul, descr_rmul = _make_descr_binop(_mul)

    def _floordiv(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        try:
            if y == -1 and x == LONGLONG_MIN:
                raise OverflowError
            z = x // y
        except ZeroDivisionError:
            raise OperationError(space.w_ZeroDivisionError,
                                 space.wrap("integer division by zero"))
        #except OverflowError:
        #    raise FailedToImplementArgs(space.w_OverflowError,
        #                            space.wrap("integer division"))
        return W_SmallLongObject(z)
    descr_floordiv, descr_rfloordiv = _make_descr_binop(_floordiv)

    _div = func_with_new_name(_floordiv, '_div')
    descr_div, descr_rdiv = _make_descr_binop(_div)

    def _mod(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        try:
            if y == -1 and x == LONGLONG_MIN:
                raise OverflowError
            z = x % y
        except ZeroDivisionError:
            raise OperationError(space.w_ZeroDivisionError,
                                 space.wrap("integer modulo by zero"))
        #except OverflowError:
        #    raise FailedToImplementArgs(space.w_OverflowError,
        #                            space.wrap("integer modulo"))
        return W_SmallLongObject(z)
    descr_mod, descr_rmod = _make_descr_binop(_mod)

    def _divmod(self, space, w_other):
        x = self.longlong
        y = w_other.longlong
        try:
            if y == -1 and x == LONGLONG_MIN:
                raise OverflowError
            z = x // y
        except ZeroDivisionError:
            raise OperationError(space.w_ZeroDivisionError,
                                 space.wrap("integer divmod by zero"))
        #except OverflowError:
        #    raise FailedToImplementArgs(space.w_OverflowError,
        #                            space.wrap("integer modulo"))
        # no overflow possible
        m = x % y
        return space.newtuple([W_SmallLongObject(z), W_SmallLongObject(m)])
    descr_divmod, descr_rdivmod = _make_descr_binop(_divmod)

    # XXX:
    @unwrap_spec(w_modulus=WrappedDefault(None))
    #def descr_pow__SmallLong_Int_SmallLong(self, space, w_exponent,
    def descr_pow(self, space, w_exponent, w_modulus=None):
        if space.isinstance_w(w_exponent, space.w_long):
            self = delegate_SmallLong2Long(space, self)
            return space.pow(self, w_exponent, w_modulus)
        elif not space.isinstance_w(w_exponent, space.w_int):
            return space.w_NotImplemented
        
        # XXX: this expects w_exponent as an int o_O
        """
        if space.isinstance_w(w_exponent, space.w_int):
            w_exponent = delegate_Int2SmallLong(space, w_exponent)
        elif not space.isinstance_w(w_exponent, space.w_long):
            return space.w_NotImplemented
        elif not isinstance(w_exponent, W_SmallLongObject):
            self = delegate_SmallLong2Long(space, self)
            return space.pow(self, w_exponent, w_modulus)
            """

        if space.is_none(w_modulus):
            #return _impl_pow(space, self.longlong, w_exponent)
            try:
                return _impl_pow(space, self.longlong, w_exponent)
            except ValueError:
                self = delegate_SmallLong2Float(space, self)
            except OverflowError:
                self = delegate_SmallLong2Long(space, self)
            return space.pow(self, w_exponent, w_modulus)
        elif space.isinstance_w(w_modulus, space.w_int):
            w_modulus = delegate_Int2SmallLong(space, w_modulus)
        elif not space.isinstance_w(w_modulus, space.w_long):
            return space.w_NotImplemented
        elif not isinstance(w_modulus, W_SmallLongObject):
            self = delegate_SmallLong2Long(space, self)
            #return space.pow(self, w_modulus, w_modulus)
            return space.pow(self, w_exponent, w_modulus)

        z = w_modulus.longlong
        if z == 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("pow() 3rd argument cannot be 0"))
        try:
            return _impl_pow(space, self.longlong, w_exponent, z)
        except ValueError:
            self = delegate_SmallLong2Float(space, self)
        except OverflowError:
            self = delegate_SmallLong2Long(space, self)
        return space.pow(self, w_exponent, w_modulus)

    # XXX:
    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_rpow(self, space, w_exponent, w_modulus=None):
        # XXX: blargh
        if space.isinstance_w(w_exponent, space.w_int):
            w_exponent = _delegate_Int2Long(space, w_exponent)
        elif not space.isinstance_w(w_exponent, space.w_long):
            return space.w_NotImplemented
        return space.pow(w_exponent, self, w_modulus)

    #def descr_lshift__SmallLong_Int(space, w_small1, w_int2):
    def descr_lshift(self, space, w_other):
        if space.isinstance_w(w_other, space.w_long):
            self = delegate_SmallLong2Long(space, self)
            w_other = delegate_SmallLong2Long(space, w_other)
            return space.lshift(self, w_other)
        elif not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        a = self.longlong
        b = w_other.intval
        if r_uint(b) < LONGLONG_BIT: # 0 <= b < LONGLONG_BIT
            try:
                c = a << b
                if a != (c >> b):
                    raise OverflowError
            except OverflowError:
                #raise FailedToImplementArgs(space.w_OverflowError,
                #                        space.wrap("integer left shift"))
                self = delegate_SmallLong2Long(space, self)
                w_other = _delegate_Int2Long(space, w_other)
                return space.lshift(self, w_other)
            return W_SmallLongObject(c)
        if b < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("negative shift count"))
        else: #b >= LONGLONG_BIT
            if a == 0:
                return self
            #raise FailedToImplementArgs(space.w_OverflowError,
            #                        space.wrap("integer left shift"))
            self = delegate_SmallLong2Long(space, self)
            w_other = _delegate_Int2Long(space, w_other)
            return space.lshift(self, w_other)

    def descr_rshift(self, space, w_other):
        if space.isinstance_w(w_other, space.w_long):
            self = delegate_SmallLong2Long(space, self)
            w_other = delegate_SmallLong2Long(space, w_other)
            return space.rshift(self, w_other)
        elif not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        a = self.longlong
        b = w_other.intval
        if r_uint(b) >= LONGLONG_BIT: # not (0 <= b < LONGLONG_BIT)
            if b < 0:
                raise OperationError(space.w_ValueError,
                                     space.wrap("negative shift count"))
            else: # b >= LONGLONG_BIT
                if a == 0:
                    return self
                if a < 0:
                    a = -1
                else:
                    a = 0
        else:
            a = a >> b
        return W_SmallLongObject(a)

    def _and(self, space, w_other):
        a = self.longlong
        b = w_other.longlong
        res = a & b
        return W_SmallLongObject(res)
    descr_and, descr_rand = _make_descr_binop(_and)

    def _xor(self, space, w_other):
        a = self.longlong
        b = w_other.longlong
        res = a ^ b
        return W_SmallLongObject(res)
    descr_xor, descr_rxor = _make_descr_binop(_xor)

    def _or(self, space, w_other):
        a = self.longlong
        b = w_other.longlong
        res = a | b
        return W_SmallLongObject(res)
    descr_or, descr_ror = _make_descr_binop(_or)

    def descr_neg(self, space):
        a = self.longlong
        try:
            if a == LONGLONG_MIN:
                raise OverflowError
            x = -a
        except OverflowError:
            return space.neg(delegate_SmallLong2Long(self))
            #raise FailedToImplementArgs(space.w_OverflowError,
            #                        space.wrap("integer negation"))
        return W_SmallLongObject(x)
    #get_negint = neg__SmallLong

    #def descr_pos(self, space):
    #    return self

    def descr_abs(self, space):
        if self.longlong >= 0:
            return self
        else:
            #return get_negint(space, self)
            return self.descr_neg(space)

    def descr_nonzero(self, space):
        return space.newbool(bool(self.longlong))

    def descr_invert(self, space):
        x = self.longlong
        a = ~x
        return W_SmallLongObject(a)


# ____________________________________________________________

def llong_mul_ovf(a, b):
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

# ____________________________________________________________

def delegate_Bool2SmallLong(space, w_bool):
    return W_SmallLongObject(r_longlong(space.is_true(w_bool)))

def delegate_Int2SmallLong(space, w_int):
    #return W_SmallLongObject(r_longlong(w_int.intval))
    return W_SmallLongObject(r_longlong(w_int.int_w(space)))

def delegate_SmallLong2Long(space, w_small):
    return W_LongObject(w_small.asbigint())

def delegate_SmallLong2Float(space, w_small):
    return space.newfloat(float(w_small.longlong))

def delegate_SmallLong2Complex(space, w_small):
    return space.newcomplex(float(w_small.longlong), 0.0)

def add_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x + y)

def sub_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x - y)

def mul_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x * y)

def floordiv_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x // y)
div_ovr = floordiv_ovr

def mod_ovr(space, w_int1, w_int2):
    x = r_longlong(w_int1.intval)
    y = r_longlong(w_int2.intval)
    return W_SmallLongObject(x % y)

def divmod_ovr(space, w_int1, w_int2):
    return space.newtuple([div_ovr(space, w_int1, w_int2),
                           mod_ovr(space, w_int1, w_int2)])

def _impl_pow(space, iv, w_int2, iz=r_longlong(0)):
    iw = w_int2.intval
    if iw < 0:
        if iz != 0:
            raise OperationError(space.w_TypeError,
                             space.wrap("pow() 2nd argument "
                 "cannot be negative when 3rd argument specified"))
        raise ValueError
    temp = iv
    ix = r_longlong(1)
    try:
        while iw > 0:
            if iw & 1:
                ix = llong_mul_ovf(ix, temp)
            iw >>= 1   #/* Shift exponent down by 1 bit */
            if iw==0:
                break
            temp = llong_mul_ovf(temp, temp) #/* Square the value of temp */
            if iz:
                #/* If we did a multiplication, perform a modulo */
                ix = ix % iz
                temp = temp % iz
        if iz:
            ix = ix % iz
    except OverflowError:
        # XXX:
        raise OverflowError
    return W_SmallLongObject(ix)

def pow_ovr(space, w_int1, w_int2):
    try:
        return _impl_pow(space, r_longlong(w_int1.intval), w_int2)
    except FailedToImplementArgs:
        from pypy.objspace.std import longobject
        w_a = W_LongObject.fromint(space, w_int1.intval)
        w_b = W_LongObject.fromint(space, w_int2.intval)
        return longobject.pow__Long_Long_None(space, w_a, w_b, space.w_None)

def neg_ovr(space, w_int):
    a = r_longlong(w_int.intval)
    return W_SmallLongObject(-a)

def abs_ovr(space, w_int):
    a = r_longlong(w_int.intval)
    if a < 0: a = -a
    return W_SmallLongObject(a)

def lshift_ovr(space, w_int1, w_int2):
    a = r_longlong(w_int1.intval)
    try:
        return lshift__SmallLong_Int(space, W_SmallLongObject(a), w_int2)
    except FailedToImplementArgs:
        from pypy.objspace.std import longobject
        w_a = W_LongObject.fromint(space, w_int1.intval)
        w_b = W_LongObject.fromint(space, w_int2.intval)
        return longobject.lshift__Long_Long(space, w_a, w_b)
