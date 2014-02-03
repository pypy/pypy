from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter import typedef
from pypy.interpreter.gateway import (
    WrappedDefault, applevel, interp2app, interpindirect2app, unwrap_spec)
from pypy.interpreter.buffer import Buffer
from pypy.objspace.std.model import W_Object
from pypy.objspace.std.stdtypedef import StdTypeDef
from rpython.rlib.rstring import ParseStringError
from rpython.rlib.rbigint import rbigint, InvalidEndiannessError, InvalidSignednessError

def descr_conjugate(space, w_int):
    return space.int(w_int)


@unwrap_spec(w_x = WrappedDefault(0))
def descr__new__(space, w_longtype, w_x, w_base=None):
    from pypy.objspace.std.longobject import W_LongObject
    if space.config.objspace.std.withsmalllong:
        from pypy.objspace.std.smalllongobject import W_SmallLongObject
    else:
        W_SmallLongObject = None

    w_value = w_x     # 'x' is the keyword argument name in CPython
    if w_base is None:
        # check for easy cases
        if (W_SmallLongObject and type(w_value) is W_SmallLongObject
            and space.is_w(w_longtype, space.w_int)):
            return w_value
        elif type(w_value) is W_LongObject:
            return newbigint(space, w_longtype, w_value.num)
        elif space.lookup(w_value, '__int__') is not None:
            return _from_intlike(space, w_longtype, w_value)
        elif space.lookup(w_value, '__trunc__') is not None:
            w_obj = space.trunc(w_value)
            return _from_intlike(space, w_longtype, w_obj)
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            return string_to_w_long(space, w_longtype, w_value,
                                    unicode_to_decimal_w(space, w_value))
        elif (space.isinstance_w(w_value, space.w_bytearray) or
              space.isinstance_w(w_value, space.w_bytes)):
            return string_to_w_long(space, w_longtype, w_value,
                                    space.bufferstr_w(w_value))
        else:
            try:
                w_buffer = space.buffer(w_value)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise oefmt(space.w_TypeError,
                            "int() argument must be a string or a number, not "
                            "'%T'", w_value)
            else:
                buf = space.interp_w(Buffer, w_buffer)
                return string_to_w_long(space, w_longtype, w_value,
                                        buf.as_str())
    else:
        try:
            base = space.int_w(w_base)
        except OperationError, e:
            if not e.match(space, space.w_OverflowError):
                raise
            base = 37 # this raises the right error in string_to_bigint()

        if space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.bufferstr_w(w_value)
            except OperationError:
                raise OperationError(space.w_TypeError,
                                     space.wrap("int() can't convert non-string "
                                                "with explicit base"))
        return string_to_w_long(space, w_longtype, w_value, s, base)


def _from_intlike(space, w_longtype, w_intlike):
    w_obj = space.int(w_intlike)
    if space.is_w(w_longtype, space.w_int):
        return w_obj
    return newbigint(space, w_longtype, space.bigint_w(w_obj))


def string_to_w_long(space, w_longtype, w_source, string, base=10):
    try:
        bigint = rbigint.fromstr(string, base, ignore_l_suffix=True,
                                 fname='int')
    except ParseStringError as e:
        from pypy.objspace.std.inttype import wrap_parsestringerror
        raise wrap_parsestringerror(space, e, w_source)
    return newbigint(space, w_longtype, bigint)
string_to_w_long._dont_inline_ = True

def newbigint(space, w_longtype, bigint):
    """Turn the bigint into a W_LongObject.  If withsmalllong is enabled,
    check if the bigint would fit in a smalllong, and return a
    W_SmallLongObject instead if it does.  Similar to newlong() in
    longobject.py, but takes an explicit w_longtype argument.
    """
    if (space.config.objspace.std.withsmalllong
        and space.is_w(w_longtype, space.w_int)):
        try:
            z = bigint.tolonglong()
        except OverflowError:
            pass
        else:
            from pypy.objspace.std.smalllongobject import W_SmallLongObject
            return W_SmallLongObject(z)
    from pypy.objspace.std.longobject import W_LongObject
    w_obj = space.allocate_instance(W_LongObject, w_longtype)
    W_LongObject.__init__(w_obj, bigint)
    return w_obj

def descr_get_numerator(space, w_obj):
    return space.int(w_obj)

def descr_get_denominator(space, w_obj):
    return space.newlong(1)

def descr_get_real(space, w_obj):
    return space.int(w_obj)

def descr_get_imag(space, w_obj):
    return space.newlong(0)

def bit_length(space, w_obj):
    bigint = space.bigint_w(w_obj)
    try:
        return space.wrap(bigint.bit_length())
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("too many digits in integer"))

@unwrap_spec(byteorder=str, signed=bool)
def descr_from_bytes(space, w_cls, w_obj, byteorder, signed=False):
    from pypy.objspace.std.bytesobject import makebytesdata_w
    bytes = ''.join(makebytesdata_w(space, w_obj))
    try:
        bigint = rbigint.frombytes(bytes, byteorder=byteorder, signed=signed)
    except InvalidEndiannessError:
        raise OperationError(
            space.w_ValueError,
            space.wrap("byteorder must be either 'little' or 'big'"))
    return newbigint(space, w_cls, bigint)

@unwrap_spec(nbytes=int, byteorder=str, signed=bool)
def descr_to_bytes(space, w_obj, nbytes, byteorder, signed=False):
    try:
        byte_string = space.bigint_w(w_obj).tobytes(nbytes, byteorder=byteorder, signed=signed)
    except InvalidEndiannessError:
        raise OperationError(
            space.w_ValueError,
            space.wrap("byteorder must be either 'little' or 'big'"))
    except InvalidSignednessError:
        raise OperationError(
            space.w_OverflowError,
            space.wrap("can't convert negative int to unsigned"))
    except OverflowError:
        raise OperationError(
            space.w_OverflowError,
            space.wrap('int too big to convert'))
    return space.wrapbytes(byte_string)

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

def descr___round__(space, w_long, w_ndigits=None):
    """To round an integer m to the nearest 10**n (n positive), we make
    use of the divmod_near operation, defined by:

    divmod_near(a, b) = (q, r)

    where q is the nearest integer to the quotient a / b (the
    nearest even integer in the case of a tie) and r == a - q * b.
    Hence q * b = a - r is the nearest multiple of b to a,
    preferring even multiples in the case of a tie.

    So the nearest multiple of 10**n to m is:

    m - divmod_near(m, 10**n)[1]

    """
    from pypy.objspace.std.longobject import newlong
    assert isinstance(w_long, W_AbstractLongObject)

    if w_ndigits is None:
        return space.int(w_long)

    ndigits = space.bigint_w(space.index(w_ndigits))
    # if ndigits >= 0 then no rounding is necessary; return self unchanged
    if ndigits.ge(rbigint.fromint(0)):
        return space.int(w_long)

    # result = self - divmod_near(self, 10 ** -ndigits)[1]
    right = rbigint.fromint(10).pow(ndigits.neg())
    w_tuple = divmod_near(space, w_long, newlong(space, right))
    _, w_r = space.fixedview(w_tuple, 2)
    return space.sub(w_long, w_r)

# ____________________________________________________________

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
        from pypy.objspace.std.model import IDTAG_INT as tag
        b = space.bigint_w(self)
        b = b.lshift(3).or_(rbigint.fromint(tag))
        return space.newlong_from_rbigint(b)

    def unwrap(w_self, space): #YYYYYY
        return w_self.longval()

    def int(self, space):
        raise NotImplementedError

long_typedef = StdTypeDef("int",
    __doc__ = '''int(x[, base]) -> integer

Convert a string or number to a long integer, if possible.  A floating
point argument will be truncated towards zero (this does not include a
string representation of a floating point number!)  When converting a
string, use the optional base.  It is an error to supply a base when
converting a non-string.''',
    __new__ = interp2app(descr__new__),
    __round__ = interp2app(descr___round__),
    conjugate = interp2app(descr_conjugate),
    numerator = typedef.GetSetProperty(descr_get_numerator),
    denominator = typedef.GetSetProperty(descr_get_denominator),
    real = typedef.GetSetProperty(descr_get_real),
    imag = typedef.GetSetProperty(descr_get_imag),
    bit_length = interp2app(bit_length),
    from_bytes = interp2app(descr_from_bytes, as_classmethod=True),
    to_bytes = interp2app(descr_to_bytes),
    __int__ = interpindirect2app(W_AbstractLongObject.int),
)
long_typedef.registermethods(globals())
