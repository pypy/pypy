from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.strutil import string_to_int, string_to_w_long, ParseStringError, ParseStringOverflowError
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped

def retry_to_w_long(space, parser, base=0):
    parser.rewind()
    try:
        return string_to_w_long(space, None, base=base, parser=parser)
    except ParseStringError, e:
        raise OperationError(space.w_ValueError,
                             space.wrap(e.msg))
    
def descr__new__(space, w_inttype, w_x=0, w_base=NoneNotWrapped):
    from pypy.objspace.std.intobject import W_IntObject
    w_longval = None
    w_value = w_x     # 'x' is the keyword argument name in CPython
    value = 0
    if w_base is None:
        # check for easy cases
        if isinstance(w_value, W_IntObject):
            value = w_value.intval
        elif space.is_true(space.isinstance(w_value, space.w_str)):
            try:
                value = string_to_int(space, space.str_w(w_value))
            except ParseStringError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.msg))
            except ParseStringOverflowError, e:
                 w_longval = retry_to_w_long(space, e.parser)                
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
            value = string_to_int(space, s, base)
        except ParseStringError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.msg))
        except ParseStringOverflowError, e:
            w_longval = retry_to_w_long(space, e.parser, base)                        

    if w_longval is not None:
        if not space.is_true(space.is_(w_inttype, space.w_int)):
            raise OperationError(space.w_OverflowError,
                                 space.wrap(
                "long int too large to convert to int"))          
        return w_longval
    else:
        w_obj = space.allocate_instance(W_IntObject, w_inttype)
        W_IntObject.__init__(w_obj, space, value)
        return w_obj

# ____________________________________________________________

int_typedef = StdTypeDef("int",
    __new__ = newmethod(descr__new__),
    )
