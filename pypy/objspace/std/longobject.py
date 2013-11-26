"""The builtin long implementation"""

import sys

from rpython.rlib.rbigint import rbigint
from rpython.rlib.rstring import ParseStringError
from rpython.tool.sourcetools import func_renamer, func_with_new_name

from pypy.interpreter import typedef
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.objspace.std import model, newformat
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.model import W_Object
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.stdtypedef import StdTypeDef


def delegate_other(func):
    @func_renamer(func.__name__)
    def delegated(self, space, w_other):
        if space.isinstance_w(w_other, space.w_int):
            w_other = _delegate_Int2Long(space, w_other)
        elif not space.isinstance_w(w_other, space.w_long):
            return space.w_NotImplemented
        # XXX: if a smalllong, delegate to Long?
        assert isinstance(w_other, W_AbstractLongObject)
        return func(self, space, w_other)
    return delegated

def _delegate_Int2Long(space, w_intobj):
    """int-to-long delegation"""
    return W_LongObject.fromint(space, w_intobj.int_w(space))


class W_AbstractLongObject(W_Object):
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
        from pypy.objspace.std.model import IDTAG_LONG as tag
        b = space.bigint_w(self)
        b = b.lshift(3).or_(rbigint.fromint(tag))
        return space.newlong_from_rbigint(b)

    def unwrap(w_self, space): #YYYYYY
        return w_self.longval()

    def int(self, space):
        raise NotImplementedError

    def asbigint(self):
        raise NotImplementedError

    def descr_long(self, space):
        raise NotImplementedError
    descr_index = func_with_new_name(descr_long, 'descr_index')
    descr_trunc = func_with_new_name(descr_long, 'descr_trunc')
    descr_pos = func_with_new_name(descr_long, 'descr_pos')

    # XXX:
    def descr_float(self, space):
        raise NotImplementedError
    descr_neg = func_with_new_name(descr_long, 'descr_neg')
    descr_pos = func_with_new_name(descr_long, 'descr_pos')
    descr_abs = func_with_new_name(descr_long, 'descr_abs')
    descr_nonzero = func_with_new_name(descr_long, 'descr_nonzero')
    descr_invert = func_with_new_name(descr_long, 'descr_invert')

    def descr_lt(self, space, w_other):
        raise NotImplementedError
    descr_le = func_with_new_name(descr_lt, 'descr_le')
    descr_eq = func_with_new_name(descr_lt, 'descr_eq')
    descr_ne = func_with_new_name(descr_lt, 'descr_ne')
    descr_gt = func_with_new_name(descr_lt, 'descr_gt')
    descr_ge = func_with_new_name(descr_lt, 'descr_ge')

    descr_add = func_with_new_name(descr_lt, 'descr_add')
    descr_radd = func_with_new_name(descr_lt, 'descr_radd')
    descr_sub = func_with_new_name(descr_lt, 'descr_sub')
    descr_rsub = func_with_new_name(descr_lt, 'descr_rsub')
    descr_mul = func_with_new_name(descr_lt, 'descr_mul')
    descr_rmul = func_with_new_name(descr_lt, 'descr_rmul')

    descr_and = func_with_new_name(descr_lt, 'descr_and')
    descr_rand = func_with_new_name(descr_lt, 'descr_rand')
    descr_or = func_with_new_name(descr_lt, 'descr_or')
    descr_ror = func_with_new_name(descr_lt, 'descr_ror')
    descr_xor = func_with_new_name(descr_lt, 'descr_xor')
    descr_rxor = func_with_new_name(descr_lt, 'descr_rxor')

    descr_lshift = func_with_new_name(descr_lt, 'descr_lshift')
    descr_rshift = func_with_new_name(descr_lt, 'descr_rshift')

    descr_floordiv = func_with_new_name(descr_lt, 'descr_floordiv')
    descr_rfloordiv = func_with_new_name(descr_lt, 'descr_rfloordiv')
    descr_div = func_with_new_name(descr_lt, 'descr_div')
    descr_rdiv = func_with_new_name(descr_lt, 'descr_rdiv')
    descr_mod = func_with_new_name(descr_lt, 'descr_mod')
    descr_rmod = func_with_new_name(descr_lt, 'descr_rmod')
    descr_divmod = func_with_new_name(descr_lt, 'descr_divmod')
    descr_rdivmod = func_with_new_name(descr_lt, 'descr_rdivmod')

    def descr_pow(self, space, w_exponent, w_modulus=None):
        raise NotImplementedError
    descr_rpow = func_with_new_name(descr_pow, 'descr_rpow')

    def descr_format(self, space, w_format_spec):
        return newformat.run_formatter(space, w_format_spec,
                                       "format_int_or_long", self,
                                       newformat.LONG_KIND)
    def descr_repr(self, space):
        return space.wrap(self.asbigint().repr())

    def descr_str(self, space):
        return space.wrap(self.asbigint().str())

    def descr_hash(self, space):
        return space.wrap(self.asbigint().hash())

    def descr_oct(self, space):
        return space.wrap(self.asbigint().oct())

    def descr_hex(self, space):
        return space.wrap(self.asbigint().hex())

    def descr_getnewargs(self, space):
        return space.newtuple([W_LongObject(self.asbigint())])

    def descr_conjugate(self, space):
        return space.long(self)

    def descr_bit_length(self, space):
        bigint = space.bigint_w(self)
        try:
            return space.wrap(bigint.bit_length())
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                                 space.wrap("too many digits in integer"))

    # XXX: need rtruediv
    @delegate_other
    def descr_truediv(self, space, w_other):
        try:
            #f = self.num.truediv(w_other.num)
            f = self.asbigint().truediv(w_other.asbigint())
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "long division or modulo by zero")
        except OverflowError:
            raise operationerrfmt(space.w_OverflowError,
                                  "long/long too large for a float")
        return space.newfloat(f)

    @delegate_other
    def descr_coerce(self, space, w_other):
        # XXX: consider stian's branch where he optimizes long + ints
        return space.newtuple([self, w_other])

    def descr_get_numerator(self, space):
        return space.long(self)
    descr_get_real = func_with_new_name(descr_get_numerator, 'descr_get_real')

    def descr_get_denominator(self, space):
        return space.newlong(1)

    def descr_get_imag(self, space):
        return space.newlong(0)


class W_LongObject(W_AbstractLongObject):
    """This is a wrapper of rbigint."""
    _immutable_fields_ = ['num']

    def __init__(self, l):
        self.num = l # instance of rbigint

    def fromint(space, intval):
        return W_LongObject(rbigint.fromint(intval))
    fromint = staticmethod(fromint)

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

    def fromfloat(space, f):
        return newlong(space, rbigint.fromfloat(f))
    fromfloat = staticmethod(fromfloat)

    def fromlong(l):
        return W_LongObject(rbigint.fromlong(l))
    fromlong = staticmethod(fromlong)

    def fromrarith_int(i):
        return W_LongObject(rbigint.fromrarith_int(i))
    fromrarith_int._annspecialcase_ = "specialize:argtype(0)"
    fromrarith_int = staticmethod(fromrarith_int)

    def int_w(self, space):
        try:
            return self.num.toint()
        except OverflowError:
            raise OperationError(space.w_OverflowError, space.wrap(
                "long int too large to convert to int"))

    def uint_w(self, space):
        try:
            return self.num.touint()
        except ValueError:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot convert negative integer to unsigned int"))
        except OverflowError:
            raise OperationError(space.w_OverflowError, space.wrap(
                "long int too large to convert to unsigned int"))

    def bigint_w(self, space):
        return self.num

    def float_w(self, space):
        return self.tofloat(space)

    def int(self, space):
        if (type(self) is not W_LongObject and
            space.is_overloaded(self, space.w_long, '__int__')):
            return W_Object.int(self, space)
        try:
            return space.newint(self.num.toint())
        except OverflowError:
            return self.descr_long(space)

    def asbigint(self):
        return self.num

    def __repr__(self):
        return '<W_LongObject(%d)>' % self.num.tolong()

    def descr_long(self, space):
        # long__Long is supposed to do nothing, unless it has a derived
        # long object, where it should return an exact one.
        if space.is_w(space.type(self), space.w_long):
            return self
        l = self.num
        return W_LongObject(l)
    descr_index = func_with_new_name(descr_long, 'descr_index')
    descr_trunc = func_with_new_name(descr_long, 'descr_trunc')
    descr_pos = func_with_new_name(descr_long, 'descr_pos')

    def descr_float(self, space):
        return space.newfloat(self.tofloat(space))

    def _make_descr_cmp(opname):
        #from pypy.objspace.std.smalllongobject import W_SmallLongObject
        op = getattr(rbigint, opname)
        @delegate_other
        def descr_impl(self, space, w_other):
            ## XXX: these only need explicit SmallLong support whereas
            ## everything else would delegate2Long. blah blah
            #if isinstance(w_other, W_SmallLongObject):
            #    result = op(self.num, w_other.asbigint())
            #else:
            #    result = op(self.num, w_other.num)
            #return space.newbool(result)

            # XXX: if we use self.asbigint then can this live on
            # AbstractLong? eek not really, a '_cmp' (_lt) could live on
            # it that just did this (without the checks..)
            return space.newbool(op(self.num, w_other.asbigint()))
        return func_with_new_name(descr_impl, "descr_" + opname)

    descr_lt = _make_descr_cmp('lt')
    descr_le = _make_descr_cmp('le')
    descr_eq = _make_descr_cmp('eq')
    descr_ne = _make_descr_cmp('ne')
    descr_gt = _make_descr_cmp('gt')
    descr_ge = _make_descr_cmp('ge')

    def _make_descr_binop(opname):
        from rpython.tool.sourcetools import func_renamer
        methname = opname + '_' if opname in ('and', 'or') else opname
        op = getattr(rbigint, methname)

        @func_renamer('descr_' + opname)
        @delegate_other
        def descr_binop(self, space, w_other):
            return W_LongObject(op(self.num, w_other.asbigint()))

        @func_renamer('descr_r' + opname)
        @delegate_other
        def descr_rbinop(self, space, w_other):
            return W_LongObject(op(w_other.asbigint(), self.num))

        return descr_binop, descr_rbinop

    descr_add, descr_radd = _make_descr_binop('add')
    descr_sub, descr_rsub = _make_descr_binop('sub')
    descr_mul, descr_rmul = _make_descr_binop('mul')
    descr_and, descr_rand = _make_descr_binop('and')
    descr_or, descr_ror = _make_descr_binop('or')
    descr_xor, descr_rxor = _make_descr_binop('xor')

    def _make_descr_unaryop(opname):
        from rpython.tool.sourcetools import func_renamer
        op = getattr(rbigint, opname)
        @func_renamer('descr_' + opname)
        def descr_unaryop(self, space):
            return W_LongObject(op(self.num))
        return descr_unaryop

    descr_neg = _make_descr_unaryop('neg')
    descr_abs = _make_descr_unaryop('abs')
    descr_invert = _make_descr_unaryop('invert')

    def descr_nonzero(self, space):
        return space.newbool(self.num.tobool())

    @delegate_other
    def descr_lshift(self, space, w_other):
        # XXX need to replicate some of the logic, to get the errors right
        if w_other.asbigint().sign < 0:
            raise operationerrfmt(space.w_ValueError, "negative shift count")
        try:
            shift = w_other.asbigint().toint()
        except OverflowError:   # b too big
            raise operationerrfmt(space.w_OverflowError,
                                  "shift count too large")
        return W_LongObject(self.num.lshift(shift))

    @delegate_other
    def descr_rshift(self, space, w_other):
        # XXX need to replicate some of the logic, to get the errors right
        if w_other.asbigint().sign < 0:
            raise operationerrfmt(space.w_ValueError, "negative shift count")
        try:
            shift = w_other.asbigint().toint()
        except OverflowError:   # b too big # XXX maybe just return 0L instead?
            raise operationerrfmt(space.w_OverflowError,
                                  "shift count too large")
        return newlong(space, self.num.rshift(shift))

    @delegate_other
    def descr_floordiv(self, space, w_other):
        try:
            z = self.num.floordiv(w_other.asbigint())
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "long division or modulo by zero")
        return newlong(space, z)
    descr_div = func_with_new_name(descr_floordiv, 'descr_div')

    @delegate_other
    def descr_mod(self, space, w_other):
        try:
            z = self.num.mod(w_other.asbigint())
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "long division or modulo by zero")
        return newlong(space, z)

    @delegate_other
    def descr_divmod(self, space, w_other):
        try:
            div, mod = self.num.divmod(w_other.asbigint())
        except ZeroDivisionError:
            raise operationerrfmt(space.w_ZeroDivisionError,
                                  "long division or modulo by zero")
        return space.newtuple([newlong(space, div), newlong(space, mod)])

    #@delegate_other # XXX:
    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_pow(self, space, w_exponent, w_modulus=None):
        if space.isinstance_w(w_exponent, space.w_int):
            w_exponent = _delegate_Int2Long(space, w_exponent)
        elif not space.isinstance_w(w_exponent, space.w_long):
            return space.w_NotImplemented
        assert isinstance(w_exponent, W_AbstractLongObject)

        #if space.is_none(w_modulus):
        #    from pypy.objspace.std.floatobject import delegate_Long2Float
        #    self = delegate_Long2Float(space, self)
        #    w_exponent = delegate_Long2Float(space, w_exponent)
        #    return space.pow(self, w_exponent, w_modulus)
        #elif space.isinstance_w(w_modulus, space.w_int):
        if space.is_none(w_modulus):
            # XXX need to replicate some of the logic, to get the errors right
            if w_exponent.asbigint().sign < 0:
                from pypy.objspace.std.floatobject import delegate_Long2Float
                w_exponent = delegate_Long2Float(space, w_exponent)
                # XXX: hack around multimethod annoyances for now (when
                # w_modulus=None)
                return space.pow(self.descr_float(space), w_exponent, space.w_None if w_modulus is None else w_modulus)
            return W_LongObject(self.num.pow(w_exponent.asbigint(), None))
        elif space.isinstance_w(w_modulus, space.w_int):
            w_modulus = _delegate_Int2Long(space, w_modulus)
        #elif space.is_none(w_modulus):
        #    # XXX need to replicate some of the logic, to get the errors right
        #    if w_exponent.num.sign < 0:
        #        return space.pow(self.descr_float(space), w_exponent, w_modulus)
        #    return W_LongObject(self.num.pow(w_exponent.num, None))
        elif not space.isinstance_w(w_modulus, space.w_long):
            return space.w_NotImplemented
        assert isinstance(w_modulus, W_AbstractLongObject)

        if w_exponent.asbigint().sign < 0:
            raise OperationError(
                space.w_TypeError,
                space.wrap(
                    "pow() 2nd argument "
                    "cannot be negative when 3rd argument specified"))
        try:
            return W_LongObject(self.num.pow(w_exponent.asbigint(),
                                             w_modulus.asbigint()))
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("pow 3rd argument cannot be 0"))

    @unwrap_spec(w_modulus=WrappedDefault(None))
    def descr_rpow(self, space, w_exponent, w_modulus=None):
        if space.isinstance_w(w_exponent, space.w_int):
            w_exponent = _delegate_Int2Long(space, w_exponent)
        elif not space.isinstance_w(w_exponent, space.w_long):
            return space.w_NotImplemented
        ### XXX: these may needs all the checks above has. annoying
        #if not space.isinstance_w(w_exponent, space.w_long):
        #    return space.w_NotImplemented
        # XXX:
        return space.pow(w_exponent, self, w_modulus)

    def descr_getnewargs(self, space):
        return space.newtuple([W_LongObject(self.num)])


def newlong(space, bigint):
    """Turn the bigint into a W_LongObject.  If withsmalllong is enabled,
    check if the bigint would fit in a smalllong, and return a
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


# register implementations of ops that recover int op overflows
def recover_with_smalllong(space):
    # True if there is a chance that a SmallLong would fit when an Int does not
    return (space.config.objspace.std.withsmalllong and
            sys.maxint == 2147483647)

# XXX:
# binary ops
for opname in ['add', 'sub', 'mul', 'div', 'floordiv', 'truediv', 'mod',
               'divmod', 'lshift']:
    exec compile("""
def %(opname)s_ovr__Int_Int(space, w_int1, w_int2):
    if recover_with_smalllong(space) and %(opname)r != 'truediv':
        from pypy.objspace.std.smalllongobject import %(opname)s_ovr
        return %(opname)s_ovr(space, w_int1, w_int2)
    w_long1 = _delegate_Int2Long(space, w_int1)
    w_long2 = _delegate_Int2Long(space, w_int2)
    #return %(opname)s__Long_Long(space, w_long1, w_long2)
    return w_long1.descr_%(opname)s(space, w_long2)
""" % {'opname': opname}, '', 'exec')

    getattr(model.MM, opname).register(globals()['%s_ovr__Int_Int' % opname],
                                       W_IntObject, W_IntObject, order=1)

# unary ops
for opname in ['neg', 'abs']:
    exec """
def %(opname)s_ovr__Int(space, w_int1):
    if recover_with_smalllong(space):
        from pypy.objspace.std.smalllongobject import %(opname)s_ovr
        return %(opname)s_ovr(space, w_int1)
    w_long1 = _delegate_Int2Long(space, w_int1)
    #return %(opname)s__Long(space, w_long1)
    return w_long1.descr_%(opname)s(space)
""" % {'opname': opname}

    getattr(model.MM, opname).register(globals()['%s_ovr__Int' % opname],
                                       W_IntObject, order=1)

# pow
def pow_ovr__Int_Int_None(space, w_int1, w_int2, w_none3):
    if recover_with_smalllong(space):
        from pypy.objspace.std.smalllongobject import pow_ovr
        return pow_ovr(space, w_int1, w_int2)
    w_long1 = _delegate_Int2Long(space, w_int1)
    w_long2 = _delegate_Int2Long(space, w_int2)
    #return pow__Long_Long_None(space, w_long1, w_long2, w_none3)
    return w_long1.descr_pow(space, w_long2, w_none3)

def pow_ovr__Int_Int_Long(space, w_int1, w_int2, w_long3):
    w_long1 = _delegate_Int2Long(space, w_int1)
    w_long2 = _delegate_Int2Long(space, w_int2)
    #return pow__Long_Long_Long(space, w_long1, w_long2, w_long3)
    return w_long1.descr_pow(space, w_long2, w_long3)

model.MM.pow.register(pow_ovr__Int_Int_None, W_IntObject, W_IntObject,
                      W_NoneObject, order=1)
model.MM.pow.register(pow_ovr__Int_Int_Long, W_IntObject, W_IntObject,
                      W_LongObject, order=1)


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
        elif space.isinstance_w(w_value, space.w_str):
            return string_to_w_long(space, w_longtype, space.str_w(w_value))
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            return string_to_w_long(space, w_longtype,
                                    unicode_to_decimal_w(space, w_value))
        else:
            # otherwise, use the __long__() or the __trunc__ methods
            w_obj = w_value
            if (space.lookup(w_obj, '__long__') is not None or
                space.lookup(w_obj, '__int__') is not None):
                w_obj = space.long(w_obj)
            elif space.lookup(w_obj, '__trunc__') is not None:
                w_obj = space.trunc(w_obj)
                # :-(  blame CPython 2.7
                if space.lookup(w_obj, '__long__') is not None:
                    w_obj = space.long(w_obj)
                else:
                    w_obj = space.int(w_obj)
            else:
                raise operationerrfmt(space.w_TypeError,
                    "long() argument must be a string or a number, not '%T'",
                    w_obj)
            bigint = space.bigint_w(w_obj)
            return newbigint(space, w_longtype, bigint)
    else:
        base = space.int_w(w_base)

        if space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError:
                msg = "long() can't convert non-string with explicit base"
                raise operationerrfmt(space.w_TypeError, msg)
        return string_to_w_long(space, w_longtype, s, base)


def string_to_w_long(space, w_longtype, s, base=10):
    try:
        bigint = rbigint.fromstr(s, base)
    except ParseStringError as e:
        raise OperationError(space.w_ValueError, space.wrap(e.msg))
    return newbigint(space, w_longtype, bigint)
string_to_w_long._dont_inline_ = True


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
    __doc__ = """long(x[, base]) -> integer

Convert a string or number to a long integer, if possible.  A floating
point argument will be truncated towards zero (this does not include a
string representation of a floating point number!)  When converting a
string, use the optional base.  It is an error to supply a base when
converting a non-string.""",
    __new__ = interp2app(descr__new__),

    numerator = typedef.GetSetProperty(
        W_AbstractLongObject.descr_get_numerator),
    denominator = typedef.GetSetProperty(
        W_AbstractLongObject.descr_get_denominator),
    real = typedef.GetSetProperty(W_AbstractLongObject.descr_get_real),
    imag = typedef.GetSetProperty(W_AbstractLongObject.descr_get_imag),
    conjugate = interp2app(W_AbstractLongObject.descr_conjugate),
    bit_length = interp2app(W_AbstractLongObject.descr_bit_length),

    # XXX: likely need indirect everything for SmallLong
    __int__ = interpindirect2app(W_AbstractLongObject.int),
    __long__ = interpindirect2app(W_AbstractLongObject.descr_long),
    __index__ = interpindirect2app(W_AbstractLongObject.descr_index),
    __trunc__ = interpindirect2app(W_AbstractLongObject.descr_trunc),
    __float__ = interpindirect2app(W_AbstractLongObject.descr_float),

    __repr__ = interp2app(W_AbstractLongObject.descr_repr),
    __str__ = interp2app(W_AbstractLongObject.descr_str),
    __format__ = interp2app(W_AbstractLongObject.descr_format),

    __hash__ = interp2app(W_AbstractLongObject.descr_hash),
    __coerce__ = interp2app(W_AbstractLongObject.descr_coerce),

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

    __neg__ = interpindirect2app(W_AbstractLongObject.descr_neg),
    __pos__ = interpindirect2app(W_AbstractLongObject.descr_pos),
    __abs__ = interpindirect2app(W_AbstractLongObject.descr_abs),
    __nonzero__ = interpindirect2app(W_AbstractLongObject.descr_nonzero),
    __invert__ = interpindirect2app(W_AbstractLongObject.descr_invert),

    __oct__ = interp2app(W_AbstractLongObject.descr_oct),
    __hex__ = interp2app(W_AbstractLongObject.descr_hex),

    __lshift__ = interpindirect2app(W_AbstractLongObject.descr_lshift),
    __rshift__ = interpindirect2app(W_AbstractLongObject.descr_rshift),

    # XXX: all these need r sides
    __truediv__ = interp2app(W_AbstractLongObject.descr_truediv),
    __floordiv__ = interpindirect2app(W_AbstractLongObject.descr_floordiv),
    __div__ = interpindirect2app(W_AbstractLongObject.descr_div),
    __mod__ = interpindirect2app(W_AbstractLongObject.descr_mod),
    __divmod__ = interpindirect2app(W_AbstractLongObject.descr_divmod),

    __pow__ = interpindirect2app(W_AbstractLongObject.descr_pow),
    __rpow__ = interpindirect2app(W_AbstractLongObject.descr_rpow),

    __getnewargs__ = interp2app(W_AbstractLongObject.descr_getnewargs),
)
