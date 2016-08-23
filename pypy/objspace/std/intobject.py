"""The builtin int type (W_AbstractInt) and the base impl (W_IntObject)
based on rpython ints.

In order to have the same behavior running on CPython, and after RPython
translation this module uses rarithmetic.ovfcheck to explicitly check
for overflows, something CPython does not do anymore.
"""
import operator
import sys

from rpython.rlib import jit
from rpython.rlib.objectmodel import instantiate
from rpython.rlib.rarithmetic import (
    LONG_BIT, intmask, is_valid_int, ovfcheck, r_longlong, r_uint,
    string_to_int)
from rpython.rlib.rbigint import (
    InvalidEndiannessError, InvalidSignednessError, rbigint)
from rpython.rlib.rfloat import DBL_MANT_DIG
from rpython.rlib.rstring import (
    ParseStringError, ParseStringOverflowError)
from rpython.tool.sourcetools import func_renamer, func_with_new_name

from pypy.interpreter import typedef
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (
    WrappedDefault, applevel, interp2app, interpindirect2app, unwrap_spec)
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std import newformat
from pypy.objspace.std.util import (
    BINARY_OPS, CMP_OPS, COMMUTATIVE_OPS, IDTAG_INT, IDTAG_SHIFT, wrap_parsestringerror)

SENTINEL = object()

HASH_BITS = 61 if sys.maxsize > 2 ** 31 - 1 else 31
HASH_MODULUS = 2 ** HASH_BITS - 1


class W_AbstractIntObject(W_Root):
    __slots__ = ()

    def is_w(self, space, w_other):
        from pypy.objspace.std.boolobject import W_BoolObject
        if (not isinstance(w_other, W_AbstractIntObject) or
            isinstance(w_other, W_BoolObject)):
            return False
        if self.user_overridden_class or w_other.user_overridden_class:
            return self is w_other
        x = space.bigint_w(self, allow_conversion=False)
        y = space.bigint_w(w_other, allow_conversion=False)
        return x.eq(y)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        b = space.bigint_w(self)
        b = b.lshift(IDTAG_SHIFT).int_or_(IDTAG_INT)
        return space.newlong_from_rbigint(b)

    @staticmethod
    @unwrap_spec(byteorder=str, signed=bool)
    def descr_from_bytes(space, w_inttype, w_obj, byteorder, signed=False):
        """int.from_bytes(bytes, byteorder, *, signed=False) -> int

        Return the integer represented by the given array of bytes.

        The bytes argument must either support the buffer protocol or be
        an iterable object producing bytes.  Bytes and bytearray are
        examples of built-in objects that support the buffer protocol.

        The byteorder argument determines the byte order used to
        represent the integer.  If byteorder is 'big', the most
        significant byte is at the beginning of the byte array.  If
        byteorder is 'little', the most significant byte is at the end
        of the byte array.  To request the native byte order of the host
        system, use `sys.byteorder' as the byte order value.

        The signed keyword-only argument indicates whether two's
        complement is used to represent the integer.
        """
        from pypy.objspace.std.bytesobject import makebytesdata_w
        bytes = ''.join(makebytesdata_w(space, w_obj))
        try:
            bigint = rbigint.frombytes(bytes, byteorder=byteorder,
                                       signed=signed)
        except InvalidEndiannessError:
            raise oefmt(space.w_ValueError,
                        "byteorder must be either 'little' or 'big'")
        try:
            as_int = bigint.toint()
        except OverflowError:
            from pypy.objspace.std.longobject import newbigint
            return newbigint(space, w_inttype, bigint)
        else:
            if space.is_w(w_inttype, space.w_int):
                # common case
                return wrapint(space, as_int)
            w_obj = space.allocate_instance(W_IntObject, w_inttype)
            W_IntObject.__init__(w_obj, as_int)
            return w_obj

    @unwrap_spec(nbytes=int, byteorder=str, signed=bool)
    def descr_to_bytes(self, space, nbytes, byteorder, signed=False):
        """to_bytes(...)
        int.to_bytes(length, byteorder, *, signed=False) -> bytes

        Return an array of bytes representing an integer.

        The integer is represented using length bytes.  An OverflowError
        is raised if the integer is not representable with the given
        number of bytes.

        The byteorder argument determines the byte order used to
        represent the integer.  If byteorder is 'big', the most
        significant byte is at the beginning of the byte array.  If
        byteorder is 'little', the most significant byte is at the end
        of the byte array.  To request the native byte order of the host
        system, use `sys.byteorder' as the byte order value.

        The signed keyword-only argument determines whether two's
        complement is used to represent the integer.  If signed is False
        and a negative integer is given, an OverflowError is raised.
        """
        bigint = space.bigint_w(self)
        try:
            byte_string = bigint.tobytes(nbytes, byteorder=byteorder,
                                         signed=signed)
        except InvalidEndiannessError:
            raise oefmt(space.w_ValueError,
                        "byteorder must be either 'little' or 'big'")
        except InvalidSignednessError:
            raise oefmt(space.w_OverflowError,
                        "can't convert negative int to unsigned")
        except OverflowError:
            raise oefmt(space.w_OverflowError, "int too big to convert")
        return space.newbytes(byte_string)

    def descr_round(self, space, w_ndigits=None):
        """Rounding an Integral returns itself.
        Rounding with an ndigits argument also returns an integer.
        """
        # To round an integer m to the nearest 10**n (n positive), we
        # make use of the divmod_near operation, defined by:
        #
        # divmod_near(a, b) = (q, r)
        #
        # where q is the nearest integer to the quotient a / b (the
        # nearest even integer in the case of a tie) and r == a - q * b.
        # Hence q * b = a - r is the nearest multiple of b to a,
        # preferring even multiples in the case of a tie.
        #
        # So the nearest multiple of 10**n to m is:
        #
        # m - divmod_near(m, 10**n)[1]

        # XXX: since divmod_near is pure python we can probably remove
        # the longs used here. or this could at least likely be more
        # efficient for W_IntObject
        from pypy.objspace.std.longobject import newlong

        if w_ndigits is None:
            return self.int(space)

        ndigits = space.bigint_w(space.index(w_ndigits))
        # if ndigits >= 0 then no rounding is necessary; return self
        # unchanged
        if ndigits.ge(rbigint.fromint(0)):
            return self.int(space)

        # result = self - divmod_near(self, 10 ** -ndigits)[1]
        right = rbigint.fromint(10).pow(ndigits.neg())
        w_tuple = divmod_near(space, self, newlong(space, right))
        _, w_r = space.fixedview(w_tuple, 2)
        return space.sub(self, w_r)

    def _self_unaryop(opname, doc=None):
        @func_renamer('descr_' + opname)
        def descr_unaryop(self, space):
            return self.int(space)
        descr_unaryop.__doc__ = doc
        return descr_unaryop

    descr_conjugate = _self_unaryop(
        'conjugate', "Returns self, the complex conjugate of any int.")
    descr_pos = _self_unaryop('pos', "x.__pos__() <==> +x")
    descr_index = _self_unaryop('index',
                                "x[y:z] <==> x[y.__index__():z.__index__()]")
    descr_trunc = _self_unaryop('trunc',
                                "Truncating an Integral returns itself.")
    descr_floor = _self_unaryop('floor', "Flooring an Integral returns itself.")
    descr_ceil = _self_unaryop('ceil', "Ceiling of an Integral returns itself.")

    descr_get_numerator = _self_unaryop('get_numerator')
    descr_get_real = _self_unaryop('get_real')

    def descr_get_denominator(self, space):
        return wrapint(space, 1)

    def descr_get_imag(self, space):
        return wrapint(space, 0)

    def int(self, space):
        """x.__int__() <==> int(x)"""
        raise NotImplementedError

    def asbigint(self):
        raise NotImplementedError

    def descr_format(self, space, w_format_spec):
        raise NotImplementedError

    def descr_pow(self, space, w_exponent, w_modulus=None):
        """x.__pow__(y[, z]) <==> pow(x, y[, z])"""
        raise NotImplementedError
    descr_rpow = func_with_new_name(descr_pow, 'descr_rpow')
    descr_rpow.__doc__ = "y.__rpow__(x[, z]) <==> pow(x, y[, z])"

    def _abstract_unaryop(opname, doc=SENTINEL):
        if doc is SENTINEL:
            doc = 'x.__%s__() <==> %s(x)' % (opname, opname)
        @func_renamer('descr_' + opname)
        def descr_unaryop(self, space):
            raise NotImplementedError
        descr_unaryop.__doc__ = doc
        return descr_unaryop

    descr_repr = _abstract_unaryop('repr')
    descr_str = _abstract_unaryop('str')

    descr_bit_length = _abstract_unaryop('bit_length', """\
        int.bit_length() -> int

        Number of bits necessary to represent self in binary.
        >>> bin(37)
        '0b100101'
        >>> (37).bit_length()
        6""")
    descr_hash = _abstract_unaryop('hash')
    descr_getnewargs = _abstract_unaryop('getnewargs', None)
    descr_float = _abstract_unaryop('float')
    descr_neg = _abstract_unaryop('neg', "x.__neg__() <==> -x")
    descr_abs = _abstract_unaryop('abs')
    descr_bool = _abstract_unaryop('bool', "x.__bool__() <==> x != 0")
    descr_invert = _abstract_unaryop('invert', "x.__invert__() <==> ~x")

    def _abstract_cmpop(opname):
        @func_renamer('descr_' + opname)
        def descr_cmp(self, space, w_other):
            raise NotImplementedError
        descr_cmp.__doc__ = 'x.__%s__(y) <==> x%sy' % (opname, CMP_OPS[opname])
        return descr_cmp

    descr_lt = _abstract_cmpop('lt')
    descr_le = _abstract_cmpop('le')
    descr_eq = _abstract_cmpop('eq')
    descr_ne = _abstract_cmpop('ne')
    descr_gt = _abstract_cmpop('gt')
    descr_ge = _abstract_cmpop('ge')

    def _abstract_binop(opname):
        oper = BINARY_OPS.get(opname)
        if oper == '%':
            oper = '%%'
        oper = '%s(%%s, %%s)' % opname if not oper else '%%s%s%%s' % oper
        @func_renamer('descr_' + opname)
        def descr_binop(self, space, w_other):
            raise NotImplementedError
        descr_binop.__doc__ = "x.__%s__(y) <==> %s" % (opname,
                                                       oper % ('x', 'y'))
        descr_rbinop = func_with_new_name(descr_binop, 'descr_r' + opname)
        descr_rbinop.__doc__ = "x.__r%s__(y) <==> %s" % (opname,
                                                         oper % ('y', 'x'))
        return descr_binop, descr_rbinop

    descr_add, descr_radd = _abstract_binop('add')
    descr_sub, descr_rsub = _abstract_binop('sub')
    descr_mul, descr_rmul = _abstract_binop('mul')

    descr_and, descr_rand = _abstract_binop('and')
    descr_or, descr_ror = _abstract_binop('or')
    descr_xor, descr_rxor = _abstract_binop('xor')

    descr_lshift, descr_rlshift = _abstract_binop('lshift')
    descr_rshift, descr_rrshift = _abstract_binop('rshift')

    descr_floordiv, descr_rfloordiv = _abstract_binop('floordiv')
    descr_truediv, descr_rtruediv = _abstract_binop('truediv')
    descr_mod, descr_rmod = _abstract_binop('mod')
    descr_divmod, descr_rdivmod = _abstract_binop('divmod')


def _floordiv(space, x, y):
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise oefmt(space.w_ZeroDivisionError,
                    "integer division or modulo by zero")
    return wrapint(space, z)


def _truediv(space, x, y):
    if not y:
        raise oefmt(space.w_ZeroDivisionError, "division by zero")

    if (DBL_MANT_DIG < LONG_BIT and
        (r_uint(abs(x)) >> DBL_MANT_DIG or r_uint(abs(y)) >> DBL_MANT_DIG)):
        # large x or y, use long arithmetic
        raise OverflowError

    # both ints can be exactly represented as doubles, do a
    # floating-point division
    a = float(x)
    b = float(y)
    return space.wrap(a / b)


def _mod(space, x, y):
    try:
        z = ovfcheck(x % y)
    except ZeroDivisionError:
        raise oefmt(space.w_ZeroDivisionError, "integer modulo by zero")
    return wrapint(space, z)


def _divmod(space, x, y):
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise oefmt(space.w_ZeroDivisionError, "integer divmod by zero")
    # no overflow possible
    m = x % y
    w = space.wrap
    return space.newtuple([w(z), w(m)])


def _divmod_ovf2small(space, x, y):
    from pypy.objspace.std.smalllongobject import W_SmallLongObject
    a = r_longlong(x)
    b = r_longlong(y)
    return space.newtuple([W_SmallLongObject(a // b),
                           W_SmallLongObject(a % b)])


def _lshift(space, a, b):
    if r_uint(b) < LONG_BIT: # 0 <= b < LONG_BIT
        c = ovfcheck(a << b)
        return wrapint(space, c)
    if b < 0:
        raise oefmt(space.w_ValueError, "negative shift count")
    # b >= LONG_BIT
    if a == 0:
        return wrapint(space, a)
    raise OverflowError


def _lshift_ovf2small(space, a, b):
    from pypy.objspace.std.smalllongobject import W_SmallLongObject
    w_a = W_SmallLongObject.fromint(a)
    w_b = W_SmallLongObject.fromint(b)
    return w_a.descr_lshift(space, w_b)


def _rshift(space, a, b):
    if r_uint(b) >= LONG_BIT: # not (0 <= b < LONG_BIT)
        if b < 0:
            raise oefmt(space.w_ValueError, "negative shift count")
        # b >= LONG_BIT
        if a == 0:
            return wrapint(space, a)
        a = -1 if a < 0 else 0
    else:
        a = a >> b
    return wrapint(space, a)


@jit.look_inside_iff(lambda space, iv, iw, iz:
                     jit.isconstant(iw) and jit.isconstant(iz))
def _pow(space, iv, iw, iz):
    """Helper for pow"""
    if iw < 0:
        if iz != 0:
            raise oefmt(space.w_TypeError,
                        "pow() 2nd argument cannot be negative when 3rd "
                        "argument specified")
        # bounce it, since it always returns float
        raise ValueError
    temp = iv
    ix = 1
    while iw > 0:
        if iw & 1:
            try:
                ix = ovfcheck(ix * temp)
            except OverflowError:
                raise
        iw >>= 1   # Shift exponent down by 1 bit
        if iw == 0:
            break
        try:
            temp = ovfcheck(temp * temp) # Square the value of temp
        except OverflowError:
            raise
        if iz:
            # If we did a multiplication, perform a modulo
            ix %= iz
            temp %= iz
    if iz:
        ix %= iz
    return ix


def _pow_ovf2long(space, iv, iw, w_modulus):
    if space.is_none(w_modulus) and _recover_with_smalllong(space):
        from pypy.objspace.std.smalllongobject import _pow as _pow_small
        try:
            # XXX: shouldn't have to pass r_longlong(0) here (see
            # 4fa4c6b93a84)
            return _pow_small(space, r_longlong(iv), iw, r_longlong(0))
        except (OverflowError, ValueError):
            pass
    from pypy.objspace.std.longobject import W_LongObject
    w_iv = W_LongObject.fromint(space, iv)
    w_iw = W_LongObject.fromint(space, iw)
    return w_iv.descr_pow(space, w_iw, w_modulus)


def _make_ovf2long(opname, ovf2small=None):
    op = getattr(operator, opname, None)
    assert op or ovf2small

    def ovf2long(space, x, y):
        """Handle overflowing to smalllong or long"""
        if _recover_with_smalllong(space):
            if ovf2small:
                return ovf2small(space, x, y)
            # Assume a generic operation without an explicit ovf2small
            # handler
            from pypy.objspace.std.smalllongobject import W_SmallLongObject
            a = r_longlong(x)
            b = r_longlong(y)
            return W_SmallLongObject(op(a, b))

        from pypy.objspace.std.longobject import W_LongObject
        w_x = W_LongObject.fromint(space, x)
        w_y = W_LongObject.fromint(space, y)
        return getattr(w_x, 'descr_' + opname)(space, w_y)

    return ovf2long


class W_IntObject(W_AbstractIntObject):

    __slots__ = 'intval'
    _immutable_fields_ = ['intval']

    def __init__(self, intval):
        assert is_valid_int(intval)
        self.intval = int(intval)

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%d)" % (self.__class__.__name__, self.intval)

    def is_w(self, space, w_other):
        from pypy.objspace.std.boolobject import W_BoolObject
        if (not isinstance(w_other, W_AbstractIntObject) or
            isinstance(w_other, W_BoolObject)):
            return False
        if self.user_overridden_class or w_other.user_overridden_class:
            return self is w_other
        x = self.intval
        try:
            y = space.int_w(w_other)
        except OperationError as e:
            if e.match(space, space.w_OverflowError):
                return False
            raise
        return x == y

    def int_w(self, space, allow_conversion=True):
        return self.intval

    def _int_w(self, space):
        return self.intval

    unwrap = _int_w

    def uint_w(self, space):
        intval = self.intval
        if intval < 0:
            raise oefmt(space.w_ValueError,
                        "cannot convert negative integer to unsigned")
        return r_uint(intval)

    def bigint_w(self, space, allow_conversion=True):
        return self.asbigint()

    def _bigint_w(self, space):
        return self.asbigint()

    def float_w(self, space, allow_conversion=True):
        return float(self.intval)

    # note that we do NOT implement _float_w, because __float__ cannot return
    # an int

    def int(self, space):
        if type(self) is W_IntObject:
            return self
        if not space.is_overloaded(self, space.w_int, '__int__'):
            return space.newint(self.intval)
        return W_Root.int(self, space)

    def asbigint(self):
        return rbigint.fromint(self.intval)

    @staticmethod
    @unwrap_spec(w_x=WrappedDefault(0))
    def descr_new(space, w_inttype, w_x, w_base=None):
        """T.__new__(S, ...) -> a new object with type S, a subtype of T"""
        return _new_int(space, w_inttype, w_x, w_base)

    def descr_hash(self, space):
        return space.wrap(_hash_int(self.intval))

    def as_w_long(self, space):
        # XXX: should try smalllong
        from pypy.objspace.std.longobject import W_LongObject
        return W_LongObject.fromint(space, self.intval)

    def descr_bool(self, space):
        return space.newbool(self.intval != 0)

    def descr_invert(self, space):
        return wrapint(space, ~self.intval)

    def descr_neg(self, space):
        a = self.intval
        try:
            b = ovfcheck(-a)
        except OverflowError:
            if _recover_with_smalllong(space):
                from pypy.objspace.std.smalllongobject import W_SmallLongObject
                x = r_longlong(a)
                return W_SmallLongObject(-x)
            return self.as_w_long(space).descr_neg(space)
        return wrapint(space, b)

    def descr_abs(self, space):
        pos = self.intval >= 0
        return self.int(space) if pos else self.descr_neg(space)

    def descr_float(self, space):
        a = self.intval
        x = float(a)
        return space.newfloat(x)

    def descr_getnewargs(self, space):
        return space.newtuple([wrapint(space, self.intval)])

    def descr_bit_length(self, space):
        val = self.intval
        bits = 0
        if val < 0:
            # warning, "-val" overflows here
            val = -((val + 1) >> 1)
            bits = 1
        while val:
            bits += 1
            val >>= 1
        return space.wrap(bits)

    def descr_repr(self, space):
        res = str(self.intval)
        return space.wrap(res)
    descr_str = func_with_new_name(descr_repr, 'descr_str')

    def descr_format(self, space, w_format_spec):
        return newformat.run_formatter(space, w_format_spec,
                                       "format_int_or_long", self,
                                       newformat.INT_KIND)

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_pow(self, space, w_exponent, w_modulus=None):
        if isinstance(w_exponent, W_IntObject):
            y = w_exponent.intval
        elif isinstance(w_exponent, W_AbstractIntObject):
            self = self.as_w_long(space)
            return self.descr_pow(space, w_exponent, w_modulus)
        else:
            return space.w_NotImplemented

        x = self.intval
        y = w_exponent.intval

        if space.is_none(w_modulus):
            z = 0
        elif isinstance(w_modulus, W_IntObject):
            z = w_modulus.intval
            if z == 0:
                raise oefmt(space.w_ValueError,
                            "pow() 3rd argument cannot be 0")
        else:
            # can't return NotImplemented (space.pow doesn't do full
            # ternary, i.e. w_modulus.__zpow__(self, w_exponent)), so
            # handle it ourselves
            return _pow_ovf2long(space, x, y, w_modulus)

        try:
            result = _pow(space, x, y, z)
        except (OverflowError, ValueError):
            return _pow_ovf2long(space, x, y, w_modulus)
        return space.wrap(result)

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_rpow(self, space, w_base, w_modulus=None):
        if isinstance(w_base, W_IntObject):
            return w_base.descr_pow(space, self, w_modulus)
        elif isinstance(w_base, W_AbstractIntObject):
            self = self.as_w_long(space)
            return self.descr_rpow(space, self, w_modulus)
        return space.w_NotImplemented

    def _make_descr_cmp(opname):
        op = getattr(operator, opname)
        descr_name = 'descr_' + opname
        @func_renamer(descr_name)
        def descr_cmp(self, space, w_other):
            if isinstance(w_other, W_IntObject):
                i = self.intval
                j = w_other.intval
                return space.newbool(op(i, j))
            elif isinstance(w_other, W_AbstractIntObject):
                self = self.as_w_long(space)
                return getattr(self, descr_name)(space, w_other)
            return space.w_NotImplemented
        return descr_cmp

    descr_lt = _make_descr_cmp('lt')
    descr_le = _make_descr_cmp('le')
    descr_eq = _make_descr_cmp('eq')
    descr_ne = _make_descr_cmp('ne')
    descr_gt = _make_descr_cmp('gt')
    descr_ge = _make_descr_cmp('ge')

    def _make_generic_descr_binop(opname, ovf=True):
        op = getattr(operator,
                     opname + '_' if opname in ('and', 'or') else opname)
        descr_name, descr_rname = 'descr_' + opname, 'descr_r' + opname
        if ovf:
            ovf2long = _make_ovf2long(opname)

        @func_renamer(descr_name)
        def descr_binop(self, space, w_other):
            if isinstance(w_other, W_IntObject):
                x = self.intval
                y = w_other.intval
                if ovf:
                    try:
                        z = ovfcheck(op(x, y))
                    except OverflowError:
                        return ovf2long(space, x, y)
                else:
                    z = op(x, y)
                return wrapint(space, z)
            elif isinstance(w_other, W_AbstractIntObject):
                self = self.as_w_long(space)
                return getattr(self, descr_name)(space, w_other)
            return space.w_NotImplemented

        if opname in COMMUTATIVE_OPS:
            @func_renamer(descr_rname)
            def descr_rbinop(self, space, w_other):
                return descr_binop(self, space, w_other)
            return descr_binop, descr_rbinop

        @func_renamer(descr_rname)
        def descr_rbinop(self, space, w_other):
            if isinstance(w_other, W_IntObject):
                x = self.intval
                y = w_other.intval
                if ovf:
                    try:
                        z = ovfcheck(op(y, x))
                    except OverflowError:
                        return ovf2long(space, y, x)
                else:
                    z = op(y, x)
                return wrapint(space, z)
            elif isinstance(w_other, W_AbstractIntObject):
                self = self.as_w_long(space)
                return getattr(self, descr_rname)(space, w_other)
            return space.w_NotImplemented

        return descr_binop, descr_rbinop

    descr_add, descr_radd = _make_generic_descr_binop('add')
    descr_sub, descr_rsub = _make_generic_descr_binop('sub')
    descr_mul, descr_rmul = _make_generic_descr_binop('mul')

    descr_and, descr_rand = _make_generic_descr_binop('and', ovf=False)
    descr_or, descr_ror = _make_generic_descr_binop('or', ovf=False)
    descr_xor, descr_rxor = _make_generic_descr_binop('xor', ovf=False)

    def _make_descr_binop(func, ovf=True, ovf2small=None):
        opname = func.__name__[1:]
        descr_name, descr_rname = 'descr_' + opname, 'descr_r' + opname
        if ovf:
            ovf2long = _make_ovf2long(opname, ovf2small)

        @func_renamer(descr_name)
        def descr_binop(self, space, w_other):
            if isinstance(w_other, W_IntObject):
                x = self.intval
                y = w_other.intval
                if ovf:
                    try:
                        return func(space, x, y)
                    except OverflowError:
                        return ovf2long(space, x, y)
                else:
                    return func(space, x, y)
            elif isinstance(w_other, W_AbstractIntObject):
                self = self.as_w_long(space)
                return getattr(self, descr_name)(space, w_other)
            return space.w_NotImplemented

        @func_renamer(descr_rname)
        def descr_rbinop(self, space, w_other):
            if isinstance(w_other, W_IntObject):
                x = self.intval
                y = w_other.intval
                if ovf:
                    try:
                        return func(space, y, x)
                    except OverflowError:
                        return ovf2long(space, y, x)
                else:
                    return func(space, y, x)
            elif isinstance(w_other, W_AbstractIntObject):
                self = self.as_w_long(space)
                return getattr(self, descr_rname)(space, w_other)
            return space.w_NotImplemented

        return descr_binop, descr_rbinop

    descr_lshift, descr_rlshift = _make_descr_binop(
        _lshift, ovf2small=_lshift_ovf2small)
    descr_rshift, descr_rrshift = _make_descr_binop(_rshift, ovf=False)

    descr_floordiv, descr_rfloordiv = _make_descr_binop(_floordiv)
    descr_truediv, descr_rtruediv = _make_descr_binop(_truediv)
    descr_mod, descr_rmod = _make_descr_binop(_mod)
    descr_divmod, descr_rdivmod = _make_descr_binop(
        _divmod, ovf2small=_divmod_ovf2small)


def setup_prebuilt(space):
    if space.config.objspace.std.withprebuiltint:
        W_IntObject.PREBUILT = []
        for i in range(space.config.objspace.std.prebuiltintfrom,
                       space.config.objspace.std.prebuiltintto):
            W_IntObject.PREBUILT.append(W_IntObject(i))
    else:
        W_IntObject.PREBUILT = None


def wrapint(space, x):
    if not space.config.objspace.std.withprebuiltint:
        return W_IntObject(x)
    lower = space.config.objspace.std.prebuiltintfrom
    upper = space.config.objspace.std.prebuiltintto
    # use r_uint to perform a single comparison (this whole function is
    # getting inlined into every caller so keeping the branching to a
    # minimum is a good idea)
    index = r_uint(x - lower)
    if index >= r_uint(upper - lower):
        w_res = instantiate(W_IntObject)
    else:
        w_res = W_IntObject.PREBUILT[index]
    # obscure hack to help the CPU cache: we store 'x' even into a
    # prebuilt integer's intval.  This makes sure that the intval field
    # is present in the cache in the common case where it is quickly
    # reused.  (we could use a prefetch hint if we had that)
    w_res.intval = x
    return w_res


divmod_near = applevel('''
       def divmod_near(a, b):
           """Return a pair (q, r) such that a = b * q + r, and abs(r)
           <= abs(b)/2, with equality possible only if q is even.  In
           other words, q == a / b, rounded to the nearest integer using
           round-half-to-even."""
           q, r = divmod(a, b)
           # round up if either r / b > 0.5, or r / b == 0.5 and q is
           # odd.  The expression r / b > 0.5 is equivalent to 2 * r > b
           # if b is positive, 2 * r < b if b negative.
           greater_than_half = 2*r > b if b > 0 else 2*r < b
           exactly_half = 2*r == b
           if greater_than_half or exactly_half and q % 2 == 1:
               q += 1
               r -= b
           return q, r
''', filename=__file__).interphook('divmod_near')


def _recover_with_smalllong(space):
    """True if there is a chance that a SmallLong would fit when an Int
    does not
    """
    return (space.config.objspace.std.withsmalllong and
            sys.maxint == 2147483647)


def _string_to_int_or_long(space, w_inttype, w_source, string, base=10):
    try:
        value = string_to_int(string, base)
    except ParseStringError as e:
        raise wrap_parsestringerror(space, e, w_source)
    except ParseStringOverflowError as e:
        return _retry_to_w_long(space, e.parser, w_inttype, w_source)

    if space.is_w(w_inttype, space.w_int):
        w_result = wrapint(space, value)
    else:
        w_result = space.allocate_instance(W_IntObject, w_inttype)
        W_IntObject.__init__(w_result, value)
    return w_result


def _retry_to_w_long(space, parser, w_inttype, w_source):
    from pypy.objspace.std.longobject import newbigint
    parser.rewind()
    try:
        bigint = rbigint._from_numberstring_parser(parser)
    except ParseStringError as e:
        raise wrap_parsestringerror(space, e, w_source)
    return newbigint(space, w_inttype, bigint)


def _new_int(space, w_inttype, w_x, w_base=None):
    from pypy.objspace.std.longobject import W_LongObject, newbigint
    if space.config.objspace.std.withsmalllong:
        from pypy.objspace.std.smalllongobject import W_SmallLongObject
    else:
        W_SmallLongObject = None

    w_longval = None
    w_value = w_x     # 'x' is the keyword argument name in CPython
    value = 0
    if w_base is None:
        # check for easy cases
        if type(w_value) is W_IntObject:
            if space.is_w(w_inttype, space.w_int):
                return w_value
            value = w_value.intval
            w_obj = space.allocate_instance(W_IntObject, w_inttype)
            W_IntObject.__init__(w_obj, value)
            return w_obj
        elif type(w_value) is W_LongObject:
            if space.is_w(w_inttype, space.w_int):
                return w_value
            return newbigint(space, w_inttype, w_value.num)
        elif W_SmallLongObject and type(w_value) is W_SmallLongObject:
            if space.is_w(w_inttype, space.w_int):
                return w_value
            return newbigint(space, w_inttype, space.bigint_w(w_value))
        elif space.lookup(w_value, '__int__') is not None:
            return _from_intlike(space, w_inttype, w_value)
        elif space.lookup(w_value, '__trunc__') is not None:
            return _from_intlike(space, w_inttype, space.trunc(w_value))
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            b = unicode_to_decimal_w(space, w_value, allow_surrogates=True)
            return _string_to_int_or_long(space, w_inttype, w_value, b)
        elif (space.isinstance_w(w_value, space.w_bytearray) or
              space.isinstance_w(w_value, space.w_bytes)):
            return _string_to_int_or_long(space, w_inttype, w_value,
                                          space.bufferstr_w(w_value))
        else:
            # If object supports the buffer interface
            try:
                buf = space.charbuf_w(w_value)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise oefmt(space.w_TypeError,
                            "int() argument must be a string or a number, "
                            "not '%T'", w_value)
            else:
                return _string_to_int_or_long(space, w_inttype, w_value, buf)
    else:
        try:
            base = space.int_w(w_base)
        except OperationError as e:
            if not e.match(space, space.w_OverflowError):
                raise
            base = 37 # this raises the right error in string_to_bigint()

        if space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value, allow_surrogates=True)
        else:
            try:
                s = space.bufferstr_w(w_value)
            except OperationError as e:
                raise oefmt(space.w_TypeError,
                            "int() can't convert non-string with explicit "
                            "base")

        return _string_to_int_or_long(space, w_inttype, w_value, s, base)


def _from_intlike(space, w_inttype, w_intlike):
    w_obj = space.int(w_intlike)
    if space.is_w(w_inttype, space.w_int):
        return w_obj
    from pypy.objspace.std.longobject import newbigint
    return newbigint(space, w_inttype, space.bigint_w(w_obj))


W_AbstractIntObject.typedef = TypeDef("int",
    __doc__ = """int(x=0) -> integer
int(x, base=10) -> integer

Convert a number or string to an integer, or return 0 if no arguments
are given.  If x is a number, return x.__int__().  For floating point
numbers, this truncates towards zero.

If x is not a number or if base is given, then x must be a string,
bytes, or bytearray instance representing an integer literal in the
given base.  The literal can be preceded by '+' or '-' and be surrounded
by whitespace.  The base defaults to 10.  Valid bases are 0 and 2-36.
Base 0 means to interpret the base from the string as an integer literal.
>>> int('0b100', base=0)
4""",
    __new__ = interp2app(W_IntObject.descr_new),

    numerator = typedef.GetSetProperty(
        W_AbstractIntObject.descr_get_numerator,
        doc="the numerator of a rational number in lowest terms"),
    denominator = typedef.GetSetProperty(
        W_AbstractIntObject.descr_get_denominator,
        doc="the denominator of a rational number in lowest terms"),
    real = typedef.GetSetProperty(
        W_AbstractIntObject.descr_get_real,
        doc="the real part of a complex number"),
    imag = typedef.GetSetProperty(
        W_AbstractIntObject.descr_get_imag,
        doc="the imaginary part of a complex number"),

    from_bytes = interp2app(W_AbstractIntObject.descr_from_bytes,
                            as_classmethod=True),
    to_bytes = interpindirect2app(W_AbstractIntObject.descr_to_bytes),

    __repr__ = interpindirect2app(W_AbstractIntObject.descr_repr),
    __str__ = interpindirect2app(W_AbstractIntObject.descr_str),

    conjugate = interpindirect2app(W_AbstractIntObject.descr_conjugate),
    bit_length = interpindirect2app(W_AbstractIntObject.descr_bit_length),
    __format__ = interpindirect2app(W_AbstractIntObject.descr_format),
    __hash__ = interpindirect2app(W_AbstractIntObject.descr_hash),
    __getnewargs__ = interpindirect2app(W_AbstractIntObject.descr_getnewargs),

    __int__ = interpindirect2app(W_AbstractIntObject.int),
    __index__ = interpindirect2app(W_AbstractIntObject.descr_index),
    __trunc__ = interpindirect2app(W_AbstractIntObject.descr_trunc),
    __float__ = interpindirect2app(W_AbstractIntObject.descr_float),
    __round__ = interpindirect2app(W_AbstractIntObject.descr_round),

    __pos__ = interpindirect2app(W_AbstractIntObject.descr_pos),
    __neg__ = interpindirect2app(W_AbstractIntObject.descr_neg),
    __abs__ = interpindirect2app(W_AbstractIntObject.descr_abs),
    __bool__ = interpindirect2app(W_AbstractIntObject.descr_bool),
    __invert__ = interpindirect2app(W_AbstractIntObject.descr_invert),
    __floor__ = interpindirect2app(W_AbstractIntObject.descr_floor),
    __ceil__ = interpindirect2app(W_AbstractIntObject.descr_ceil),

    __lt__ = interpindirect2app(W_AbstractIntObject.descr_lt),
    __le__ = interpindirect2app(W_AbstractIntObject.descr_le),
    __eq__ = interpindirect2app(W_AbstractIntObject.descr_eq),
    __ne__ = interpindirect2app(W_AbstractIntObject.descr_ne),
    __gt__ = interpindirect2app(W_AbstractIntObject.descr_gt),
    __ge__ = interpindirect2app(W_AbstractIntObject.descr_ge),

    __add__ = interpindirect2app(W_AbstractIntObject.descr_add),
    __radd__ = interpindirect2app(W_AbstractIntObject.descr_radd),
    __sub__ = interpindirect2app(W_AbstractIntObject.descr_sub),
    __rsub__ = interpindirect2app(W_AbstractIntObject.descr_rsub),
    __mul__ = interpindirect2app(W_AbstractIntObject.descr_mul),
    __rmul__ = interpindirect2app(W_AbstractIntObject.descr_rmul),

    __and__ = interpindirect2app(W_AbstractIntObject.descr_and),
    __rand__ = interpindirect2app(W_AbstractIntObject.descr_rand),
    __or__ = interpindirect2app(W_AbstractIntObject.descr_or),
    __ror__ = interpindirect2app(W_AbstractIntObject.descr_ror),
    __xor__ = interpindirect2app(W_AbstractIntObject.descr_xor),
    __rxor__ = interpindirect2app(W_AbstractIntObject.descr_rxor),

    __lshift__ = interpindirect2app(W_AbstractIntObject.descr_lshift),
    __rlshift__ = interpindirect2app(W_AbstractIntObject.descr_rlshift),
    __rshift__ = interpindirect2app(W_AbstractIntObject.descr_rshift),
    __rrshift__ = interpindirect2app(W_AbstractIntObject.descr_rrshift),

    __floordiv__ = interpindirect2app(W_AbstractIntObject.descr_floordiv),
    __rfloordiv__ = interpindirect2app(W_AbstractIntObject.descr_rfloordiv),
    __truediv__ = interpindirect2app(W_AbstractIntObject.descr_truediv),
    __rtruediv__ = interpindirect2app(W_AbstractIntObject.descr_rtruediv),
    __mod__ = interpindirect2app(W_AbstractIntObject.descr_mod),
    __rmod__ = interpindirect2app(W_AbstractIntObject.descr_rmod),
    __divmod__ = interpindirect2app(W_AbstractIntObject.descr_divmod),
    __rdivmod__ = interpindirect2app(W_AbstractIntObject.descr_rdivmod),

    __pow__ = interpindirect2app(W_AbstractIntObject.descr_pow),
    __rpow__ = interpindirect2app(W_AbstractIntObject.descr_rpow),
)


def _hash_int(a):
    sign = 1
    if a < 0:
        sign = -1
        a = -a

    x = r_uint(a)
    # efficient x % HASH_MODULUS: as HASH_MODULUS is a Mersenne
    # prime
    x = (x & HASH_MODULUS) + (x >> HASH_BITS)
    if x >= HASH_MODULUS:
        x -= HASH_MODULUS

    h = intmask(intmask(x) * sign)
    return h - (h == -1)
