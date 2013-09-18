"""The builtin int implementation

In order to have the same behavior running on CPython, and after RPython
translation this module uses rarithmetic.ovfcheck to explicitly check
for overflows, something CPython does not do anymore.
"""

from rpython.rlib import jit
from rpython.rlib.rarithmetic import (
    LONG_BIT, is_valid_int, ovfcheck, string_to_int, r_uint)
from rpython.rlib.rbigint import rbigint
from rpython.rlib.objectmodel import instantiate
from rpython.rlib.rstring import ParseStringError, ParseStringOverflowError
from rpython.tool.sourcetools import func_with_new_name

from pypy.interpreter import typedef
from pypy.interpreter.buffer import Buffer
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.objspace.std import newformat
from pypy.objspace.std.model import W_Object
from pypy.objspace.std.stdtypedef import StdTypeDef


class W_AbstractIntObject(W_Object):
    __slots__ = ()

    def int(self, space):
        raise NotImplementedError

    def descr_format(self, space, w_format_spec):
        return newformat.run_formatter(space, w_format_spec,
                                       "format_int_or_long", self,
                                       newformat.INT_KIND)

    def descr_hash(self, space):
        # unlike CPython, we don't special-case the value -1 in most of
        # our hash functions, so there is not much sense special-casing
        # it here either.  Make sure this is consistent with the hash of
        # floats and longs.
        return self.int(space)

    def descr_coerce(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented
        # XXX: have to call space.int on w_other: 2
        # .__coerce__(True) -> (2, 1): actually cpython doesn't do
        # this, so i don't care!
        return space.newtuple([self, w_other])

    def _make_descr_binop(opname):
        # XXX: func_renamer or func_with_new_name?
        import operator
        from rpython.tool.sourcetools import func_renamer
        op = getattr(operator, opname)

        @func_renamer('descr_' + opname)
        def descr_binop(self, space, w_other):
            if not space.isinstance_w(w_other, space.w_int):
                return space.w_NotImplemented

            x = space.int_w(self)
            y = space.int_w(w_other)
            try:
                z = ovfcheck(op(x, y))
            except OverflowError:
                w_long1 = _delegate_Int2Long(space, self)
                # XXX: this needs to be _delegate_Int2Long(space,
                # space.int(w_other)) to support bools. so maybe delegation
                # should work against space.int_w(w_other)
                w_long2 = _delegate_Int2Long(space, w_other)
                return getattr(space, opname)(w_long1, w_long2)
            return wrapint(space, z)

        @func_renamer('descr_r' + opname)
        def descr_rbinop(self, space, w_other):
            if not space.isinstance_w(w_other, space.w_int):
                return space.w_NotImplemented

            x = space.int_w(self)
            y = space.int_w(w_other)
            try:
                z = ovfcheck(op(y, x))
            except OverflowError:
                w_long1 = _delegate_Int2Long(space, self)
                # XXX: this needs to be _delegate_Int2Long(space,
                # space.int(w_other)) to support bools. so maybe delegation
                # should work against space.int_w(w_other)
                w_long2 = _delegate_Int2Long(space, w_other)
                return getattr(space, opname)(w_long2, w_long1)
            return wrapint(space, z)

        return descr_binop, descr_rbinop

    descr_add, descr_radd = _make_descr_binop('add')
    descr_sub, descr_rsub = _make_descr_binop('sub')
    descr_mul, descr_rmul = _make_descr_binop('mul')

    def _make_descr_cmp(opname):
        import operator
        op = getattr(operator, opname)
        def f(self, space, w_other):
            if not space.isinstance_w(w_other, space.w_int):
                return space.w_NotImplemented

            i = space.int_w(self)
            j = space.int_w(w_other)
            return space.newbool(op(i, j))
        return func_with_new_name(f, "descr_" + opname)

    descr_lt = _make_descr_cmp('lt')
    descr_le = _make_descr_cmp('le')
    descr_eq = _make_descr_cmp('eq')
    descr_ne = _make_descr_cmp('ne')
    descr_gt = _make_descr_cmp('gt')
    descr_ge = _make_descr_cmp('ge')

    def descr_floordiv(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        x = space.int_w(self)
        y = space.int_w(w_other)
        try:
            z = ovfcheck(x // y)
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "integer division by zero")
        except OverflowError:
            w_long1 = _delegate_Int2Long(space, self)
            w_long2 = _delegate_Int2Long(space, w_other)
            return space.floordiv(w_long1, w_long2)
        return wrapint(space, z)

    descr_div = func_with_new_name(descr_floordiv, 'descr_div')

    def descr_truediv(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        x = float(space.int_w(self))
        y = float(space.int_w(w_other))
        if y == 0.0:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "division by zero")
        return space.wrap(x / y)

    def descr_mod(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        x = space.int_w(self)
        y = space.int_w(w_other)
        try:
            z = ovfcheck(x % y)
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "integer modulo by zero")
        except OverflowError:
            w_long1 = _delegate_Int2Long(space, self)
            w_long2 = _delegate_Int2Long(space, w_other)
            return space.mod(w_long1, w_long2)
        return wrapint(space, z)

    def descr_divmod(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        x = space.int_w(self)
        y = space.int_w(w_other)
        try:
            z = ovfcheck(x // y)
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "integer divmod by zero")
        except OverflowError:
            w_long1 = _delegate_Int2Long(space, self)
            w_long2 = _delegate_Int2Long(space, w_other)
            return space.divmod(w_long1, w_long2)

        # no overflow possible
        m = x % y
        w = space.wrap
        return space.newtuple([w(z), w(m)])

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_pow(self, space, w_exponent, w_modulus):
        if not space.isinstance_w(w_exponent, space.w_int):
            return space.w_NotImplemented
        if space.is_none(w_modulus):
            z = 0
        elif space.isinstance_w(w_modulus, space.w_int):
            # XXX: handle long... overflow?
            z = space.int_w(w_modulus)
            if z == 0:
                raise operationerrfmt(space.w_ValueError,
                                      "pow() 3rd argument cannot be 0")
        else:
            return self._delegate2longpow(space, w_exponent, w_modulus)
            #return space.w_NotImplemented

        x = space.int_w(self)
        y = space.int_w(w_exponent)
        try:
            return space.wrap(_pow_impl(space, x, y, z))
        except NotImplementedError:
            return self._delegate2longpow(space, w_exponent, w_modulus)

    def _delegate2longpow(self, space, w_exponent, w_modulus):
        # XXX: gross
        w_long1 = _delegate_Int2Long(space, self)
        w_exponent = _delegate_Int2Long(space, w_exponent)
        if not space.is_none(w_modulus):
            w_modulus = _delegate_Int2Long(space, w_modulus)
        return space.pow(w_long1, w_exponent, w_modulus)

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_rpow(self, space, w_base, w_modulus):
        if not space.isinstance_w(w_base, space.w_int):
            return space.w_NotImplemented
        # XXX: this seems like trouble?
        return space.pow(w_base, self, w_modulus)

    def descr_neg(self, space):
        a = space.int_w(self)
        try:
            x = ovfcheck(-a)
        except OverflowError:
            w_long1 = _delegate_Int2Long(space, self)
            return space.neg(w_long1)
        return wrapint(space, x)

    def descr_abs(self, space):
        return self.int(space) if space.int_w(self) >= 0 else self.descr_neg(space)

    def descr_nonzero(self, space):
        return space.newbool(space.int_w(self) != 0)

    def descr_invert(self, space):
        return wrapint(space, ~space.int_w(self))

    def descr_lshift(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        a = space.int_w(self)
        b = space.int_w(w_other)
        if r_uint(b) < LONG_BIT: # 0 <= b < LONG_BIT
            try:
                c = ovfcheck(a << b)
            except OverflowError:
                w_long1 = _delegate_Int2Long(space, self)
                w_long2 = _delegate_Int2Long(space, w_other)
                return space.lshift(w_long1, w_long2)
            return wrapint(space, c)
        if b < 0:
            raise operationerrfmt(space.w_ValueError, "negative shift count")
        else: # b >= LONG_BIT
            if a == 0:
                return self.int(space)
            w_long1 = _delegate_Int2Long(space, self)
            w_long2 = _delegate_Int2Long(space, w_other)
            return space.lshift(w_long1, w_long2)

    def descr_rshift(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        a = space.int_w(self)
        b = space.int_w(w_other)
        if r_uint(b) >= LONG_BIT: # not (0 <= b < LONG_BIT)
            if b < 0:
                raise operationerrfmt(space.w_ValueError,
                                      "negative shift count")
            else: # b >= LONG_BIT
                if a == 0:
                    return self.int(space)
                if a < 0:
                    a = -1
                else:
                    a = 0
        else:
            a = a >> b
        return wrapint(space, a)

    def descr_and(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        a = space.int_w(self)
        b = space.int_w(w_other)
        res = a & b
        return wrapint(space, res)

    def descr_or(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        a = space.int_w(self)
        b = space.int_w(w_other)
        res = a | b
        return wrapint(space, res)

    def descr_xor(self, space, w_other):
        if not space.isinstance_w(w_other, space.w_int):
            return space.w_NotImplemented

        a = space.int_w(self)
        b = space.int_w(w_other)
        res = a ^ b
        return wrapint(space, res)

    descr_rand = func_with_new_name(descr_and, 'descr_rand')
    descr_ror = func_with_new_name(descr_or, 'descr_ror')
    descr_rxor = func_with_new_name(descr_xor, 'descr_rxor')

    def descr_pos(self, space):
        return self.int(space)

    descr_trunc = func_with_new_name(descr_pos, 'descr_trunc')

    def descr_index(self, space):
        return self.int(space)

    def descr_float(self, space):
        a = space.int_w(self)
        x = float(a)
        return space.newfloat(x)

    def descr_oct(self, space):
        return space.wrap(oct(space.int_w(self)))

    def descr_hex(self, space):
        return space.wrap(hex(space.int_w(self)))

    def descr_getnewargs(self, space):
        return space.newtuple([wrapint(space, space.int_w(self))])


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
        if not isinstance(w_other, W_AbstractIntObject):
            return False
        if self.user_overridden_class or w_other.user_overridden_class:
            return self is w_other
        return space.int_w(self) == space.int_w(w_other)

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        from pypy.objspace.std.model import IDTAG_INT as tag
        b = space.bigint_w(self)
        b = b.lshift(3).or_(rbigint.fromint(tag))
        return space.newlong_from_rbigint(b)

    def unwrap(self, space):
        return int(self.intval)
    int_w = unwrap

    def uint_w(self, space):
        intval = self.intval
        if intval < 0:
            raise OperationError(
                space.w_ValueError,
                space.wrap("cannot convert negative integer to unsigned"))
        else:
            return r_uint(intval)

    def bigint_w(self, space):
        return rbigint.fromint(self.intval)

    def float_w(self, space):
        return float(self.intval)

    def int(self, space):
        if (type(self) is not W_IntObject and
            space.is_overloaded(self, space.w_int, '__int__')):
            return W_Object.int(self, space)
        if space.is_w(space.type(self), space.w_int):
            return self
        a = self.intval
        return space.newint(a)

    def descr_repr(self, space):
        res = str(self.intval)
        return space.wrap(res)

    descr_str = func_with_new_name(descr_repr, 'descr_str')

def _delegate_Int2Long(space, w_intobj):
    from pypy.objspace.std.longobject import W_LongObject
    return W_LongObject.fromint(space, w_intobj.int_w(space))


# helper for pow()
@jit.look_inside_iff(lambda space, iv, iw, iz:
                     jit.isconstant(iw) and jit.isconstant(iz))
def _pow_impl(space, iv, iw, iz):
    if iw < 0:
        if iz != 0:
            msg = ("pow() 2nd argument cannot be negative when 3rd argument "
                   "specified")
            raise operationerrfmt(space.w_TypeError, msg)
        ## bounce it, since it always returns float
        raise NotImplementedError
    temp = iv
    ix = 1
    try:
        while iw > 0:
            if iw & 1:
                ix = ovfcheck(ix*temp)
            iw >>= 1   #/* Shift exponent down by 1 bit */
            if iw==0:
                break
            temp = ovfcheck(temp*temp) #/* Square the value of temp */
            if iz:
                #/* If we did a multiplication, perform a modulo */
                ix = ix % iz;
                temp = temp % iz;
        if iz:
            ix = ix % iz
    except OverflowError:
        raise NotImplementedError
    return ix

# ____________________________________________________________

def descr_conjugate(space, w_int):
    "Returns self, the complex conjugate of any int."
    return space.int(w_int)

def descr_bit_length(space, w_int):
    """int.bit_length() -> int

    Number of bits necessary to represent self in binary.
    >>> bin(37)
    '0b100101'
    >>> (37).bit_length()
    6
    """
    val = space.int_w(w_int)
    if val < 0:
        val = -val
    bits = 0
    while val:
        bits += 1
        val >>= 1
    return space.wrap(bits)


def wrapint(space, x):
    if space.config.objspace.std.withprebuiltint:
        from pypy.objspace.std.intobject import W_IntObject
        lower = space.config.objspace.std.prebuiltintfrom
        upper =  space.config.objspace.std.prebuiltintto
        # use r_uint to perform a single comparison (this whole function
        # is getting inlined into every caller so keeping the branching
        # to a minimum is a good idea)
        index = r_uint(x - lower)
        if index >= r_uint(upper - lower):
            w_res = instantiate(W_IntObject)
        else:
            w_res = W_IntObject.PREBUILT[index]
        # obscure hack to help the CPU cache: we store 'x' even into
        # a prebuilt integer's intval.  This makes sure that the intval
        # field is present in the cache in the common case where it is
        # quickly reused.  (we could use a prefetch hint if we had that)
        w_res.intval = x
        return w_res
    else:
        from pypy.objspace.std.intobject import W_IntObject
        return W_IntObject(x)

# ____________________________________________________________

@jit.elidable
def string_to_int_or_long(space, string, base=10):
    w_longval = None
    value = 0
    try:
        value = string_to_int(string, base)
    except ParseStringError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.msg))
    except ParseStringOverflowError, e:
        w_longval = retry_to_w_long(space, e.parser)
    return value, w_longval

def retry_to_w_long(space, parser):
    parser.rewind()
    try:
        bigint = rbigint._from_numberstring_parser(parser)
    except ParseStringError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.msg))
    return space.newlong_from_rbigint(bigint)

@unwrap_spec(w_x = WrappedDefault(0))
def descr__new__(space, w_inttype, w_x, w_base=None):
    from pypy.objspace.std.intobject import W_IntObject
    w_longval = None
    w_value = w_x     # 'x' is the keyword argument name in CPython
    value = 0
    if w_base is None:
        ok = False
        # check for easy cases
        if type(w_value) is W_IntObject:
            value = w_value.intval
            ok = True
        elif space.isinstance_w(w_value, space.w_str):
            value, w_longval = string_to_int_or_long(space, space.str_w(w_value))
            ok = True
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            string = unicode_to_decimal_w(space, w_value)
            value, w_longval = string_to_int_or_long(space, string)
            ok = True
        else:
            # If object supports the buffer interface
            try:
                w_buffer = space.buffer(w_value)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
            else:
                buf = space.interp_w(Buffer, w_buffer)
                value, w_longval = string_to_int_or_long(space, buf.as_str())
                ok = True

        if not ok:
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
            try:
                value = space.int_w(w_obj)
            except OperationError, e:
                if e.match(space, space.w_TypeError):
                    raise OperationError(space.w_ValueError,
                        space.wrap("value can't be converted to int"))
                raise e
    else:
        base = space.int_w(w_base)

        if space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError, e:
                raise OperationError(space.w_TypeError,
                                     space.wrap("int() can't convert non-string "
                                                "with explicit base"))

        value, w_longval = string_to_int_or_long(space, s, base)

    if w_longval is not None:
        if not space.is_w(w_inttype, space.w_int):
            raise OperationError(space.w_OverflowError,
                                 space.wrap(
                "long int too large to convert to int"))
        return w_longval
    elif space.is_w(w_inttype, space.w_int):
        # common case
        return wrapint(space, value)
    else:
        w_obj = space.allocate_instance(W_IntObject, w_inttype)
        W_IntObject.__init__(w_obj, value)
        return w_obj

def descr_get_numerator(space, w_obj):
    return space.int(w_obj)

def descr_get_denominator(space, w_obj):
    return space.wrap(1)

def descr_get_real(space, w_obj):
    return space.int(w_obj)

def descr_get_imag(space, w_obj):
    return space.wrap(0)

# ____________________________________________________________


W_IntObject.typedef = StdTypeDef("int",
    __doc__ = '''int(x[, base]) -> integer

Convert a string or number to an integer, if possible.  A floating point
argument will be truncated towards zero (this does not include a string
representation of a floating point number!)  When converting a string, use
the optional base.  It is an error to supply a base when converting a
non-string. If the argument is outside the integer range a long object
will be returned instead.''',
    __new__ = interp2app(descr__new__),

    conjugate = interp2app(descr_conjugate),
    bit_length = interp2app(descr_bit_length),
    numerator = typedef.GetSetProperty(descr_get_numerator),
    denominator = typedef.GetSetProperty(descr_get_denominator),
    real = typedef.GetSetProperty(descr_get_real),
    imag = typedef.GetSetProperty(descr_get_imag),
    __int__ = interpindirect2app(W_AbstractIntObject.int),

    __format__ = interpindirect2app(W_AbstractIntObject.descr_format),
    __hash__ = interpindirect2app(W_AbstractIntObject.descr_hash),
    __coerce__ = interpindirect2app(W_AbstractIntObject.descr_coerce),

    __add__ = interpindirect2app(W_AbstractIntObject.descr_add),
    __radd__ = interpindirect2app(W_AbstractIntObject.descr_radd),
    __sub__ = interpindirect2app(W_AbstractIntObject.descr_sub),
    __rsub__ = interpindirect2app(W_AbstractIntObject.descr_rsub),
    __mul__ = interpindirect2app(W_AbstractIntObject.descr_mul),
    __rmul__ = interpindirect2app(W_AbstractIntObject.descr_rmul),
    __lt__ = interpindirect2app(W_AbstractIntObject.descr_lt),
    __le__ = interpindirect2app(W_AbstractIntObject.descr_le),
    __eq__ = interpindirect2app(W_AbstractIntObject.descr_eq),
    __ne__ = interpindirect2app(W_AbstractIntObject.descr_ne),
    __gt__ = interpindirect2app(W_AbstractIntObject.descr_gt),
    __ge__ = interpindirect2app(W_AbstractIntObject.descr_ge),

    __floordiv__ = interpindirect2app(W_AbstractIntObject.descr_floordiv),
    __div__ = interpindirect2app(W_AbstractIntObject.descr_div),
    __truediv__ = interpindirect2app(W_AbstractIntObject.descr_truediv),
    __mod__ = interpindirect2app(W_AbstractIntObject.descr_mod),
    __divmod__ = interpindirect2app(W_AbstractIntObject.descr_divmod),

    __pow__ = interpindirect2app(W_AbstractIntObject.descr_pow),
    __rpow__ = interpindirect2app(W_AbstractIntObject.descr_rpow),
    __neg__ = interpindirect2app(W_AbstractIntObject.descr_neg),
    __abs__ = interpindirect2app(W_AbstractIntObject.descr_abs),
    __nonzero__ = interpindirect2app(W_AbstractIntObject.descr_nonzero),
    __invert__ = interpindirect2app(W_AbstractIntObject.descr_invert),
    __lshift__ = interpindirect2app(W_AbstractIntObject.descr_lshift),
    __rshift__ = interpindirect2app(W_AbstractIntObject.descr_rshift),
    __and__ = interpindirect2app(W_AbstractIntObject.descr_and),
    __rand__ = interpindirect2app(W_AbstractIntObject.descr_rand),
    __xor__ = interpindirect2app(W_AbstractIntObject.descr_xor),
    __rxor__ = interpindirect2app(W_AbstractIntObject.descr_rxor),
    __or__ = interpindirect2app(W_AbstractIntObject.descr_or),
    __ror__ = interpindirect2app(W_AbstractIntObject.descr_ror),
    __pos__ = interpindirect2app(W_AbstractIntObject.descr_pos),
    __trunc__ = interpindirect2app(W_AbstractIntObject.descr_trunc),
    __index__ = interpindirect2app(W_AbstractIntObject.descr_index),
    __float__ = interpindirect2app(W_AbstractIntObject.descr_float),
    __oct__ = interpindirect2app(W_AbstractIntObject.descr_oct),
    __hex__ = interpindirect2app(W_AbstractIntObject.descr_hex),
    __getnewargs__ = interpindirect2app(W_AbstractIntObject.descr_getnewargs),

    __repr__ = interp2app(W_IntObject.descr_repr),
    __str__ = interp2app(W_IntObject.descr_str),
)
