from pypy.objspace.std.objspace import MultiMethod, StdObjSpace, W_ANY, register_all
from typeobject import W_TypeObject


class W_StringType(W_TypeObject):

    typename = 'str'

    str_join    = MultiMethod('join', 2)
    str_split   = MultiMethod('split', 3, defaults=(None,-1))

    str_isdigit    = MultiMethod('isdigit', 1)
    str_isalpha    = MultiMethod('isalpha', 1)
    str_isspace    = MultiMethod('isspace', 1)
    str_isupper    = MultiMethod('isupper', 1)
    str_islower    = MultiMethod('islower', 1)
    str_istitle    = MultiMethod('istitle', 1)
    str_isalnum    = MultiMethod('isalnum', 1)
    str_ljust      = MultiMethod('ljust', 2)
    str_rjust      = MultiMethod('rjust', 2)
    str_upper      = MultiMethod('upper', 1)
    str_lower      = MultiMethod('lower', 1)
    str_capitalize = MultiMethod('capitalize', 1)
    str_title      = MultiMethod('title', 1)
    #XXX we need to have the possibility to specify, if the a parameter
    #was given
    str_find       = MultiMethod('find', 4, defaults=(None, None))
    str_rfind      = MultiMethod('rfind', 4, defaults=(None, None))
    str_index      = MultiMethod('index', 4, defaults=(None, None))
    str_rindex     = MultiMethod('rindex', 4, defaults=(None, None))

    str_strip      = MultiMethod('strip', 1)
    str_rstrip     = MultiMethod('rstrip', 1)
    str_lstrip     = MultiMethod('lstrip', 1)
    str_center     = MultiMethod('center', 2)
    str_count      = MultiMethod('count', 2)      #[optional arguments not supported now]
    str_endswith   = MultiMethod('endswith', 2)   #[optional arguments not supported now]
    str_expandtabs = MultiMethod('expandtabs', 2, defaults=(8,))


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
