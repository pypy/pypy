from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.strutil import string_to_int, string_to_w_long, ParseStringError, ParseStringOverflowError
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.objectmodel import instantiate

# ____________________________________________________________


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
                value = string_to_int(space.str_w(w_value))
            except ParseStringError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.msg))
            except ParseStringOverflowError, e:
                 w_longval = retry_to_w_long(space, e.parser)                
        elif space.is_true(space.isinstance(w_value, space.w_unicode)):
            if space.config.objspace.std.withropeunicode:
                from pypy.objspace.std.ropeunicodeobject import unicode_to_decimal_w
            else:
                from pypy.objspace.std.unicodeobject import unicode_to_decimal_w
            string = unicode_to_decimal_w(space, w_value)
            try:
                value = string_to_int(string)
            except ParseStringError, e:
                raise OperationError(space.w_ValueError,
                                     space.wrap(e.msg))
            except ParseStringOverflowError, e:
                 w_longval = retry_to_w_long(space, e.parser)                
        else:
            # otherwise, use the __int__() method
            w_obj = space.int(w_value)
            # 'int(x)' should return whatever x.__int__() returned
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
        try:
            value = string_to_int(s, base)
        except ParseStringError, e:
            raise OperationError(space.w_ValueError,
                                 space.wrap(e.msg))
        except ParseStringOverflowError, e:
            w_longval = retry_to_w_long(space, e.parser, base)                        

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

# ____________________________________________________________

int_typedef = StdTypeDef("int",
    __doc__ = '''int(x[, base]) -> integer

Convert a string or number to an integer, if possible.  A floating point
argument will be truncated towards zero (this does not include a string
representation of a floating point number!)  When converting a string, use
the optional base.  It is an error to supply a base when converting a
non-string. If the argument is outside the integer range a long object
will be returned instead.''',
    __new__ = newmethod(descr__new__),
    )
int_typedef.custom_hash = True
