from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.basestringtype import basestring_typedef

from sys import maxint

str_join    = MultiMethod('join', 2)
str_split   = MultiMethod('split', 3, defaults=(None,-1))
str_isdigit    = MultiMethod('isdigit', 1)
str_isalpha    = MultiMethod('isalpha', 1)
str_isspace    = MultiMethod('isspace', 1)
str_isupper    = MultiMethod('isupper', 1)
str_islower    = MultiMethod('islower', 1)
str_istitle    = MultiMethod('istitle', 1)
str_isalnum    = MultiMethod('isalnum', 1)
str_ljust      = MultiMethod('ljust', 3, defaults=(' ',))
str_rjust      = MultiMethod('rjust', 3, defaults=(' ',))
str_upper      = MultiMethod('upper', 1)
str_lower      = MultiMethod('lower', 1)
str_swapcase   = MultiMethod('swapcase', 1)
str_capitalize = MultiMethod('capitalize', 1)
str_title      = MultiMethod('title', 1)
str_find       = MultiMethod('find', 4, defaults=(0, maxint))
str_rfind      = MultiMethod('rfind', 4, defaults=(0, maxint))
str_index      = MultiMethod('index', 4, defaults=(0, maxint))
str_rindex     = MultiMethod('rindex', 4, defaults=(0, maxint))
str_replace    = MultiMethod('replace', 4, defaults=(-1,))
str_zfill      = MultiMethod('zfill', 2)
str_strip      = MultiMethod('strip',  2, defaults=(None,))
str_rstrip     = MultiMethod('rstrip', 2, defaults=(None,))
str_lstrip     = MultiMethod('lstrip', 2, defaults=(None,))
str_center     = MultiMethod('center', 3, defaults=(' ',))
str_count      = MultiMethod('count', 4, defaults=(0, maxint))      
str_endswith   = MultiMethod('endswith', 4, defaults=(0, maxint))
str_expandtabs = MultiMethod('expandtabs', 2, defaults=(8,))
str_splitlines = MultiMethod('splitlines', 2, defaults=(0,))
str_startswith = MultiMethod('startswith', 4, defaults=(0, maxint))
str_translate  = MultiMethod('translate', 3, defaults=('',)) #unicode mimic not supported now
str_decode     = MultiMethod('decode', 3, defaults=(None, None))
str_encode     = MultiMethod('encode', 3, defaults=(None, None))

# ____________________________________________________________

def descr__new__(space, w_stringtype, w_object=''):
    from pypy.objspace.std.stringobject import W_StringObject
    w_obj = space.str(w_object)
    if space.is_true(space.is_(w_stringtype, space.w_str)):
        return w_obj  # XXX might be reworked when space.str() typechecks
    value = space.str_w(w_obj)
    w_obj = space.allocate_instance(W_StringObject, w_stringtype)
    W_StringObject.__init__(w_obj, space, value)
    return w_obj

# ____________________________________________________________

str_typedef = StdTypeDef("str", basestring_typedef,
    __new__ = newmethod(descr__new__),
    )
str_typedef.registermethods(globals())
