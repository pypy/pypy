from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.basestringtype import basestring_typedef

from sys import maxint

str_join    = StdObjSpaceMultiMethod('join', 2)
str_split   = StdObjSpaceMultiMethod('split', 3, defaults=(None,-1))
str_rsplit  = StdObjSpaceMultiMethod('rsplit', 3, defaults=(None,-1))
str_isdigit    = StdObjSpaceMultiMethod('isdigit', 1)
str_isalpha    = StdObjSpaceMultiMethod('isalpha', 1)
str_isspace    = StdObjSpaceMultiMethod('isspace', 1)
str_isupper    = StdObjSpaceMultiMethod('isupper', 1)
str_islower    = StdObjSpaceMultiMethod('islower', 1)
str_istitle    = StdObjSpaceMultiMethod('istitle', 1)
str_isalnum    = StdObjSpaceMultiMethod('isalnum', 1)
str_ljust      = StdObjSpaceMultiMethod('ljust', 3, defaults=(' ',))
str_rjust      = StdObjSpaceMultiMethod('rjust', 3, defaults=(' ',))
str_upper      = StdObjSpaceMultiMethod('upper', 1)
str_lower      = StdObjSpaceMultiMethod('lower', 1)
str_swapcase   = StdObjSpaceMultiMethod('swapcase', 1)
str_capitalize = StdObjSpaceMultiMethod('capitalize', 1)
str_title      = StdObjSpaceMultiMethod('title', 1)
str_find       = StdObjSpaceMultiMethod('find', 4, defaults=(0, maxint))
str_rfind      = StdObjSpaceMultiMethod('rfind', 4, defaults=(0, maxint))
str_index      = StdObjSpaceMultiMethod('index', 4, defaults=(0, maxint))
str_rindex     = StdObjSpaceMultiMethod('rindex', 4, defaults=(0, maxint))
str_replace    = StdObjSpaceMultiMethod('replace', 4, defaults=(-1,))
str_zfill      = StdObjSpaceMultiMethod('zfill', 2)
str_strip      = StdObjSpaceMultiMethod('strip',  2, defaults=(None,))
str_rstrip     = StdObjSpaceMultiMethod('rstrip', 2, defaults=(None,))
str_lstrip     = StdObjSpaceMultiMethod('lstrip', 2, defaults=(None,))
str_center     = StdObjSpaceMultiMethod('center', 3, defaults=(' ',))
str_count      = StdObjSpaceMultiMethod('count', 4, defaults=(0, maxint))      
str_endswith   = StdObjSpaceMultiMethod('endswith', 4, defaults=(0, maxint))
str_expandtabs = StdObjSpaceMultiMethod('expandtabs', 2, defaults=(8,))
str_splitlines = StdObjSpaceMultiMethod('splitlines', 2, defaults=(0,))
str_startswith = StdObjSpaceMultiMethod('startswith', 4, defaults=(0, maxint))
str_translate  = StdObjSpaceMultiMethod('translate', 3, defaults=('',)) #unicode mimic not supported now
str_decode     = StdObjSpaceMultiMethod('decode', 3, defaults=(None, None))
str_encode     = StdObjSpaceMultiMethod('encode', 3, defaults=(None, None))

# ____________________________________________________________

def descr__new__(space, w_stringtype, w_object=''):
    from pypy.objspace.std.stringobject import W_StringObject
    w_obj = space.str(w_object)
    if space.is_w(w_stringtype, space.w_str):
        return w_obj  # XXX might be reworked when space.str() typechecks
    value = space.str_w(w_obj)
    w_obj = space.allocate_instance(W_StringObject, w_stringtype)
    W_StringObject.__init__(w_obj, space, value)
    return w_obj

# ____________________________________________________________

str_typedef = StdTypeDef("str", basestring_typedef,
    __new__ = newmethod(descr__new__),
    __doc__ = '''str(object) -> string

Return a nice string representation of the object.
If the argument is a string, the return value is the same object.'''
    )
str_typedef.registermethods(globals())
