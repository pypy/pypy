from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway, typedef
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.strutil import string_to_bigint, ParseStringError

long_conjugate = SMM("conjugate", 1, doc="Returns self, the complex conjugate of any long.")

def long_conjugate__ANY(space, w_int):
    return space.pos(w_int)

register_all(vars(), globals())


def descr__new__(space, w_longtype, w_x=0, w_base=gateway.NoneNotWrapped):
    from pypy.objspace.std.longobject import W_LongObject
    w_value = w_x     # 'x' is the keyword argument name in CPython
    if w_base is None:
        # check for easy cases
        if type(w_value) is W_LongObject:
            bigint = w_value.num
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            try:
                bigint = string_to_bigint(space.str_w(w_value))
            except ParseStringError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.msg))
        elif space.is_true(space.isinstance(w_value, space.w_unicode)):
            try:
                if space.config.objspace.std.withropeunicode:
                    from pypy.objspace.std.ropeunicodeobject import unicode_to_decimal_w
                else:
                    from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
                bigint = string_to_bigint(unicode_to_decimal_w(space, w_value))
            except ParseStringError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.msg))
        else:
            # otherwise, use the __long__() or the __trunc__ methods
            w_obj = w_value
            if (space.lookup(w_obj, '__long__') is not None or
                space.lookup(w_obj, '__int__') is not None):
                w_obj = space.long(w_obj)
            else:
                w_obj = space.trunc(w_obj)
                # :-(  blame CPython 2.7
                if space.lookup(w_obj, '__long__') is not None:
                    w_obj = space.long(w_obj)
                else:
                    w_obj = space.int(w_obj)
            # 'long(x)' should return whatever x.__long__() returned
            if space.is_w(w_longtype, space.w_long):
                return w_obj
            if space.is_true(space.isinstance(w_obj, space.w_long)):
                assert isinstance(w_obj, W_LongObject)  # XXX this could fail!
                # XXX find a way to do that even if w_obj is not a W_LongObject
                bigint = w_obj.num
            elif space.is_true(space.isinstance(w_obj, space.w_int)):
                from pypy.rlib.rbigint import rbigint
                intval = space.int_w(w_obj)
                bigint = rbigint.fromint(intval)
            else:
                raise OperationError(space.w_ValueError,
                                    space.wrap("value can't be converted to long"))
    else:
        base = space.int_w(w_base)

        if space.is_true(space.isinstance(w_value, space.w_unicode)):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError, e:
                raise OperationError(space.w_TypeError,
                                     space.wrap("long() can't convert non-string "
                                                "with explicit base"))
        try:
            bigint = string_to_bigint(s, base)
        except ParseStringError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.msg))

    w_obj = space.allocate_instance(W_LongObject, w_longtype)
    W_LongObject.__init__(w_obj, bigint)
    return w_obj

def descr_get_numerator(space, w_obj):
    return space.long(w_obj)

def descr_get_denominator(space, w_obj):
    return space.newlong(1)

def descr_get_real(space, w_obj):
    return w_obj

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

long_typedef = StdTypeDef("long",
    __doc__ = '''long(x[, base]) -> integer

Convert a string or number to a long integer, if possible.  A floating
point argument will be truncated towards zero (this does not include a
string representation of a floating point number!)  When converting a
string, use the optional base.  It is an error to supply a base when
converting a non-string.''',
    __new__ = gateway.interp2app(descr__new__),
    numerator = typedef.GetSetProperty(descr_get_numerator),
    denominator = typedef.GetSetProperty(descr_get_denominator),
    real = typedef.GetSetProperty(descr_get_real),
    imag = typedef.GetSetProperty(descr_get_imag),
    bit_length = gateway.interp2app(bit_length),
)
long_typedef.registermethods(globals())
