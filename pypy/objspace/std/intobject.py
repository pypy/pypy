"""The builtin int implementation

In order to have the same behavior running on CPython, and after RPython
translation this module uses rarithmetic.ovfcheck to explicitly check
for overflows, something CPython does not do anymore.
"""

import operator
import sys

from rpython.rlib import jit
from rpython.rlib.objectmodel import instantiate, import_from_mixin, specialize
from rpython.rlib.rarithmetic import (
    LONG_BIT, is_valid_int, ovfcheck, r_uint, string_to_int)
from rpython.rlib.rbigint import rbigint
from rpython.rlib.rstring import (
    InvalidBaseError, ParseStringError, ParseStringOverflowError)
from rpython.tool.sourcetools import func_renamer, func_with_new_name

from pypy.interpreter import typedef
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import Buffer
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.objspace.std import newformat
from pypy.objspace.std.model import (
    BINARY_OPS, CMP_OPS, COMMUTATIVE_OPS, IDTAG_INT)
from pypy.objspace.std.stdtypedef import StdTypeDef


SENTINEL = object()


class W_AbstractIntObject(W_Root):

    __slots__ = ()

    def int(self, space):
        """x.__int__() <==> int(x)"""
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

    descr_coerce = _abstract_unaryop('coerce')
    descr_conjugate = _abstract_unaryop(
        'conjugate', "Returns self, the complex conjugate of any int.")
    descr_bit_length = _abstract_unaryop('bit_length', """\
        int.bit_length() -> int

        Number of bits necessary to represent self in binary.
        >>> bin(37)
        '0b100101'
        >>> (37).bit_length()
        6""")
    descr_hash = _abstract_unaryop('hash')
    descr_oct = _abstract_unaryop('oct')
    descr_hex = _abstract_unaryop('hex')
    descr_getnewargs = _abstract_unaryop('getnewargs', None)

    descr_long = _abstract_unaryop('long')
    descr_index = _abstract_unaryop(
        'index', "x[y:z] <==> x[y.__index__():z.__index__()]")
    descr_trunc = _abstract_unaryop('trunc',
                                    "Truncating an Integral returns itself.")
    descr_float = _abstract_unaryop('float')

    descr_pos = _abstract_unaryop('pos', "x.__pos__() <==> +x")
    descr_neg = _abstract_unaryop('neg', "x.__neg__() <==> -x")
    descr_abs = _abstract_unaryop('abs')
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
    descr_truediv, descr_rtruediv = _abstract_binop('truediv')
    descr_mod, descr_rmod = _abstract_binop('mod')
    descr_divmod, descr_rdivmod = _abstract_binop('divmod')


def _floordiv(space, x, y):
    try:
        z = ovfcheck(x // y)
    except ZeroDivisionError:
        raise oefmt(space.w_ZeroDivisionError, "integer division by zero")
    return wrapint(space, z)
_div = func_with_new_name(_floordiv, '_div')


def _truediv(space, x, y):
    a = float(x)
    b = float(y)
    if b == 0.0:
        raise oefmt(space.w_ZeroDivisionError, "division by zero")
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
        return self.intval == w_other.intval

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
            raise oefmt(space.w_ValueError,
                        "cannot convert negative integer to unsigned")
        return r_uint(intval)

    def bigint_w(self, space):
        return rbigint.fromint(self.intval)

    def float_w(self, space):
        return float(self.intval)

    def int(self, space):
        if type(self) is W_IntObject:
            return self
        if not space.is_overloaded(self, space.w_int, '__int__'):
            return space.newint(self.intval)
        return W_Root.int(self, space)

    descr_pos = func_with_new_name(int, 'descr_pos')
    descr_index = func_with_new_name(int, 'descr_index')
    descr_trunc = func_with_new_name(int, 'descr_trunc')
    descr_conjugate = func_with_new_name(int, 'descr_conjugate')

    def descr_get_numerator(self, space):
        return self.int(space)
    descr_get_real = descr_get_numerator

    def descr_get_denominator(self, space):
        return wrapint(space, 1)

    def descr_get_imag(self, space):
        return wrapint(space, 0)

    def descr_coerce(self, space, w_other):
        if not isinstance(w_other, W_AbstractIntObject):
            return space.w_NotImplemented
        return space.newtuple([self, w_other])

    def descr_long(self, space):
        from pypy.objspace.std.longobject import W_LongObject
        return W_LongObject.fromint(space, self.intval)

    def descr_hash(self, space):
        # unlike CPython, we don't special-case the value -1 in most of
        # our hash functions, so there is not much sense special-casing
        # it here either.  Make sure this is consistent with the hash of
        # floats and longs.
        return self.int(space)

    def descr_nonzero(self, space):
        return space.newbool(self.intval != 0)

    def descr_invert(self, space):
        return wrapint(space, ~self.intval)

    def descr_neg(self, space):
        a = self.intval
        try:
            x = ovfcheck(-a)
        except OverflowError:
            if _recover_with_smalllong(space):
                from pypy.objspace.std.smalllongobject import neg_ovr
                return neg_ovr(space, self)
            return self.descr_long(space).descr_neg(space)
        return wrapint(space, x)

    def descr_abs(self, space):
        pos = self.intval >= 0
        return self.int(space) if pos else self.descr_neg(space)

    def descr_float(self, space):
        a = self.intval
        x = float(a)
        return space.newfloat(x)

    def descr_oct(self, space):
        return space.wrap(oct(self.intval))

    def descr_hex(self, space):
        return space.wrap(hex(self.intval))

    def descr_getnewargs(self, space):
        return space.newtuple([wrapint(space, self.intval)])

    def descr_bit_length(self, space):
        val = self.intval
        if val < 0:
            val = -val
        bits = 0
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
        if not isinstance(w_exponent, W_IntObject):
            return space.w_NotImplemented

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
            return self._ovfpow2long(space, w_exponent, w_modulus)

        x = self.intval
        y = w_exponent.intval
        try:
            result = _pow_impl(space, x, y, z)
        except (OverflowError, ValueError):
            return self._ovfpow2long(space, w_exponent, w_modulus)
        return space.wrap(result)

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_rpow(self, space, w_base, w_modulus=None):
        if not isinstance(w_base, W_IntObject):
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
            if not isinstance(w_other, W_IntObject):
                return space.w_NotImplemented
            i = self.intval
            j = w_other.intval
            return space.newbool(op(i, j))
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

        @func_renamer('descr_' + opname)
        def descr_binop(self, space, w_other):
            if not isinstance(w_other, W_IntObject):
                return space.w_NotImplemented

            x = self.intval
            y = w_other.intval
            if ovf:
                try:
                    z = ovfcheck(op(x, y))
                except OverflowError:
                    return _ovf2long(space, opname, self, w_other)
            else:
                z = op(x, y)
            return wrapint(space, z)

        if opname in COMMUTATIVE_OPS:
            return descr_binop, func_with_new_name(descr_binop,
                                                   'descr_r' + opname)

        @func_renamer('descr_r' + opname)
        def descr_rbinop(self, space, w_other):
            if not isinstance(w_other, W_IntObject):
                return space.w_NotImplemented

            x = self.intval
            y = w_other.intval
            if ovf:
                try:
                    z = ovfcheck(op(y, x))
                except OverflowError:
                    return _ovf2long(space, opname, w_other, self)
            else:
                z = op(y, x)
            return wrapint(space, z)

        return descr_binop, descr_rbinop

    descr_add, descr_radd = _make_generic_descr_binop('add')
    descr_sub, descr_rsub = _make_generic_descr_binop('sub')
    descr_mul, descr_rmul = _make_generic_descr_binop('mul')

    descr_and, descr_rand = _make_generic_descr_binop('and', ovf=False)
    descr_or, descr_ror = _make_generic_descr_binop('or', ovf=False)
    descr_xor, descr_rxor = _make_generic_descr_binop('xor', ovf=False)

    def _make_descr_binop(func, ovf=True):
        opname = func.__name__[1:]

        @func_renamer('descr_' + opname)
        def descr_binop(self, space, w_other):
            if not isinstance(w_other, W_IntObject):
                return space.w_NotImplemented

            x = self.intval
            y = w_other.intval
            if ovf:
                try:
                    return func(space, x, y)
                except OverflowError:
                    return _ovf2long(space, opname, self, w_other)
            else:
                return func(space, x, y)

        @func_renamer('descr_r' + opname)
        def descr_rbinop(self, space, w_other):
            if not isinstance(w_other, W_IntObject):
                return space.w_NotImplemented

            x = self.intval
            y = w_other.intval
            if ovf:
                try:
                    return func(space, y, x)
                except OverflowError:
                    return _ovf2long(space, opname, w_other, self)
            else:
                return func(space, y, x)
        return descr_binop, descr_rbinop

    descr_floordiv, descr_rfloordiv = _make_descr_binop(_floordiv)
    descr_div, descr_rdiv = _make_descr_binop(_div)
    descr_truediv, descr_rtruediv = _make_descr_binop(_truediv, ovf=False)
    descr_mod, descr_rmod = _make_descr_binop(_mod)
    descr_divmod, descr_rdivmod = _make_descr_binop(_divmod)
    descr_lshift, descr_rlshift = _make_descr_binop(_lshift)
    descr_rshift, descr_rrshift = _make_descr_binop(_rshift, ovf=False)

    @staticmethod
    @unwrap_spec(w_x=WrappedDefault(0))
    def descr_new(space, w_inttype, w_x, w_base=None):
        """T.__new__(S, ...) -> a new object with type S, a subtype of T"""
        return _new_int(space, w_inttype, w_x, w_base)


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
            raise oefmt(space.w_TypeError,
                        "pow() 2nd argument cannot be negative when 3rd "
                        "argument specified")
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


def _new_int(space, w_inttype, w_x, w_base=None):
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
                raise oefmt(space.w_TypeError,
                            "int() argument must be a string or a number, "
                            "not '%T'", w_value)
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
                raise oefmt(space.w_TypeError,
                            "int() can't convert non-string with explicit "
                            "base")

        value, w_longval = _string_to_int_or_long(space, w_value, s, base)

    if w_longval is not None:
        if not space.is_w(w_inttype, space.w_int):
            raise oefmt(space.w_OverflowError,
                        "long int too large to convert to int")
        return w_longval
    elif space.is_w(w_inttype, space.w_int):
        # common case
        return wrapint(space, value)
    else:
        w_obj = space.allocate_instance(W_IntObject, w_inttype)
        W_IntObject.__init__(w_obj, value)
        return w_obj


W_IntObject.typedef = StdTypeDef("int",
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
    __new__ = interp2app(W_IntObject.descr_new),

    numerator = typedef.GetSetProperty(
        W_IntObject.descr_get_numerator,
        doc="the numerator of a rational number in lowest terms"),
    denominator = typedef.GetSetProperty(
        W_IntObject.descr_get_denominator,
        doc="the denominator of a rational number in lowest terms"),
    real = typedef.GetSetProperty(
        W_IntObject.descr_get_real,
        doc="the real part of a complex number"),
    imag = typedef.GetSetProperty(
        W_IntObject.descr_get_imag,
        doc="the imaginary part of a complex number"),

    __repr__ = interp2app(W_IntObject.descr_repr,
                          doc=W_AbstractIntObject.descr_repr.__doc__),
    __str__ = interp2app(W_IntObject.descr_str,
                         doc=W_AbstractIntObject.descr_str.__doc__),

    conjugate = interp2app(W_IntObject.descr_conjugate,
                           doc=W_AbstractIntObject.descr_conjugate.__doc__),
    bit_length = interp2app(W_IntObject.descr_bit_length,
                            doc=W_AbstractIntObject.descr_bit_length.__doc__),
    __format__ = interp2app(W_IntObject.descr_format,
                            doc=W_AbstractIntObject.descr_format.__doc__),
    __hash__ = interp2app(W_IntObject.descr_hash,
                          doc=W_AbstractIntObject.descr_hash.__doc__),
    __coerce__ = interp2app(W_IntObject.descr_coerce,
                            doc=W_AbstractIntObject.descr_coerce.__doc__),
    __oct__ = interp2app(W_IntObject.descr_oct,
                         doc=W_AbstractIntObject.descr_oct.__doc__),
    __hex__ = interp2app(W_IntObject.descr_hex,
                         doc=W_AbstractIntObject.descr_hex.__doc__),
    __getnewargs__ = interp2app(
        W_IntObject.descr_getnewargs,
        doc=W_AbstractIntObject.descr_getnewargs.__doc__),

    __int__ = interp2app(W_IntObject.int,
                         doc=W_AbstractIntObject.int.__doc__),
    __long__ = interp2app(W_IntObject.descr_long,
                          doc=W_AbstractIntObject.descr_long.__doc__),
    __index__ = interp2app(W_IntObject.descr_index,
                           doc=W_AbstractIntObject.descr_index.__doc__),
    __trunc__ = interp2app(W_IntObject.descr_trunc,
                           doc=W_AbstractIntObject.descr_trunc.__doc__),
    __float__ = interp2app(W_IntObject.descr_float,
                           doc=W_AbstractIntObject.descr_float.__doc__),

    __pos__ = interp2app(W_IntObject.descr_pos,
                         doc=W_AbstractIntObject.descr_pos.__doc__),
    __neg__ = interp2app(W_IntObject.descr_neg,
                         doc=W_AbstractIntObject.descr_neg.__doc__),
    __abs__ = interp2app(W_IntObject.descr_abs,
                         doc=W_AbstractIntObject.descr_abs.__doc__),
    __nonzero__ = interp2app(W_IntObject.descr_nonzero,
                             doc=W_AbstractIntObject.descr_nonzero.__doc__),
    __invert__ = interp2app(W_IntObject.descr_invert,
                            doc=W_AbstractIntObject.descr_invert.__doc__),

    __lt__ = interp2app(W_IntObject.descr_lt,
                        doc=W_AbstractIntObject.descr_lt.__doc__),
    __le__ = interp2app(W_IntObject.descr_le,
                        doc=W_AbstractIntObject.descr_le.__doc__),
    __eq__ = interp2app(W_IntObject.descr_eq,
                        doc=W_AbstractIntObject.descr_eq.__doc__),
    __ne__ = interp2app(W_IntObject.descr_ne,
                        doc=W_AbstractIntObject.descr_ne.__doc__),
    __gt__ = interp2app(W_IntObject.descr_gt,
                        doc=W_AbstractIntObject.descr_gt.__doc__),
    __ge__ = interp2app(W_IntObject.descr_ge,
                        doc=W_AbstractIntObject.descr_ge.__doc__),

    __add__ = interp2app(W_IntObject.descr_add,
                         doc=W_AbstractIntObject.descr_add.__doc__),
    __radd__ = interp2app(W_IntObject.descr_radd,
                          doc=W_AbstractIntObject.descr_radd.__doc__),
    __sub__ = interp2app(W_IntObject.descr_sub,
                         doc=W_AbstractIntObject.descr_sub.__doc__),
    __rsub__ = interp2app(W_IntObject.descr_rsub,
                          doc=W_AbstractIntObject.descr_rsub.__doc__),
    __mul__ = interp2app(W_IntObject.descr_mul,
                         doc=W_AbstractIntObject.descr_mul.__doc__),
    __rmul__ = interp2app(W_IntObject.descr_rmul,
                          doc=W_AbstractIntObject.descr_rmul.__doc__),

    __and__ = interp2app(W_IntObject.descr_and,
                         doc=W_AbstractIntObject.descr_and.__doc__),
    __rand__ = interp2app(W_IntObject.descr_rand,
                          doc=W_AbstractIntObject.descr_rand.__doc__),
    __or__ = interp2app(W_IntObject.descr_or,
                        doc=W_AbstractIntObject.descr_or.__doc__),
    __ror__ = interp2app(W_IntObject.descr_ror,
                         doc=W_AbstractIntObject.descr_ror.__doc__),
    __xor__ = interp2app(W_IntObject.descr_xor,
                         doc=W_AbstractIntObject.descr_xor.__doc__),
    __rxor__ = interp2app(W_IntObject.descr_rxor,
                          doc=W_AbstractIntObject.descr_rxor.__doc__),

    __lshift__ = interp2app(W_IntObject.descr_lshift,
                            doc=W_AbstractIntObject.descr_lshift.__doc__),
    __rlshift__ = interp2app(W_IntObject.descr_rlshift,
                             doc=W_AbstractIntObject.descr_rlshift.__doc__),
    __rshift__ = interp2app(W_IntObject.descr_rshift,
                            doc=W_AbstractIntObject.descr_rshift.__doc__),
    __rrshift__ = interp2app(W_IntObject.descr_rrshift,
                             doc=W_AbstractIntObject.descr_rrshift.__doc__),

    __floordiv__ = interp2app(W_IntObject.descr_floordiv,
                              doc=W_AbstractIntObject.descr_floordiv.__doc__),
    __rfloordiv__ = interp2app(
        W_IntObject.descr_rfloordiv,
        doc=W_AbstractIntObject.descr_rfloordiv.__doc__),
    __div__ = interp2app(W_IntObject.descr_div,
                         doc=W_AbstractIntObject.descr_div.__doc__),
    __rdiv__ = interp2app(W_IntObject.descr_rdiv,
                          doc=W_AbstractIntObject.descr_rdiv.__doc__),
    __truediv__ = interp2app(W_IntObject.descr_truediv,
                             doc=W_AbstractIntObject.descr_truediv.__doc__),
    __rtruediv__ = interp2app(W_IntObject.descr_rtruediv,
                              doc=W_AbstractIntObject.descr_rtruediv.__doc__),
    __mod__ = interp2app(W_IntObject.descr_mod,
                         doc=W_AbstractIntObject.descr_mod.__doc__),
    __rmod__ = interp2app(W_IntObject.descr_rmod,
                          doc=W_AbstractIntObject.descr_rmod.__doc__),
    __divmod__ = interp2app(W_IntObject.descr_divmod,
                            doc=W_AbstractIntObject.descr_divmod.__doc__),
    __rdivmod__ = interp2app(W_IntObject.descr_rdivmod,
                             doc=W_AbstractIntObject.descr_rdivmod.__doc__),

    __pow__ = interp2app(W_IntObject.descr_pow,
                         doc=W_AbstractIntObject.descr_pow.__doc__),
    __rpow__ = interp2app(W_IntObject.descr_rpow,
                          doc=W_AbstractIntObject.descr_rpow.__doc__),
)
