from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.objspace.std.strutil import string_to_bigint, ParseStringError

def descr__new__(space, w_longtype, w_x=0, w_base=gateway.NoneNotWrapped):
    from pypy.objspace.std.longobject import W_LongObject, newbigint
    from pypy.rlib.rbigint import rbigint
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
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            return string_to_w_long(space, w_longtype, space.str_w(w_value))
        elif space.is_true(space.isinstance(w_value, space.w_unicode)):
            if space.config.objspace.std.withropeunicode:
                from pypy.objspace.std.ropeunicodeobject import unicode_to_decimal_w
            else:
                from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            return string_to_w_long(space, w_longtype,
                                    unicode_to_decimal_w(space, w_value))
        else:
            # otherwise, use the __long__() method
            w_obj = space.long(w_value)
            # 'long(x)' should return whatever x.__long__() returned
            if space.is_w(w_longtype, space.w_long):
                return w_obj
            # the following is all for the 'subclass_of_long(x)' case
            if W_SmallLongObject and isinstance(w_obj, W_SmallLongObject):
                bigint = w_obj.as_bigint()
            elif isinstance(w_obj, W_LongObject):
                bigint = w_obj.num
            elif space.is_true(space.isinstance(w_obj, space.w_int)):
                from pypy.rlib.rbigint import rbigint
                bigint = rbigint.fromint(space.int_w(w_obj))
            else:
                raise OperationError(space.w_ValueError,
                                space.wrap("value can't be converted to long"))
            return newbigint(space, w_longtype, bigint)
    #
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
        return string_to_w_long(space, w_longtype, s, base)


def string_to_w_long(space, w_longtype, s, base=10):
    try:
        bigint = string_to_bigint(s, base)
    except ParseStringError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.msg))
    if (space.config.objspace.std.withsmalllong
        and space.is_w(w_longtype, space.w_long)):
        try:
            longlong = bigint.tolonglong()
        except OverflowError:
            pass
        else:
            from pypy.objspace.std.smalllongobject import W_SmallLongObject
            return W_SmallLongObject(longlong)
    return newbigint(space, w_longtype, bigint)

# ____________________________________________________________

long_typedef = StdTypeDef("long",
    __doc__ = '''long(x[, base]) -> integer

Convert a string or number to a long integer, if possible.  A floating
point argument will be truncated towards zero (this does not include a
string representation of a floating point number!)  When converting a
string, use the optional base.  It is an error to supply a base when
converting a non-string.''',
    __new__ = gateway.interp2app(descr__new__),
    )
