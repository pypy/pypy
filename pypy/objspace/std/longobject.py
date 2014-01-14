"""The builtin long implementation"""

import functools

from rpython.rlib.objectmodel import specialize
from rpython.rlib.rbigint import rbigint
from rpython.rlib.rstring import ParseStringError
from rpython.tool.sourcetools import func_renamer, func_with_new_name

from pypy.interpreter import typedef
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import Buffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.objspace.std import newformat
from pypy.objspace.std.intobject import W_AbstractIntObject
from pypy.objspace.std.model import (
    BINARY_OPS, CMP_OPS, COMMUTATIVE_OPS, IDTAG_LONG)
from pypy.objspace.std.stdtypedef import StdTypeDef


def delegate_other(func):
    @functools.wraps(func)
    def delegated(self, space, w_other):
        if isinstance(w_other, W_AbstractIntObject):
            w_other = w_other.descr_long(space)
        elif not isinstance(w_other, W_AbstractLongObject):
            return space.w_NotImplemented
        return func(self, space, w_other)
    return delegated


class W_AbstractLongObject(W_Root):

    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractLongObject):
            return False
        if self.user_overridden_class or w_other.user_overridden_class:
            return self is w_other
        return space.bigint_w(self).eq(space.bigint_w(w_other))

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        b = space.bigint_w(self)
        b = b.lshift(3).or_(rbigint.fromint(IDTAG_LONG))
        return space.newlong_from_rbigint(b)

    def unwrap(self, space):
        return self.longval()

    def int(self, space):
        raise NotImplementedError

    def asbigint(self):
        raise NotImplementedError

    def descr_getnewargs(self, space):
        return space.newtuple([newlong(space, self.asbigint())])

    def descr_conjugate(self, space):
        """Returns self, the complex conjugate of any long."""
        return space.long(self)

    def descr_bit_length(self, space):
        """long.bit_length() -> int or long

        Number of bits necessary to represent self in binary.
        >>> bin(37L)
        '0b100101'
        >>> (37L).bit_length()
        6
        """
        bigint = space.bigint_w(self)
        try:
            return space.wrap(bigint.bit_length())
        except OverflowError:
            raise operationerrfmt(space.w_OverflowError,
                                  "too many digits in integer")

    def _truediv(self, space, w_other):
        try:
            f = self.asbigint().truediv(w_other.asbigint())
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "long division or modulo by zero")
        except OverflowError:
            raise operationerrfmt(space.w_OverflowError,
                                  "long/long too large for a float")
        return space.newfloat(f)

    @delegate_other
    def descr_truediv(self, space, w_other):
        """x.__truediv__(y) <==> x/y"""
        return W_AbstractLongObject._truediv(self, space, w_other)

    @delegate_other
    def descr_rtruediv(self, space, w_other):
        """x.__rtruediv__(y) <==> y/x"""
        return W_AbstractLongObject._truediv(w_other, space, self)

    @delegate_other
    def descr_coerce(self, space, w_other):
        """x.__coerce__(y) <==> coerce(x, y)"""
        return space.newtuple([self, w_other])

    def descr_get_numerator(self, space):
        return space.long(self)
    descr_get_real = func_with_new_name(descr_get_numerator, 'descr_get_real')

    def descr_format(self, space, w_format_spec):
        return newformat.run_formatter(space, w_format_spec,
                                       "format_int_or_long", self,
                                       newformat.LONG_KIND)

    def descr_get_denominator(self, space):
        return space.newlong(1)

    def descr_get_imag(self, space):
        return space.newlong(0)

    def _make_descr_unaryop(opname):
        op = getattr(rbigint, opname)
        @func_renamer('descr_' + opname)
        def descr_unaryop(self, space):
            return space.wrap(op(self.asbigint()))
        descr_unaryop.__doc__ = 'x.__%s__(y) <==> %s(x, y)' % (opname, opname)
        return descr_unaryop

    descr_repr = _make_descr_unaryop('repr')
    descr_str = _make_descr_unaryop('str')
    descr_hash = _make_descr_unaryop('hash')
    descr_oct = _make_descr_unaryop('oct')
    descr_hex = _make_descr_unaryop('hex')

    def descr_pow(self, space, w_exponent, w_modulus=None):
        """x.__pow__(y[, z]) <==> pow(x, y[, z])"""
        raise NotImplementedError
    descr_rpow = func_with_new_name(descr_pow, 'descr_rpow')
    descr_rpow.__doc__ = "y.__rpow__(x[, z]) <==> pow(x, y[, z])"

    def _abstract_unaryop(opname, doc=None):
        @func_renamer('descr_' + opname)
        def descr_unaryop(self, space):
            raise NotImplementedError
        descr_unaryop.__doc__ = doc
        return descr_unaryop

    descr_long = _abstract_unaryop('long', "x.__long__() <==> long(x)")
    descr_float = _abstract_unaryop('float', "x.__float__() <==> float(x)")
    descr_index = _abstract_unaryop(
        'index', "x[y:z] <==> x[y.__index__():z.__index__()]")
    descr_trunc = _abstract_unaryop('trunc',
                                    "Truncating an Integral returns itself.")
    descr_pos = _abstract_unaryop('pos', "x.__pos__() <==> +x")
    descr_neg = _abstract_unaryop('neg', "x.__neg__() <==> -x")
    descr_abs = _abstract_unaryop('abs', "x.__abs__() <==> abs(x)")
    descr_nonzero = _abstract_unaryop('nonzero', "x.__nonzero__() <==> x != 0")
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
    descr_div, descr_rdiv = _abstract_binop('div')
    descr_mod, descr_rmod = _abstract_binop('mod')
    descr_divmod, descr_rdivmod = _abstract_binop('divmod')


class W_LongObject(W_AbstractLongObject):
    """This is a wrapper of rbigint."""

    _immutable_fields_ = ['num']

    def __init__(self, num):
        self.num = num # instance of rbigint

    @staticmethod
    def fromint(space, intval):
        return W_LongObject(rbigint.fromint(intval))

    def longval(self):
        return self.num.tolong()

    def tofloat(self, space):
        try:
            return self.num.tofloat()
        except OverflowError:
            raise operationerrfmt(space.w_OverflowError,
                                  "long int too large to convert to float")

    def toint(self):
        return self.num.toint()

    @staticmethod
    def fromfloat(space, f):
        return newlong(space, rbigint.fromfloat(f))

    @staticmethod
    def fromlong(l):
        return W_LongObject(rbigint.fromlong(l))

    @staticmethod
    @specialize.argtype(0)
    def fromrarith_int(i):
        return W_LongObject(rbigint.fromrarith_int(i))

    def int_w(self, space):
        try:
            return self.num.toint()
        except OverflowError:
            raise operationerrfmt(space.w_OverflowError,
                                  "long int too large to convert to int")

    def uint_w(self, space):
        try:
            return self.num.touint()
        except ValueError:
            raise operationerrfmt(space.w_ValueError,
                                  "cannot convert negative integer to "
                                  "unsigned int")
        except OverflowError:
            raise operationerrfmt(space.w_OverflowError,
                                  "long int too large to convert to unsigned "
                                  "int")

    def bigint_w(self, space):
        return self.num

    def float_w(self, space):
        return self.tofloat(space)

    def int(self, space):
        if (type(self) is not W_LongObject and
            space.is_overloaded(self, space.w_long, '__int__')):
            return W_Root.int(self, space)
        try:
            return space.newint(self.num.toint())
        except OverflowError:
            return self.descr_long(space)

    def asbigint(self):
        return self.num

    def __repr__(self):
        return '<W_LongObject(%d)>' % self.num.tolong()

    def descr_long(self, space):
        # __long__ is supposed to do nothing, unless it has a derived
        # long object, where it should return an exact one.
        if space.is_w(space.type(self), space.w_long):
            return self
        return W_LongObject(self.num)
    descr_index = descr_trunc = descr_pos = descr_long

    def descr_float(self, space):
        return space.newfloat(self.tofloat(space))

    def descr_nonzero(self, space):
        return space.newbool(self.num.tobool())

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_pow(self, space, w_exponent, w_modulus=None):
        if isinstance(w_exponent, W_AbstractIntObject):
            w_exponent = w_exponent.descr_long(space)
        elif not isinstance(w_exponent, W_AbstractLongObject):
            return space.w_NotImplemented

        if space.is_none(w_modulus):
            if w_exponent.asbigint().sign < 0:
                self = self.descr_float(space)
                w_exponent = w_exponent.descr_float(space)
                return space.pow(self, w_exponent, space.w_None)
            return W_LongObject(self.num.pow(w_exponent.asbigint()))
        elif isinstance(w_modulus, W_AbstractIntObject):
            w_modulus = w_modulus.descr_long(space)
        elif not isinstance(w_modulus, W_AbstractLongObject):
            return space.w_NotImplemented

        if w_exponent.asbigint().sign < 0:
            raise operationerrfmt(space.w_TypeError,
                                  "pow() 2nd argument cannot be negative when "
                                  "3rd argument specified")
        try:
            result = self.num.pow(w_exponent.asbigint(), w_modulus.asbigint())
        except ValueError:
            raise operationerrfmt(space.w_ValueError,
                                  "pow 3rd argument cannot be 0")
        return W_LongObject(result)

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_rpow(self, space, w_base, w_modulus=None):
        if isinstance(w_base, W_AbstractIntObject):
            w_base = w_base.descr_long(space)
        elif not isinstance(w_base, W_AbstractLongObject):
            return space.w_NotImplemented
        return w_base.descr_pow(space, self, w_modulus)

    def _make_descr_unaryop(opname):
        op = getattr(rbigint, opname)
        @func_renamer('descr_' + opname)
        def descr_unaryop(self, space):
            return W_LongObject(op(self.num))
        return descr_unaryop

    descr_neg = _make_descr_unaryop('neg')
    descr_abs = _make_descr_unaryop('abs')
    descr_invert = _make_descr_unaryop('invert')

    def _make_descr_cmp(opname):
        op = getattr(rbigint, opname)
        @delegate_other
        def descr_impl(self, space, w_other):
            # XXX: previous impl had all kinds of shortcuts between
            # smalllong and int/long
            return space.newbool(op(self.num, w_other.asbigint()))
        return func_with_new_name(descr_impl, "descr_" + opname)

    descr_lt = _make_descr_cmp('lt')
    descr_le = _make_descr_cmp('le')
    descr_eq = _make_descr_cmp('eq')
    descr_ne = _make_descr_cmp('ne')
    descr_gt = _make_descr_cmp('gt')
    descr_ge = _make_descr_cmp('ge')

    def _make_generic_descr_binop(opname):
        methname = opname + '_' if opname in ('and', 'or') else opname
        op = getattr(rbigint, methname)

        @func_renamer('descr_' + opname)
        @delegate_other
        def descr_binop(self, space, w_other):
            return W_LongObject(op(self.num, w_other.asbigint()))

        if opname in COMMUTATIVE_OPS:
            descr_rbinop = func_with_new_name(descr_binop, 'descr_r' + opname)
        else:
            @func_renamer('descr_r' + opname)
            @delegate_other
            def descr_rbinop(self, space, w_other):
                # XXX: delegate, for --objspace-std-withsmalllong
                return W_LongObject(op(w_other.asbigint(), self.num))

        return descr_binop, descr_rbinop

    descr_add, descr_radd = _make_generic_descr_binop('add')
    descr_sub, descr_rsub = _make_generic_descr_binop('sub')
    descr_mul, descr_rmul = _make_generic_descr_binop('mul')
    descr_and, descr_rand = _make_generic_descr_binop('and')
    descr_or, descr_ror = _make_generic_descr_binop('or')
    descr_xor, descr_rxor = _make_generic_descr_binop('xor')

    def _make_descr_binop(func):
        opname = func.__name__[1:]

        @delegate_other
        @func_renamer('descr_' + opname)
        def descr_binop(self, space, w_other):
            return func(self, space, w_other)

        @delegate_other
        @func_renamer('descr_r' + opname)
        def descr_rbinop(self, space, w_other):
            if not isinstance(w_other, W_LongObject):
                # coerce other W_AbstractLongObjects
                w_other = W_LongObject(w_other.asbigint())
            return func(w_other, space, self)

        return descr_binop, descr_rbinop

    def _lshift(self, space, w_other):
        if w_other.asbigint().sign < 0:
            raise operationerrfmt(space.w_ValueError, "negative shift count")
        try:
            shift = w_other.asbigint().toint()
        except OverflowError:   # b too big
            raise operationerrfmt(space.w_OverflowError,
                                  "shift count too large")
        return W_LongObject(self.num.lshift(shift))
    descr_lshift, descr_rlshift = _make_descr_binop(_lshift)

    def _rshift(self, space, w_other):
        if w_other.asbigint().sign < 0:
            raise operationerrfmt(space.w_ValueError, "negative shift count")
        try:
            shift = w_other.asbigint().toint()
        except OverflowError:   # b too big # XXX maybe just return 0L instead?
            raise operationerrfmt(space.w_OverflowError,
                                  "shift count too large")
        return newlong(space, self.num.rshift(shift))
    descr_rshift, descr_rrshift = _make_descr_binop(_rshift)

    def _floordiv(self, space, w_other):
        try:
            z = self.num.floordiv(w_other.asbigint())
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "long division or modulo by zero")
        return newlong(space, z)
    descr_floordiv, descr_rfloordiv = _make_descr_binop(_floordiv)

    _div = func_with_new_name(_floordiv, '_div')
    descr_div, descr_rdiv = _make_descr_binop(_div)

    def _mod(self, space, w_other):
        try:
            z = self.num.mod(w_other.asbigint())
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "long division or modulo by zero")
        return newlong(space, z)
    descr_mod, descr_rmod = _make_descr_binop(_mod)

    def _divmod(self, space, w_other):
        try:
            div, mod = self.num.divmod(w_other.asbigint())
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "long division or modulo by zero")
        return space.newtuple([newlong(space, div), newlong(space, mod)])
    descr_divmod, descr_rdivmod = _make_descr_binop(_divmod)


def newlong(space, bigint):
    """Turn the bigint into a W_LongObject.  If withsmalllong is
    enabled, check if the bigint would fit in a smalllong, and return a
    W_SmallLongObject instead if it does.
    """
    if space.config.objspace.std.withsmalllong:
        try:
            z = bigint.tolonglong()
        except OverflowError:
            pass
        else:
            from pypy.objspace.std.smalllongobject import W_SmallLongObject
            return W_SmallLongObject(z)
    return W_LongObject(bigint)


@unwrap_spec(w_x=WrappedDefault(0))
def descr__new__(space, w_longtype, w_x, w_base=None):
    if space.config.objspace.std.withsmalllong:
        from pypy.objspace.std.smalllongobject import W_SmallLongObject
    else:
        W_SmallLongObject = None

    w_value = w_x     # 'x' is the keyword argument name in CPython
    if w_base is None:
        # check for easy cases
        if (W_SmallLongObject and type(w_value) is W_SmallLongObject
            and space.is_w(w_longtype, space.w_long)):
            return w_value
        elif type(w_value) is W_LongObject:
            return newbigint(space, w_longtype, w_value.num)
        elif (space.lookup(w_value, '__long__') is not None or
              space.lookup(w_value, '__int__') is not None):
            w_obj = space.long(w_value)
            return newbigint(space, w_longtype, space.bigint_w(w_obj))
        elif space.lookup(w_value, '__trunc__') is not None:
            w_obj = space.trunc(w_value)
            # :-(  blame CPython 2.7
            if space.lookup(w_obj, '__long__') is not None:
                w_obj = space.long(w_obj)
            else:
                w_obj = space.int(w_obj)
            return newbigint(space, w_longtype, space.bigint_w(w_obj))
        elif space.isinstance_w(w_value, space.w_str):
            return _string_to_w_long(space, w_longtype, space.str_w(w_value))
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            return _string_to_w_long(space, w_longtype,
                                     unicode_to_decimal_w(space, w_value))
        else:
            try:
                w_buffer = space.buffer(w_value)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise operationerrfmt(space.w_TypeError,
                    "long() argument must be a string or a number, not '%T'",
                    w_value)
            else:
                buf = space.interp_w(Buffer, w_buffer)
                return _string_to_w_long(space, w_longtype, buf.as_str())
    else:
        base = space.int_w(w_base)

        if space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError:
                raise operationerrfmt(space.w_TypeError,
                                      "long() can't convert non-string with "
                                      "explicit base")
        return _string_to_w_long(space, w_longtype, s, base)


def _string_to_w_long(space, w_longtype, s, base=10):
    try:
        bigint = rbigint.fromstr(s, base)
    except ParseStringError as e:
        raise OperationError(space.w_ValueError, space.wrap(e.msg))
    return newbigint(space, w_longtype, bigint)
_string_to_w_long._dont_inline_ = True


def newbigint(space, w_longtype, bigint):
    """Turn the bigint into a W_LongObject.  If withsmalllong is enabled,
    check if the bigint would fit in a smalllong, and return a
    W_SmallLongObject instead if it does.  Similar to newlong() in
    longobject.py, but takes an explicit w_longtype argument.
    """
    if (space.config.objspace.std.withsmalllong
        and space.is_w(w_longtype, space.w_long)):
        try:
            z = bigint.tolonglong()
        except OverflowError:
            pass
        else:
            from pypy.objspace.std.smalllongobject import W_SmallLongObject
            return W_SmallLongObject(z)
    w_obj = space.allocate_instance(W_LongObject, w_longtype)
    W_LongObject.__init__(w_obj, bigint)
    return w_obj


W_AbstractLongObject.typedef = StdTypeDef("long",
    __doc__ = """long(x=0) -> long
long(x, base=10) -> long

Convert a number or string to a long integer, or return 0L if no arguments
are given.  If x is floating point, the conversion truncates towards zero.

If x is not a number or if base is given, then x must be a string or
Unicode object representing an integer literal in the given base.  The
literal can be preceded by '+' or '-' and be surrounded by whitespace.
The base defaults to 10.  Valid bases are 0 and 2-36.  Base 0 means to
interpret the base from the string as an integer literal.
>>> int('0b100', base=0)
4L""",
    __new__ = interp2app(descr__new__),

    numerator = typedef.GetSetProperty(
        W_AbstractLongObject.descr_get_numerator,
        doc="the numerator of a rational number in lowest terms"),
    denominator = typedef.GetSetProperty(
        W_AbstractLongObject.descr_get_denominator,
        doc="the denominator of a rational number in lowest terms"),
    real = typedef.GetSetProperty(
        W_AbstractLongObject.descr_get_real,
        doc="the real part of a complex number"),
    imag = typedef.GetSetProperty(
        W_AbstractLongObject.descr_get_imag,
        doc="the imaginary part of a complex number"),

    __repr__ = interp2app(W_AbstractLongObject.descr_repr),
    __str__ = interp2app(W_AbstractLongObject.descr_str),

    conjugate = interpindirect2app(W_AbstractLongObject.descr_conjugate),
    bit_length = interpindirect2app(W_AbstractLongObject.descr_bit_length),
    __format__ = interpindirect2app(W_AbstractLongObject.descr_format),
    __hash__ = interpindirect2app(W_AbstractLongObject.descr_hash),
    __coerce__ = interpindirect2app(W_AbstractLongObject.descr_coerce),
    __oct__ = interpindirect2app(W_AbstractLongObject.descr_oct),
    __hex__ = interpindirect2app(W_AbstractLongObject.descr_hex),
    __getnewargs__ = interpindirect2app(W_AbstractLongObject.descr_getnewargs),

    __int__ = interpindirect2app(W_AbstractLongObject.int),
    __long__ = interpindirect2app(W_AbstractLongObject.descr_long),
    __index__ = interpindirect2app(W_AbstractLongObject.descr_index),
    __trunc__ = interpindirect2app(W_AbstractLongObject.descr_trunc),
    __float__ = interpindirect2app(W_AbstractLongObject.descr_float),

    __pos__ = interpindirect2app(W_AbstractLongObject.descr_pos),
    __neg__ = interpindirect2app(W_AbstractLongObject.descr_neg),
    __abs__ = interpindirect2app(W_AbstractLongObject.descr_abs),
    __nonzero__ = interpindirect2app(W_AbstractLongObject.descr_nonzero),
    __invert__ = interpindirect2app(W_AbstractLongObject.descr_invert),

    __lt__ = interpindirect2app(W_AbstractLongObject.descr_lt),
    __le__ = interpindirect2app(W_AbstractLongObject.descr_le),
    __eq__ = interpindirect2app(W_AbstractLongObject.descr_eq),
    __ne__ = interpindirect2app(W_AbstractLongObject.descr_ne),
    __gt__ = interpindirect2app(W_AbstractLongObject.descr_gt),
    __ge__ = interpindirect2app(W_AbstractLongObject.descr_ge),

    __add__ = interpindirect2app(W_AbstractLongObject.descr_add),
    __radd__ = interpindirect2app(W_AbstractLongObject.descr_radd),
    __sub__ = interpindirect2app(W_AbstractLongObject.descr_sub),
    __rsub__ = interpindirect2app(W_AbstractLongObject.descr_rsub),
    __mul__ = interpindirect2app(W_AbstractLongObject.descr_mul),
    __rmul__ = interpindirect2app(W_AbstractLongObject.descr_rmul),

    __and__ = interpindirect2app(W_AbstractLongObject.descr_and),
    __rand__ = interpindirect2app(W_AbstractLongObject.descr_rand),
    __or__ = interpindirect2app(W_AbstractLongObject.descr_or),
    __ror__ = interpindirect2app(W_AbstractLongObject.descr_ror),
    __xor__ = interpindirect2app(W_AbstractLongObject.descr_xor),
    __rxor__ = interpindirect2app(W_AbstractLongObject.descr_rxor),

    __lshift__ = interpindirect2app(W_AbstractLongObject.descr_lshift),
    __rlshift__ = interpindirect2app(W_AbstractLongObject.descr_rlshift),
    __rshift__ = interpindirect2app(W_AbstractLongObject.descr_rshift),
    __rrshift__ = interpindirect2app(W_AbstractLongObject.descr_rrshift),

    __floordiv__ = interpindirect2app(W_AbstractLongObject.descr_floordiv),
    __rfloordiv__ = interpindirect2app(W_AbstractLongObject.descr_rfloordiv),
    __div__ = interpindirect2app(W_AbstractLongObject.descr_div),
    __rdiv__ = interpindirect2app(W_AbstractLongObject.descr_rdiv),
    __truediv__ = interpindirect2app(W_AbstractLongObject.descr_truediv),
    __rtruediv__ = interpindirect2app(W_AbstractLongObject.descr_rtruediv),
    __mod__ = interpindirect2app(W_AbstractLongObject.descr_mod),
    __rmod__ = interpindirect2app(W_AbstractLongObject.descr_rmod),
    __divmod__ = interpindirect2app(W_AbstractLongObject.descr_divmod),
    __rdivmod__ = interpindirect2app(W_AbstractLongObject.descr_rdivmod),

    __pow__ = interpindirect2app(W_AbstractLongObject.descr_pow),
    __rpow__ = interpindirect2app(W_AbstractLongObject.descr_rpow),
)
