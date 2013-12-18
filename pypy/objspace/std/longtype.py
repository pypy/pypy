from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter import typedef
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault,\
     interpindirect2app
from pypy.interpreter.buffer import Buffer
from pypy.objspace.std.model import W_Object
from pypy.objspace.std.stdtypedef import StdTypeDef
from rpython.rlib.rstring import ParseStringError
from rpython.rlib.rbigint import rbigint

def descr_conjugate(space, w_int):
    return space.long(w_int)


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
            return string_to_w_long(space, w_longtype, space.str_w(w_value))
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            return string_to_w_long(space, w_longtype,
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
                return string_to_w_long(space, w_longtype, buf.as_str())
    else:
        base = space.int_w(w_base)

        if space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError:
                raise OperationError(space.w_TypeError,
                                     space.wrap("long() can't convert non-string "
                                                "with explicit base"))
        return string_to_w_long(space, w_longtype, s, base)


def string_to_w_long(space, w_longtype, s, base=10):
    try:
        bigint = rbigint.fromstr(s, base)
    except ParseStringError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.msg))
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
    from pypy.objspace.std.longobject import W_LongObject
    w_obj = space.allocate_instance(W_LongObject, w_longtype)
    W_LongObject.__init__(w_obj, bigint)
    return w_obj

def descr_get_numerator(space, w_obj):
    return space.long(w_obj)

def descr_get_denominator(space, w_obj):
    return space.newlong(1)

def descr_get_real(space, w_obj):
    return space.long(w_obj)

def descr_get_imag(space, w_obj):
    return space.newlong(0)

def bit_length(space, w_obj):
    bigint = space.bigint_w(w_obj)
    try:
        return space.wrap(bigint.bit_length())
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("too many digits in integer"))

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
        from pypy.objspace.std.model import IDTAG_LONG as tag
        b = space.bigint_w(self)
        b = b.lshift(3).or_(rbigint.fromint(tag))
        return space.newlong_from_rbigint(b)

    def unwrap(w_self, space): #YYYYYY
        return w_self.longval()

    def int(self, space):
        raise NotImplementedError

long_typedef = StdTypeDef("long",
    __doc__ = '''long(x[, base]) -> integer

Convert a string or number to a long integer, if possible.  A floating
point argument will be truncated towards zero (this does not include a
string representation of a floating point number!)  When converting a
string, use the optional base.  It is an error to supply a base when
converting a non-string.''',
    __new__ = interp2app(descr__new__),
    conjugate = interp2app(descr_conjugate),
    numerator = typedef.GetSetProperty(descr_get_numerator),
    denominator = typedef.GetSetProperty(descr_get_denominator),
    real = typedef.GetSetProperty(descr_get_real),
    imag = typedef.GetSetProperty(descr_get_imag),
    bit_length = interp2app(bit_length),
    __int__ = interpindirect2app(W_AbstractLongObject.int),
)
long_typedef.registermethods(globals())
