from pypy.objspace.std.objspace import MultiMethod, StdObjSpace, W_ANY, register_all
from typeobject import W_TypeObject


class W_StringType(W_TypeObject):

    typename = 'str'

    str_join    = MultiMethod('join', 2)
    str_split   = MultiMethod('split', 2, defaults=(None,))

    str_isdigit = MultiMethod('isdigit', 1)
    str_isalpha = MultiMethod('isalpha', 1)
    str_isspace = MultiMethod('isspace', 1)
    str_isupper = MultiMethod('isupper', 1)
    str_islower = MultiMethod('islower', 1)
    str_istitle = MultiMethod('istitle', 1)
    str_isalnum = MultiMethod('isalnum', 1)
    str_ljust   = MultiMethod('ljust', 2)
    str_rjust   = MultiMethod('rjust', 2)

# XXX we'll worry about the __new__/__init__ distinction later
def new__StringType_ANY_ANY(space, w_stringtype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        return space.newstring([])
    elif len(args) == 1:
        return space.str(args[0])
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("str() takes at most 1 argument"))

register_all(vars())
