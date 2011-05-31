from pypy.interpreter import gateway, typedef
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.buffer import Buffer
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.strutil import (string_to_int, string_to_bigint,
                                       ParseStringError,
                                       ParseStringOverflowError)
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.objectmodel import instantiate

# ____________________________________________________________

def descr_conjugate(space, w_int):
    return space.pos(w_int)

def descr_bit_length(space, w_int):
    val = space.int_w(w_int)
    if val < 0:
        val = -val
    bits = 0
    while val:
        bits += 1
        val >>= 1
    return space.wrap(bits)


def wrapint(space, x):
    if space.config.objspace.std.withsmallint:
        from pypy.objspace.std.smallintobject import W_SmallIntObject
        try:
            return W_SmallIntObject(x)
        except OverflowError:
            from pypy.objspace.std.intobject import W_IntObject
            return W_IntObject(x)
    elif space.config.objspace.std.withprebuiltint:
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

def retry_to_w_long(space, parser, base=0):
    parser.rewind()
    try:
        bigint = string_to_bigint(None, base=base, parser=parser)
    except ParseStringError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.msg))
    from pypy.objspace.std.longobject import newlong
    return newlong(space, bigint)

def descr__new__(space, w_inttype, w_x=0, w_base=gateway.NoneNotWrapped):
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
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            value, w_longval = string_to_int_or_long(space, space.str_w(w_value))
            ok = True
        elif space.is_true(space.isinstance(w_value, space.w_unicode)):
            if space.config.objspace.std.withropeunicode:
                from pypy.objspace.std.ropeunicodeobject import unicode_to_decimal_w
            else:
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
                if e.match(space,space.w_TypeError):
                    raise OperationError(space.w_ValueError,
                        space.wrap("value can't be converted to int"))
                raise e
    else:
        base = space.int_w(w_base)

        if space.is_true(space.isinstance(w_value, space.w_unicode)):
            if space.config.objspace.std.withropeunicode:
                from pypy.objspace.std.ropeunicodeobject import unicode_to_decimal_w
            else:
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

int_typedef = StdTypeDef("int",
    __doc__ = '''int(x[, base]) -> integer

Convert a string or number to an integer, if possible.  A floating point
argument will be truncated towards zero (this does not include a string
representation of a floating point number!)  When converting a string, use
the optional base.  It is an error to supply a base when converting a
non-string. If the argument is outside the integer range a long object
will be returned instead.''',
    __new__ = gateway.interp2app(descr__new__),
    conjugate = gateway.interp2app(descr_conjugate),
    bit_length = gateway.interp2app(descr_bit_length),
    numerator = typedef.GetSetProperty(descr_get_numerator),
    denominator = typedef.GetSetProperty(descr_get_denominator),
    real = typedef.GetSetProperty(descr_get_real),
    imag = typedef.GetSetProperty(descr_get_imag),
)
int_typedef.registermethods(globals())
