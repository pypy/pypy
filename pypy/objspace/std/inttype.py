from pypy.interpreter import typedef
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault,\
     interpindirect2app
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.buffer import Buffer
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.model import W_Object
from rpython.rlib.rarithmetic import r_uint, string_to_int
from rpython.rlib.objectmodel import instantiate
from rpython.rlib.rbigint import rbigint
from rpython.rlib.rstring import (
    InvalidBaseError, ParseStringError, ParseStringOverflowError)
from rpython.rlib import jit

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
def string_to_int_or_long(space, w_source, string, base=10):
    w_longval = None
    value = 0
    try:
        value = string_to_int(string, base)
    except ParseStringError as e:
        raise wrap_parsestringerror(space, e, w_source)
    except ParseStringOverflowError, e:
        w_longval = retry_to_w_long(space, e.parser, w_source)
    return value, w_longval

def retry_to_w_long(space, parser, w_source):
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

@unwrap_spec(w_x = WrappedDefault(0))
def descr__new__(space, w_inttype, w_x, w_base=None):
    from pypy.objspace.std.intobject import W_IntObject
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
            value, w_longval = string_to_int_or_long(space, w_value,
                                                     space.str_w(w_value))
        elif space.isinstance_w(w_value, space.w_unicode):
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            string = unicode_to_decimal_w(space, w_value)
            value, w_longval = string_to_int_or_long(space, w_value, string)
        else:
            # If object supports the buffer interface
            try:
                w_buffer = space.buffer(w_value)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise operationerrfmt(space.w_TypeError,
                    "int() argument must be a string or a number, not '%T'",
                    w_value)
            else:
                buf = space.interp_w(Buffer, w_buffer)
                value, w_longval = string_to_int_or_long(space, w_value,
                                                         buf.as_str())
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

        value, w_longval = string_to_int_or_long(space, w_value, s, base)

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

class W_AbstractIntObject(W_Object):
    __slots__ = ()

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

    def int(self, space):
        raise NotImplementedError

int_typedef = StdTypeDef("int",
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
)
int_typedef.registermethods(globals())
