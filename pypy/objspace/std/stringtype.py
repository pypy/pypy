from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef

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
str_swapcase   = MultiMethod('swapcase', 1)
str_capitalize = MultiMethod('capitalize', 1)
str_title      = MultiMethod('title', 1)
str_find       = MultiMethod('find', 4, defaults=(None, None))
str_rfind      = MultiMethod('rfind', 4, defaults=(None, None))
str_index      = MultiMethod('index', 4, defaults=(None, None))
str_rindex     = MultiMethod('rindex', 4, defaults=(None, None))
str_replace    = MultiMethod('replace', 4, defaults=(-1,))
str_zfill      = MultiMethod('zfill', 2)
str_strip      = MultiMethod('strip',  2, defaults=('', ' '))
str_rstrip     = MultiMethod('rstrip', 2, defaults=('', ' '))
str_lstrip     = MultiMethod('lstrip', 2, defaults=('', ' '))
str_center     = MultiMethod('center', 2, )
str_count      = MultiMethod('count', 4, defaults=(None,None))      
str_endswith   = MultiMethod('endswith', 2)   #[optional arguments not supported now]
str_expandtabs = MultiMethod('expandtabs', 2, defaults=(8,))
str_splitlines = MultiMethod('splitlines', 2, defaults=(0,))
str_startswith = MultiMethod('startswith', 2) #[optional arguments not supported now]
str_translate  = MultiMethod('translate', 3, defaults=('',)) #unicode mimic not supported now

# ____________________________________________________________

def descr__new__(space, w_stringtype, w_obj=''):
    return space.str(w_obj)

# ____________________________________________________________

str_typedef = StdTypeDef("str", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
str_typedef.registermethods(globals())
