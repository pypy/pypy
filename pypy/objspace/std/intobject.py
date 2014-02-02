"""The builtin int implementation

In order to have the same behavior running on CPython, and after RPython
translation this module uses rarithmetic.ovfcheck to explicitly check
for overflows, something CPython does not do anymore.
"""

import operator
import sys

from rpython.rlib import jit
from rpython.rlib.objectmodel import instantiate, specialize
from rpython.rlib.rarithmetic import (
    LONG_BIT, is_valid_int, ovfcheck, r_uint, string_to_int)
from rpython.rlib.rbigint import rbigint
from rpython.rlib.rstring import (
    InvalidBaseError, ParseStringError, ParseStringOverflowError)
from rpython.tool.sourcetools import func_renamer, func_with_new_name

from pypy.interpreter import typedef
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import Buffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.objspace.std import newformat
from pypy.objspace.std.model import (
    BINARY_OPS, CMP_OPS, COMMUTATIVE_OPS, IDTAG_INT)
from pypy.objspace.std.stdtypedef import StdTypeDef


class W_AbstractIntObject(W_Root):

    __slots__ = ()

    def int(self, space):
        """x.__int__() <==> int(x)"""
        raise NotImplementedError

    def descr_coerce(self, space, w_other):
        """x.__coerce__(y) <==> coerce(x, y)"""
        if not isinstance(w_other, W_AbstractIntObject):
            return space.w_NotImplemented
        return space.newtuple([self, w_other])

    def descr_long(self, space):
        """x.__long__() <==> long(x)"""
        from pypy.objspace.std.longobject import W_LongObject
        return W_LongObject.fromint(space, self.int_w(space))

    def descr_hash(self, space):
        """x.__hash__() <==> hash(x)"""
        # unlike CPython, we don't special-case the value -1 in most of
        # our hash functions, so there is not much sense special-casing
        # it here either.  Make sure this is consistent with the hash of
        # floats and longs.
        return self.int(space)

    def descr_nonzero(self, space):
        """x.__nonzero__() <==> x != 0"""
        return space.newbool(space.int_w(self) != 0)

    def descr_invert(self, space):
        """x.__invert__() <==> ~x"""
        return wrapint(space, ~space.int_w(self))

    def descr_pos(self, space):
        """x.__pos__() <==> +x"""
        return self.int(space)
    descr_trunc = func_with_new_name(descr_pos, 'descr_trunc')
    descr_trunc.__doc__ = 'Truncating an Integral returns itself.'

    def descr_neg(self, space):
        """x.__neg__() <==> -x"""
        a = space.int_w(self)
        try:
            x = ovfcheck(-a)
        except OverflowError:
            if _recover_with_smalllong(space):
                from pypy.objspace.std.smalllongobject import neg_ovr
                return neg_ovr(space, self)
            return self.descr_long(space).descr_neg(space)
        return wrapint(space, x)

    def descr_abs(self, space):
        """x.__abs__() <==> abs(x)"""
        pos = space.int_w(self) >= 0
        return self.int(space) if pos else self.descr_neg(space)

    def descr_index(self, space):
        """x[y:z] <==> x[y.__index__():z.__index__()]"""
        return self.int(space)

    def descr_float(self, space):
        """x.__float__() <==> float(x)"""
        a = space.int_w(self)
        x = float(a)
        return space.newfloat(x)

    def descr_oct(self, space):
        """x.__oct__() <==> oct(x)"""
        return space.wrap(oct(space.int_w(self)))

    def descr_hex(self, space):
        """x.__hex__() <==> hex(x)"""
        return space.wrap(hex(space.int_w(self)))

    def descr_getnewargs(self, space):
        return space.newtuple([wrapint(space, space.int_w(self))])

    def descr_conjugate(self, space):
        """Returns self, the complex conjugate of any int."""
        return space.int(self)

    def descr_bit_length(self, space):
        """int.bit_length() -> int

        Number of bits necessary to represent self in binary.
        >>> bin(37)
        '0b100101'
        >>> (37).bit_length()
        6
        """
        val = space.int_w(self)
        if val < 0:
            val = -val
        bits = 0
        while val:
            bits += 1
            val >>= 1
        return space.wrap(bits)

    def descr_repr(self, space):
        """x.__repr__() <==> repr(x)"""
        res = str(self.int_w(space))
        return space.wrap(res)
    descr_str = func_with_new_name(descr_repr, 'descr_str')
    descr_str.__doc__ = "x.__str__() <==> str(x)"

    def descr_format(self, space, w_format_spec):
        return newformat.run_formatter(space, w_format_spec,
                                       "format_int_or_long", self,
                                       newformat.INT_KIND)

    def descr_get_denominator(self, space):
        return space.wrap(1)

    def descr_get_imag(self, space):
        return space.wrap(0)

    descr_get_numerator = descr_get_real = descr_conjugate

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_pow(self, space, w_exponent, w_modulus=None):
        """x.__pow__(y[, z]) <==> pow(x, y[, z])"""
        if not isinstance(w_exponent, W_AbstractIntObject):
            return space.w_NotImplemented

        if space.is_none(w_modulus):
            z = 0
        elif isinstance(w_modulus, W_AbstractIntObject):
            z = space.int_w(w_modulus)
            if z == 0:
                raise operationerrfmt(space.w_ValueError,
                                      "pow() 3rd argument cannot be 0")
        else:
            # can't return NotImplemented (space.pow doesn't do full
            # ternary, i.e. w_modulus.__zpow__(self, w_exponent)), so
            # handle it ourselves
            return self._ovfpow2long(space, w_exponent, w_modulus)

        x = space.int_w(self)
        y = space.int_w(w_exponent)
        try:
            result = _pow_impl(space, x, y, z)
        except (OverflowError, ValueError):
            return self._ovfpow2long(space, w_exponent, w_modulus)
        return space.wrap(result)

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_rpow(self, space, w_base, w_modulus=None):
        """y.__rpow__(x[, z]) <==> pow(x, y[, z])"""
        if not isinstance(w_base, W_AbstractIntObject):
            return space.w_NotImplemented
        return w_base.descr_pow(space, self, w_modulus)

    def _ovfpow2long(self, space, w_exponent, w_modulus):
        if space.is_none(w_modulus) and _recover_with_smalllong(space):
            from pypy.objspace.std.smalllongobject import pow_ovr
            return pow_ovr(space, self, w_exponent)
        self = self.descr_long(space)
        return self.descr_pow(space, w_exponent, w_modulus)

    def _make_descr_cmp(opname):
        op = getattr(operator, opname)
        @func_renamer('descr_' + opname)
        def descr_cmp(self, space, w_other):
            if not isinstance(w_other, W_AbstractIntObject):
                return space.w_NotImplemented
            i = space.int_w(self)
            j = space.int_w(w_other)
            return space.newbool(op(i, j))
        descr_cmp.__doc__ = 'x.__%s__(y) <==> x%sy' % (opname, CMP_OPS[opname])
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
        oper = BINARY_OPS.get(opname)
        doc = "x.__%s__(y) <==> x%sy" % (opname, oper)
        rdoc = "x.__r%s__(y) <==> y%sx" % (opname, oper)

        @func_renamer('descr_' + opname)
        def descr_binop(self, space, w_other):
            if not isinstance(w_other, W_AbstractIntObject):
                return space.w_NotImplemented

            x = space.int_w(self)
            y = space.int_w(w_other)
            if ovf:
                try:
                    z = ovfcheck(op(x, y))
                except OverflowError:
                    return _ovf2long(space, opname, self, w_other)
            else:
                z = op(x, y)
            return wrapint(space, z)
        descr_binop.__doc__ = doc

        if opname in COMMUTATIVE_OPS:
            descr_rbinop = func_with_new_name(descr_binop, 'descr_r' + opname)
        else:
            @func_renamer('descr_r' + opname)
            def descr_rbinop(self, space, w_other):
                if not isinstance(w_other, W_AbstractIntObject):
                    return space.w_NotImplemented

                x = space.int_w(self)
                y = space.int_w(w_other)
                if ovf:
                    try:
                        z = ovfcheck(op(y, x))
                    except OverflowError:
                        return _ovf2long(space, opname, w_other, self)
                else:
                    z = op(y, x)
                return wrapint(space, z)
        descr_rbinop.__doc__ = rdoc

        return descr_binop, descr_rbinop

    descr_add, descr_radd = _make_generic_descr_binop('add')
    descr_sub, descr_rsub = _make_generic_descr_binop('sub')
    descr_mul, descr_rmul = _make_generic_descr_binop('mul')

    descr_and, descr_rand = _make_generic_descr_binop('and', ovf=False)
    descr_or, descr_ror = _make_generic_descr_binop('or', ovf=False)
    descr_xor, descr_rxor = _make_generic_descr_binop('xor', ovf=False)

    def _make_descr_binop(func, ovf=True):
        opname = func.__name__[1:]
        oper = BINARY_OPS.get(opname)
        if oper == '%':
            oper = '%%'
        oper = '%s(%%s, %%s)' % opname if not oper else '%%s%s%%s' % oper

        @func_renamer('descr_' + opname)
        def descr_binop(self, space, w_other):
            if not isinstance(w_other, W_AbstractIntObject):
                return space.w_NotImplemented
            if ovf:
                try:
                    return func(self, space, w_other)
                except OverflowError:
                    return _ovf2long(space, opname, self, w_other)
            else:
                return func(self, space, w_other)
        descr_binop.__doc__ = "x.__%s__(y) <==> %s" % (opname,
                                                       oper % ('x', 'y'))

        @func_renamer('descr_r' + opname)
        def descr_rbinop(self, space, w_other):
            if not isinstance(w_other, W_AbstractIntObject):
                return space.w_NotImplemented
            if ovf:
                try:
                    return func(w_other, space, self)
                except OverflowError:
                    return _ovf2long(space, opname, w_other, self)
            else:
                return func(w_other, space, self)
        descr_rbinop.__doc__ = "x.__r%s__(y) <==> %s" % (opname,
                                                         oper % ('y', 'x'))

        return descr_binop, descr_rbinop

    def _floordiv(self, space, w_other):
        x = space.int_w(self)
        y = space.int_w(w_other)
        try:
            z = ovfcheck(x // y)
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "integer division by zero")
        return wrapint(space, z)
    descr_floordiv, descr_rfloordiv = _make_descr_binop(_floordiv)

    _div = func_with_new_name(_floordiv, '_div')
    descr_div, descr_rdiv = _make_descr_binop(_div)

    def _truediv(self, space, w_other):
        x = float(space.int_w(self))
        y = float(space.int_w(w_other))
        if y == 0.0:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "division by zero")
        return space.wrap(x / y)
    descr_truediv, descr_rtruediv = _make_descr_binop(_truediv, ovf=False)

    def _mod(self, space, w_other):
        x = space.int_w(self)
        y = space.int_w(w_other)
        try:
            z = ovfcheck(x % y)
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "integer modulo by zero")
        return wrapint(space, z)
    descr_mod, descr_rmod = _make_descr_binop(_mod)

    def _divmod(self, space, w_other):
        x = space.int_w(self)
        y = space.int_w(w_other)
        try:
            z = ovfcheck(x // y)
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "integer divmod by zero")
        # no overflow possible
        m = x % y
        w = space.wrap
        return space.newtuple([w(z), w(m)])
    descr_divmod, descr_rdivmod = _make_descr_binop(_divmod)

    def _lshift(self, space, w_other):
        a = space.int_w(self)
        b = space.int_w(w_other)
        if r_uint(b) < LONG_BIT: # 0 <= b < LONG_BIT
            c = ovfcheck(a << b)
            return wrapint(space, c)
        if b < 0:
            raise operationerrfmt(space.w_ValueError, "negative shift count")
        # b >= LONG_BIT
        if a == 0:
            return self.int(space)
        raise OverflowError
    descr_lshift, descr_rlshift = _make_descr_binop(_lshift)

    def _rshift(self, space, w_other):
        a = space.int_w(self)
        b = space.int_w(w_other)
        if r_uint(b) >= LONG_BIT: # not (0 <= b < LONG_BIT)
            if b < 0:
                raise operationerrfmt(space.w_ValueError,
                                      "negative shift count")
            # b >= LONG_BIT
            if a == 0:
                return self.int(space)
            a = -1 if a < 0 else 0
        else:
            a = a >> b
        return wrapint(space, a)
    descr_rshift, descr_rrshift = _make_descr_binop(_rshift, ovf=False)


class W_IntObject(W_AbstractIntObject):

    __slots__ = 'intval'
    _immutable_fields_ = ['intval']

    def __init__(self, intval):
        assert is_valid_int(intval)
        self.intval = intval

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%d)" % (self.__class__.__name__, self.intval)

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_IntObject):
            return False
        if self.user_overridden_class or w_other.user_overridden_class:
            return self is w_other
        return space.int_w(self) == space.int_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        b = space.bigint_w(self)
        b = b.lshift(3).or_(rbigint.fromint(IDTAG_INT))
        return space.newlong_from_rbigint(b)

    def int_w(self, space):
        return int(self.intval)
    unwrap = int_w

    def uint_w(self, space):
        intval = self.intval
        if intval < 0:
            raise operationerrfmt(space.w_ValueError,
                                  "cannot convert negative integer to "
                                  "unsigned")
        return r_uint(intval)

    def bigint_w(self, space):
        return rbigint.fromint(self.intval)

    def float_w(self, space):
        return float(self.intval)

    def int(self, space):
        if (type(self) is not W_IntObject and
            space.is_overloaded(self, space.w_int, '__int__')):
            return W_Root.int(self, space)
        if space.is_w(space.type(self), space.w_int):
            return self
        a = self.intval
        return space.newint(a)


def _recover_with_smalllong(space):
    # True if there is a chance that a SmallLong would fit when an Int
    # does not
    return (space.config.objspace.std.withsmalllong and
            sys.maxint == 2147483647)


@specialize.arg(1)
def _ovf2long(space, opname, self, w_other):
    if _recover_with_smalllong(space) and opname != 'truediv':
        from pypy.objspace.std import smalllongobject
        op = getattr(smalllongobject, opname + '_ovr')
        return op(space, self, w_other)
    self = self.descr_long(space)
    w_other = w_other.descr_long(space)
    return getattr(self, 'descr_' + opname)(space, w_other)


# helper for pow()
@jit.look_inside_iff(lambda space, iv, iw, iz:
                     jit.isconstant(iw) and jit.isconstant(iz))
def _pow_impl(space, iv, iw, iz):
    if iw < 0:
        if iz != 0:
            raise operationerrfmt(space.w_TypeError,
                                  "pow() 2nd argument cannot be negative when "
                                  "3rd argument specified")
        # bounce it, since it always returns float
        raise ValueError
    temp = iv
    ix = 1
    while iw > 0:
        if iw & 1:
            ix = ovfcheck(ix * temp)
        iw >>= 1   # Shift exponent down by 1 bit
        if iw == 0:
            break
        temp = ovfcheck(temp * temp) # Square the value of temp
        if iz:
            # If we did a multiplication, perform a modulo
            ix %= iz
            temp %= iz
    if iz:
        ix %= iz
    return ix


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


@jit.elidable
def _string_to_int_or_long(space, w_source, string, base=10):
    w_longval = None
    value = 0
    try:
        value = string_to_int(string, base)
    except ParseStringError as e:
        raise wrap_parsestringerror(space, e, w_source)
    except ParseStringOverflowError as e:
        w_longval = _retry_to_w_long(space, e.parser, w_source)
    return value, w_longval


def _retry_to_w_long(space, parser, w_source):
    parser.rewind()
    try:
        bigint = rbigint._from_numberstring_parser(parser)
    except ParseStringError as e:
        raise wrap_parsestringerror(space, e, w_source)
    return space.newlong_from_rbigint(bigint)


def wrap_parsestringerror(space, e, w_source):
    if isinstance(e, InvalidBaseError):
        w_msg = space.wrap(e.msg)
    else:
        w_msg = space.wrap('%s: %s' % (e.msg,
                                       space.str_w(space.repr(w_source))))
    return OperationError(space.w_ValueError, w_msg)


@unwrap_spec(w_x=WrappedDefault(0))
def descr__new__(space, w_inttype, w_x, w_base=None):
    w_longval = None
    w_value = w_x     # 'x' is the keyword argument name in CPython
    value = 0
    if w_base is None:
        # check for easy cases
        if type(w_value) is W_IntObject:
            value = w_value.intval
        elif space.lookup(w_value, '__int__') is not None or \
                space.lookup(w_value, '__trunc__') is not None:
            # otherwise, use the __int__() or the __trunc__() methods
            w_obj = w_value
            if space.lookup(w_obj, '__int__') is None:
                w_obj = space.trunc(w_obj)
            w_obj = space.int(w_obj)
            # 'int(x)' should return what x.__int__() returned, which should
            # be an int or long or a subclass thereof.
            if space.is_w(w_inttype, space.w_int):
                return w_obj
            # int_w is effectively what we want in this case,
            # we cannot construct a subclass of int instance with an
            # an overflowing long
            value = space.int_w(w_obj)
        elif space.isinstance_w(w_value, space.w_str):
            value, w_longval = _string_to_int_or_long(space, w_value,
                                                      space.str_w(w_value))
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            string = unicode_to_decimal_w(space, w_value)
            value, w_longval = _string_to_int_or_long(space, w_value, string)
        else:
            # If object supports the buffer interface
            try:
                w_buffer = space.buffer(w_value)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise operationerrfmt(space.w_TypeError,
                    "int() argument must be a string or a number, not '%T'",
                    w_value)
            else:
                buf = space.interp_w(Buffer, w_buffer)
                value, w_longval = _string_to_int_or_long(space, w_value,
                                                          buf.as_str())
                ok = True
    else:
        base = space.int_w(w_base)

        if space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError as e:
                raise operationerrfmt(space.w_TypeError,
                                      "int() can't convert non-string with "
                                      "explicit base")

        value, w_longval = _string_to_int_or_long(space, w_value, s, base)

    if w_longval is not None:
        if not space.is_w(w_inttype, space.w_int):
            raise operationerrfmt(space.w_OverflowError,
                                  "long int too large to convert to int")
        return w_longval
    elif space.is_w(w_inttype, space.w_int):
        # common case
        return wrapint(space, value)
    else:
        w_obj = space.allocate_instance(W_IntObject, w_inttype)
        W_IntObject.__init__(w_obj, value)
        return w_obj


W_AbstractIntObject.typedef = StdTypeDef("int",
    __doc__ = """int(x=0) -> int or long
int(x, base=10) -> int or long

Convert a number or string to an integer, or return 0 if no arguments
are given.  If x is floating point, the conversion truncates towards zero.
If x is outside the integer range, the function returns a long instead.

If x is not a number or if base is given, then x must be a string or
Unicode object representing an integer literal in the given base.  The
literal can be preceded by '+' or '-' and be surrounded by whitespace.
The base defaults to 10.  Valid bases are 0 and 2-36.  Base 0 means to
interpret the base from the string as an integer literal.
>>> int('0b100', base=0)
4""",
    __new__ = interp2app(descr__new__),

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

    __repr__ = interp2app(W_AbstractIntObject.descr_repr),
    __str__ = interp2app(W_AbstractIntObject.descr_str),

    conjugate = interpindirect2app(W_AbstractIntObject.descr_conjugate),
    bit_length = interpindirect2app(W_AbstractIntObject.descr_bit_length),
    __format__ = interpindirect2app(W_AbstractIntObject.descr_format),
    __hash__ = interpindirect2app(W_AbstractIntObject.descr_hash),
    __coerce__ = interpindirect2app(W_AbstractIntObject.descr_coerce),
    __oct__ = interpindirect2app(W_AbstractIntObject.descr_oct),
    __hex__ = interpindirect2app(W_AbstractIntObject.descr_hex),
    __getnewargs__ = interpindirect2app(W_AbstractIntObject.descr_getnewargs),

    __int__ = interpindirect2app(W_AbstractIntObject.int),
    __long__ = interpindirect2app(W_AbstractIntObject.descr_long),
    __index__ = interpindirect2app(W_AbstractIntObject.descr_index),
    __trunc__ = interpindirect2app(W_AbstractIntObject.descr_trunc),
    __float__ = interpindirect2app(W_AbstractIntObject.descr_float),

    __pos__ = interpindirect2app(W_AbstractIntObject.descr_pos),
    __neg__ = interpindirect2app(W_AbstractIntObject.descr_neg),
    __abs__ = interpindirect2app(W_AbstractIntObject.descr_abs),
    __nonzero__ = interpindirect2app(W_AbstractIntObject.descr_nonzero),
    __invert__ = interpindirect2app(W_AbstractIntObject.descr_invert),

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
    __div__ = interpindirect2app(W_AbstractIntObject.descr_div),
    __rdiv__ = interpindirect2app(W_AbstractIntObject.descr_rdiv),
    __truediv__ = interpindirect2app(W_AbstractIntObject.descr_truediv),
    __rtruediv__ = interpindirect2app(W_AbstractIntObject.descr_rtruediv),
    __mod__ = interpindirect2app(W_AbstractIntObject.descr_mod),
    __rmod__ = interpindirect2app(W_AbstractIntObject.descr_rmod),
    __divmod__ = interpindirect2app(W_AbstractIntObject.descr_divmod),
    __rdivmod__ = interpindirect2app(W_AbstractIntObject.descr_rdivmod),

    __pow__ = interpindirect2app(W_AbstractIntObject.descr_pow),
    __rpow__ = interpindirect2app(W_AbstractIntObject.descr_rpow),
)
