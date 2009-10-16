from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.strutil import string_to_w_long, ParseStringError
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped

def descr__new__(space, w_longtype, w_x=0, w_base=NoneNotWrapped):
    from pypy.objspace.std.longobject import W_LongObject
    w_value = w_x     # 'x' is the keyword argument name in CPython
    if w_base is None:
        # check for easy cases
        if type(w_value) is W_LongObject:
            pass
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            try:
                w_value = string_to_w_long(space, space.str_w(w_value))
            except ParseStringError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.msg))
        elif space.is_true(space.isinstance(w_value, space.w_unicode)):
            try:
                if space.config.objspace.std.withropeunicode:
                    from pypy.objspace.std.ropeunicodeobject import unicode_to_decimal_w
                else:
                    from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
                w_value = string_to_w_long(space, unicode_to_decimal_w(space, w_value))
            except ParseStringError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.msg))
        else:
            # otherwise, use the __long__() method
            w_obj = space.long(w_value)
            # 'long(x)' should return whatever x.__long__() returned
            if space.is_w(w_longtype, space.w_long):
                return w_obj
            if space.is_true(space.isinstance(w_obj, space.w_long)):
                assert isinstance(w_obj, W_LongObject)  # XXX this could fail!
                # XXX find a way to do that even if w_obj is not a W_LongObject
                w_value = w_obj
            elif space.is_true(space.isinstance(w_obj, space.w_int)):
                intval = space.int_w(w_obj)
                w_value = W_LongObject.fromint(space, intval)
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
            w_value = string_to_w_long(space, s, base)
        except ParseStringError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.msg))

    w_obj = space.allocate_instance(W_LongObject, w_longtype)
    W_LongObject.__init__(w_obj, w_value.num)
    return w_obj

# ____________________________________________________________

long_typedef = StdTypeDef("long",
    __doc__ = '''long(x[, base]) -> integer

Convert a string or number to a long integer, if possible.  A floating
point argument will be truncated towards zero (this does not include a
string representation of a floating point number!)  When converting a
string, use the optional base.  It is an error to supply a base when
converting a non-string.''',
    __new__ = newmethod(descr__new__),
    )
