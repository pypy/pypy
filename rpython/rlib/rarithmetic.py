"""
This file defines restricted arithmetic:

classes and operations to express integer arithmetic,
such that before and after translation semantics are
consistent

r_uint   an unsigned integer which has no overflow
         checking. It is always positive and always
         truncated to the internal machine word size.
intmask  mask a possibly long value when running on CPython
         back to a signed int value
ovfcheck check on CPython whether the result of a signed
         integer operation did overflow
ovfcheck_float_to_int
         convert to an integer or raise OverflowError
r_longlong
         like r_int but double word size
r_ulonglong
         like r_uint but double word size
widen(x)
         if x is of a type smaller than lltype.Signed or
         lltype.Unsigned, widen it to lltype.Signed.
         Useful because the translator doesn't support
         arithmetic on the smaller types.

These are meant to be erased by translation, r_uint
in the process should mark unsigned values, ovfcheck should
mark where overflow checking is required.


"""
import sys, struct
from rpython.rtyper import extregistry
from rpython.rlib import objectmodel
from rpython.flowspace.model import Constant, const
from rpython.flowspace.specialcase import register_flow_sc

"""
Long-term target:
We want to make pypy very flexible concerning its data type layout.
This is a larger task for later.

Short-term target:
We want to run PyPy on windows 64 bit.

Problem:
On windows 64 bit, integers are only 32 bit. This is a problem for PyPy
right now, since it assumes that a c long can hold a pointer.
We therefore set up the target machine constants to obey this rule.
Right now this affects 64 bit Python only on windows.

Note: We use the struct module, because the array module doesn's support
all typecodes.
"""

def _get_bitsize(typecode):
    return len(struct.pack(typecode, 1)) * 8

_long_typecode = 'l'
if _get_bitsize('P') > _get_bitsize('l'):
    _long_typecode = 'P'

def _get_long_bit():
    # whatever size a long has, make it big enough for a pointer.
    return _get_bitsize(_long_typecode)

# exported for now for testing array values.
# might go into its own module.
def get_long_pattern(x):
    """get the bit pattern for a long, adjusted to pointer size"""
    return struct.pack(_long_typecode, x)

# used in tests for ctypes and for genc and friends
# to handle the win64 special case:
is_emulated_long = _long_typecode != 'l'

LONG_BIT = _get_long_bit()
LONG_MASK = (2**LONG_BIT)-1
LONG_TEST = 2**(LONG_BIT-1)

# XXX this is a good guess, but what if a long long is 128 bit?
LONGLONG_BIT  = 64
LONGLONG_MASK = (2**LONGLONG_BIT)-1
LONGLONG_TEST = 2**(LONGLONG_BIT-1)

LONG_BIT_SHIFT = 0
while (1 << LONG_BIT_SHIFT) != LONG_BIT:
    LONG_BIT_SHIFT += 1
    assert LONG_BIT_SHIFT < 99, "LONG_BIT_SHIFT value not found?"

LONGLONGLONG_BIT  = 128
LONGLONGLONG_MASK = (2**LONGLONGLONG_BIT)-1
LONGLONGLONG_TEST = 2**(LONGLONGLONG_BIT-1)

"""
int is no longer necessarily the same size as the target int.
We therefore can no longer use the int type as it is, but need
to use long everywhere.
"""

# XXX returning int(n) should not be necessary and should be simply n.
# XXX TODO: replace all int(n) by long(n) and fix everything that breaks.
# XXX       Then relax it and replace int(n) by n.
def intmask(n):
    """
    NOT_RPYTHON
    """
    if isinstance(n, objectmodel.Symbolic):
        return n        # assume Symbolics don't overflow
    assert not isinstance(n, float)
    if is_valid_int(n):
        return int(n)
    n = long(n)
    n &= LONG_MASK
    if n >= LONG_TEST:
        n -= 2*LONG_TEST
    return int(n)

def longlongmask(n):
    """
    NOT_RPYTHON
    """
    assert isinstance(n, (int, long))
    n = long(n)
    n &= LONGLONG_MASK
    if n >= LONGLONG_TEST:
        n -= 2*LONGLONG_TEST
    return r_longlong(n)

def longlonglongmask(n):
    # Assume longlonglong doesn't overflow. This is perfectly fine for rbigint.
    # We deal directly with overflow there anyway.
    return r_longlonglong(n)

def widen(n):
    from rpython.rtyper.lltypesystem import lltype
    if _should_widen_type(lltype.typeOf(n)):
        return intmask(n)
    else:
        return n
widen._annspecialcase_ = 'specialize:argtype(0)'

def _should_widen_type(tp):
    from rpython.rtyper.lltypesystem import lltype, rffi
    if tp is lltype.Bool:
        return True
    if tp is lltype.Signed:
        return False
    r_class = rffi.platform.numbertype_to_rclass[tp]
    assert issubclass(r_class, base_int)
    return r_class.BITS < LONG_BIT
_should_widen_type._annspecialcase_ = 'specialize:memo'

# the replacement for sys.maxint
maxint = int(LONG_TEST - 1)

def is_valid_int(r):
    if objectmodel.we_are_translated():
        return isinstance(r, int)
    return isinstance(r, (base_int, int, long, bool)) and (
        -maxint - 1 <= r <= maxint)
is_valid_int._annspecialcase_ = 'specialize:argtype(0)'

def ovfcheck(r):
    "NOT_RPYTHON"
    # to be used as ovfcheck(x <op> y)
    # raise OverflowError if the operation did overflow
    assert not isinstance(r, r_uint), "unexpected ovf check on unsigned"
    assert not isinstance(r, r_longlong), "ovfcheck not supported on r_longlong"
    assert not isinstance(r, r_ulonglong), "ovfcheck not supported on r_ulonglong"
    if type(r) is long and not is_valid_int(r):
        # checks only if applicable to r's type.
        # this happens in the garbage collector.
        raise OverflowError, "signed integer expression did overflow"
    return r

# Strange things happening for float to int on 64 bit:
# int(float(i)) != i  because of rounding issues.
# These are the minimum and maximum float value that can
# successfully be casted to an int.
if sys.maxint == 2147483647:
    def ovfcheck_float_to_int(x):
        from rpython.rlib.rfloat import isnan
        if isnan(x):
            raise OverflowError
        if -2147483649.0 < x < 2147483648.0:
            return int(x)
        raise OverflowError
else:
    # The following values are not quite +/-sys.maxint.
    # Note the "<= x <" here, as opposed to "< x <" above.
    # This is justified by test_typed in translator/c/test.
    def ovfcheck_float_to_int(x):
        from rpython.rlib.rfloat import isnan
        if isnan(x):
            raise OverflowError
        if -9223372036854776832.0 <= x < 9223372036854775296.0:
            return int(x)
        raise OverflowError

def compute_restype(self_type, other_type):
    if self_type is other_type:
        if self_type is bool:
            return int
        return self_type
    if other_type in (bool, int, long):
        if self_type is bool:
            return int
        return self_type
    if self_type in (bool, int, long):
        return other_type
    if self_type.SIGNED == other_type.SIGNED:
        return build_int(None, self_type.SIGNED, max(self_type.BITS, other_type.BITS))
    raise AssertionError, "Merging these types (%s, %s) is not supported" % (self_type, other_type)

def signedtype(t):
    if t in (bool, int, long):
        return True
    else:
        return t.SIGNED
signedtype._annspecialcase_ = 'specialize:memo'

def normalizedinttype(t):
    if t is int:
        return int
    if t.BITS <= r_int.BITS:
        return build_int(None, t.SIGNED, r_int.BITS)
    else:
        assert t.BITS <= r_longlong.BITS
        return build_int(None, t.SIGNED, r_longlong.BITS)

def most_neg_value_of_same_type(x):
    from rpython.rtyper.lltypesystem import lltype
    return most_neg_value_of(lltype.typeOf(x))
most_neg_value_of_same_type._annspecialcase_ = 'specialize:argtype(0)'

def most_neg_value_of(tp):
    from rpython.rtyper.lltypesystem import lltype, rffi
    if tp is lltype.Signed:
        return -sys.maxint-1
    r_class = rffi.platform.numbertype_to_rclass[tp]
    assert issubclass(r_class, base_int)
    if r_class.SIGNED:
        return r_class(-(r_class.MASK >> 1) - 1)
    else:
        return r_class(0)
most_neg_value_of._annspecialcase_ = 'specialize:memo'

def most_pos_value_of_same_type(x):
    from rpython.rtyper.lltypesystem import lltype
    return most_pos_value_of(lltype.typeOf(x))
most_pos_value_of_same_type._annspecialcase_ = 'specialize:argtype(0)'

def most_pos_value_of(tp):
    from rpython.rtyper.lltypesystem import lltype, rffi
    if tp is lltype.Signed:
        return sys.maxint
    r_class = rffi.platform.numbertype_to_rclass[tp]
    assert issubclass(r_class, base_int)
    if r_class.SIGNED:
        return r_class(r_class.MASK >> 1)
    else:
        return r_class(r_class.MASK)
most_pos_value_of._annspecialcase_ = 'specialize:memo'

def is_signed_integer_type(tp):
    from rpython.rtyper.lltypesystem import lltype, rffi
    if tp is lltype.Signed:
        return True
    try:
        r_class = rffi.platform.numbertype_to_rclass[tp]
        return r_class.SIGNED
    except KeyError:
        return False   # not an integer type
is_signed_integer_type._annspecialcase_ = 'specialize:memo'

def highest_bit(n):
    """
    Calculates the highest set bit in n.  This function assumes that n is a
    power of 2 (and thus only has a single set bit).
    """
    assert n and (n & (n - 1)) == 0
    i = -1
    while n:
        i += 1
        n >>= 1
    return i


class base_int(long):
    """ fake unsigned integer implementation """

    def _widen(self, other, value):
        """
        if one argument is int or long, the other type wins.
        otherwise, produce the largest class to hold the result.
        """
        self_type = type(self)
        other_type = type(other)
        try:
            return self.typemap[self_type, other_type](value)
        except KeyError:
            pass
        restype = compute_restype(self_type, other_type)
        self.typemap[self_type, other_type] = restype
        return restype(value)

    def __new__(klass, val):
        if klass is base_int:
            raise TypeError("abstract base!")
        else:
            return super(base_int, klass).__new__(klass, val)

    def __add__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x + y)
    __radd__ = __add__

    def __sub__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x - y)

    def __rsub__(self, other):
        y = long(self)
        x = long(other)
        return self._widen(other, x - y)

    def __mul__(self, other):
        x = long(self)
        if not isinstance(other, (int, long)):
            return x * other
        y = long(other)
        return self._widen(other, x * y)
    __rmul__ = __mul__

    def __div__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x // y)

    __floordiv__ = __div__

    def __rdiv__(self, other):
        y = long(self)
        x = long(other)
        return self._widen(other, x // y)

    __rfloordiv__ = __rdiv__

    def __mod__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x % y)

    def __rmod__(self, other):
        y = long(self)
        x = long(other)
        return self._widen(other, x % y)

    def __divmod__(self, other):
        x = long(self)
        y = long(other)
        res = divmod(x, y)
        return (self.__class__(res[0]), self.__class__(res[1]))

    def __lshift__(self, n):
        x = long(self)
        y = long(n)
        return self.__class__(x << y)

    def __rlshift__(self, n):
        y = long(self)
        x = long(n)
        return self._widen(n, x << y)

    def __rshift__(self, n):
        x = long(self)
        y = long(n)
        return self._widen(n, x >> y)

    def __rrshift__(self, n):
        y = long(self)
        x = long(n)
        return self._widen(n, x >> y)

    def __or__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x | y)
    __ror__ = __or__

    def __and__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x & y)
    __rand__ = __and__

    def __xor__(self, other):
        x = long(self)
        y = long(other)
        return self._widen(other, x ^ y)
    __rxor__ = __xor__

    def __neg__(self):
        x = long(self)
        return self.__class__(-x)

    def __abs__(self):
        x = long(self)
        return self.__class__(abs(x))

    def __pos__(self):
        return self.__class__(self)

    def __invert__(self):
        x = long(self)
        return self.__class__(~x)

    def __pow__(self, other, m=None):
        x = long(self)
        y = long(other)
        res = pow(x, y, m)
        return self._widen(other, res)

    def __rpow__(self, other, m=None):
        y = long(self)
        x = long(other)
        res = pow(x, y, m)
        return self._widen(other, res)


class signed_int(base_int):
    SIGNED = True

    def __new__(klass, val=0):
        if isinstance(val, (float, str)):
            val = long(val)
        if val > klass.MASK >> 1 or val < -(klass.MASK >> 1) - 1:
            raise OverflowError("%s does not fit in signed %d-bit integer" % (val, klass.BITS))
        if val < 0:
            val = ~ ((~val) & klass.MASK)
        return super(signed_int, klass).__new__(klass, val)
    typemap = {}


class unsigned_int(base_int):
    SIGNED = False

    def __new__(klass, val=0):
        if isinstance(val, (float, long, str)):
            val = long(val)
        return super(unsigned_int, klass).__new__(klass, val & klass.MASK)
    typemap = {}

_inttypes = {}

def build_int(name, sign, bits, force_creation=False):
    sign = bool(sign)
    if not force_creation:
        try:
            return _inttypes[sign, bits]
        except KeyError:
            pass
    if sign:
        base_int_type = signed_int
    else:
        base_int_type = unsigned_int
    mask = (2 ** bits) - 1
    if name is None:
        raise TypeError('No predefined %sint%d'%(['u', ''][sign], bits))
    int_type = type(name, (base_int_type,), {'MASK': mask,
                                             'BITS': bits,
                                             'SIGN': sign})
    if not force_creation:
        _inttypes[sign, bits] = int_type
    class ForValuesEntry(extregistry.ExtRegistryEntry):
        _type_ = int_type

        def compute_annotation(self):
            from rpython.annotator import model as annmodel
            return annmodel.SomeInteger(knowntype=int_type)

    class ForTypeEntry(extregistry.ExtRegistryEntry):
        _about_ = int_type

        def compute_result_annotation(self, *args_s, **kwds_s):
            from rpython.annotator import model as annmodel
            return annmodel.SomeInteger(knowntype=int_type)

        def specialize_call(self, hop):
            v_result, = hop.inputargs(hop.r_result.lowleveltype)
            hop.exception_cannot_occur()
            return v_result

    return int_type

class BaseIntValueEntry(extregistry.ExtRegistryEntry):
    _type_ = base_int

    def compute_annotation(self):
        from rpython.annotator import model as annmodel
        return annmodel.SomeInteger(knowntype=r_ulonglong)

class BaseIntTypeEntry(extregistry.ExtRegistryEntry):
    _about_ = base_int

    def compute_result_annotation(self, *args_s, **kwds_s):
        raise TypeError("abstract base!")

r_int = build_int('r_int', True, LONG_BIT)
r_uint = build_int('r_uint', False, LONG_BIT)

@register_flow_sc(r_uint)
def sc_r_uint(ctx, w_value):
    # (normally, the 32-bit constant is a long, and is not allowed to
    # show up in the flow graphs at all)
    if isinstance(w_value, Constant):
        return Constant(r_uint(w_value.value))
    return ctx.appcall(r_uint, w_value)


r_longlong = build_int('r_longlong', True, 64)
r_ulonglong = build_int('r_ulonglong', False, 64)

r_longlonglong = build_int('r_longlonglong', True, 128)
longlongmax = r_longlong(LONGLONG_TEST - 1)

if r_longlong is not r_int:
    r_int64 = r_longlong
else:
    r_int64 = int

# needed for ll_os_stat.time_t_to_FILE_TIME in the 64 bit case
r_uint32 = build_int('r_uint32', False, 32)

SHRT_MIN = -2**(_get_bitsize('h') - 1)
SHRT_MAX = 2**(_get_bitsize('h') - 1) - 1
INT_MIN = int(-2**(_get_bitsize('i') - 1))
INT_MAX = int(2**(_get_bitsize('i') - 1) - 1)
UINT_MAX = r_uint(2**_get_bitsize('i') - 1)

# the 'float' C type

class r_singlefloat(object):
    """A value of the C type 'float'.

    This is a single-precision floating-point number.
    Regular 'float' values in Python and RPython are double-precision.
    Note that we consider this as a black box for now - the only thing
    you can do with it is cast it back to a regular float."""

    def __init__(self, floatval):
        import struct
        # simulates the loss of precision
        self._bytes = struct.pack("f", floatval)

    def __float__(self):
        import struct
        return struct.unpack("f", self._bytes)[0]

    def __nonzero__(self):
        raise TypeError("not supported on r_singlefloat instances")

    def __cmp__(self, other):
        raise TypeError("not supported on r_singlefloat instances")

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._bytes == other._bytes

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'r_singlefloat(%s)' % (float(self),)

class r_longfloat(object):
    """A value of the C type 'long double'.

    Note that we consider this as a black box for now - the only thing
    you can do with it is cast it back to a regular float."""

    def __init__(self, floatval):
        self.value = floatval

    def __float__(self):
        return self.value

    def __nonzero__(self):
        raise TypeError("not supported on r_longfloat instances")

    def __cmp__(self, other):
        raise TypeError("not supported on r_longfloat instances")

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)


class For_r_singlefloat_values_Entry(extregistry.ExtRegistryEntry):
    _type_ = r_singlefloat

    def compute_annotation(self):
        from rpython.annotator import model as annmodel
        return annmodel.SomeSingleFloat()

class For_r_singlefloat_type_Entry(extregistry.ExtRegistryEntry):
    _about_ = r_singlefloat

    def compute_result_annotation(self, *args_s, **kwds_s):
        from rpython.annotator import model as annmodel
        return annmodel.SomeSingleFloat()

    def specialize_call(self, hop):
        from rpython.rtyper.lltypesystem import lltype
        v, = hop.inputargs(lltype.Float)
        hop.exception_cannot_occur()
        # we use cast_primitive to go between Float and SingleFloat.
        return hop.genop('cast_primitive', [v],
                         resulttype = lltype.SingleFloat)


def int_between(n, m, p):
    """ check that n <= m < p. This assumes that n <= p. This is useful because
    the JIT special-cases it. """
    from rpython.rtyper.lltypesystem import lltype
    from rpython.rtyper.lltypesystem.lloperation import llop
    if not objectmodel.we_are_translated():
        assert n <= p
    return llop.int_between(lltype.Bool, n, m, p)

@objectmodel.specialize.ll()
def byteswap(arg):
    """ Convert little->big endian and the opposite
    """
    from rpython.rtyper.lltypesystem import lltype, rffi
    from rpython.rlib.longlong2float import longlong2float, float2longlong,\
         uint2singlefloat, singlefloat2uint

    T = lltype.typeOf(arg)
    if T == lltype.SingleFloat:
        arg = singlefloat2uint(arg)
    elif T == lltype.Float:
        arg = float2longlong(arg)
    elif T == lltype.LongFloat:
        assert False
    else:
        # we cannot do arithmetics on small ints
        arg = widen(arg)

    if rffi.sizeof(T) == 1:
        res = arg
    elif rffi.sizeof(T) == 2:
        a, b = arg & 0xFF, arg & 0xFF00
        res = (a << 8) | (b >> 8)
    elif rffi.sizeof(T) == 4:
        FF = r_uint(0xFF)
        arg = r_uint(arg)
        a, b, c, d = (arg & FF, arg & (FF << 8), arg & (FF << 16),
                      arg & (FF << 24))
        res = (a << 24) | (b << 8) | (c >> 8) | (d >> 24)
    elif rffi.sizeof(T) == 8:
        FF = r_ulonglong(0xFF)
        arg = r_ulonglong(arg)
        a, b, c, d = (arg & FF, arg & (FF << 8), arg & (FF << 16),
                      arg & (FF << 24))
        e, f, g, h = (arg & (FF << 32), arg & (FF << 40), arg & (FF << 48),
                      arg & (FF << 56))
        res = ((a << 56) | (b << 40) | (c << 24) | (d << 8) | (e >> 8) |
               (f >> 24) | (g >> 40) | (h >> 56))
    else:
        assert False # unreachable code

    if T == lltype.SingleFloat:
        return uint2singlefloat(rffi.cast(rffi.UINT, res))
    if T == lltype.Float:
        return longlong2float(rffi.cast(rffi.LONGLONG, res))
    return rffi.cast(T, res)


# String parsing support
# ---------------------------

def string_to_int(s, base=10):
    """Utility to converts a string to an integer.
    If base is 0, the proper base is guessed based on the leading
    characters of 's'.  Raises ParseStringError in case of error.
    Raises ParseStringOverflowError in case the result does not fit.
    """
    from rpython.rlib.rstring import (
        NumberStringParser, ParseStringOverflowError, strip_spaces)
    s = literal = strip_spaces(s)
    p = NumberStringParser(s, literal, base, 'int')
    base = p.base
    result = 0
    while True:
        digit = p.next_digit()
        if digit == -1:
            return result

        if p.sign == -1:
            digit = -digit

        try:
            result = ovfcheck(result * base)
            result = ovfcheck(result + digit)
        except OverflowError:
            raise ParseStringOverflowError(p)
string_to_int._elidable_function_ = True
