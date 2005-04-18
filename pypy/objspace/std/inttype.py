from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.strutil import string_to_int
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped

def descr__new__(space, w_inttype, w_value=0, w_base=NoneNotWrapped):
    from pypy.objspace.std.intobject import W_IntObject
    if w_base is None:
        # check for easy cases
        if isinstance(w_value, W_IntObject):
            value = w_value.intval
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            try:
                # XXX can produce unwrapped long
                value = string_to_int(space.str_w(w_value))
            except ValueError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.args[0]))
        else:
            # otherwise, use the __int__() method
            w_obj = space.int(w_value)
            # 'int(x)' should return whatever x.__int__() returned
            if space.is_true(space.is_(w_inttype, space.w_int)):
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
            from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            s = unicode_to_decimal_w(space, w_value)
        else:
            try:
                s = space.str_w(w_value)
            except OperationError, e:
                raise OperationError(space.w_TypeError,
                                     space.wrap("int() can't convert non-string "
                                                "with explicit base"))
        try:
            # XXX can produce unwrapped long, need real long impl to know
            # what to do
            value = string_to_int(s, base)
        except ValueError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.args[0]))

    if isinstance(value, long):
        if not space.is_true(space.is_(w_inttype, space.w_int)):
            raise OperationError(space.w_OverflowError,
                                 space.wrap(
                "long int too large to convert to int"))          
        from pypy.objspace.std.longobject import W_LongObject, args_from_long
        w_obj = space.allocate_instance(W_LongObject, space.w_long)
        w_obj.__init__(space, *args_from_long(value))
        return w_obj
    else:
        w_obj = space.allocate_instance(W_IntObject, w_inttype)
        w_obj.__init__(space, value)
        return w_obj

def descr__getnewargs__(space, w_obj):
    from pypy.objspace.std.intobject import W_IntObject
    return space.newtuple([W_IntObject(space, w_obj.intval)])

# ____________________________________________________________

int_typedef = StdTypeDef("int",
    __new__ = newmethod(descr__new__),
    __getnewargs__ = newmethod(descr__getnewargs__),
    )
