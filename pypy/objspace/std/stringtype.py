from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.basestringtype import basestring_typedef

from sys import maxint

str_join    = StdObjspaceMultiMethod('join', 2)
str_split   = StdObjspaceMultiMethod('split', 3, defaults=(None,-1))
str_rsplit  = StdObjspaceMultiMethod('rsplit', 3, defaults=(None,-1))
str_isdigit    = StdObjspaceMultiMethod('isdigit', 1)
str_isalpha    = StdObjspaceMultiMethod('isalpha', 1)
str_isspace    = StdObjspaceMultiMethod('isspace', 1)
str_isupper    = StdObjspaceMultiMethod('isupper', 1)
str_islower    = StdObjspaceMultiMethod('islower', 1)
str_istitle    = StdObjspaceMultiMethod('istitle', 1)
str_isalnum    = StdObjspaceMultiMethod('isalnum', 1)
str_ljust      = StdObjspaceMultiMethod('ljust', 3, defaults=(' ',))
str_rjust      = StdObjspaceMultiMethod('rjust', 3, defaults=(' ',))
str_upper      = StdObjspaceMultiMethod('upper', 1)
str_lower      = StdObjspaceMultiMethod('lower', 1)
str_swapcase   = StdObjspaceMultiMethod('swapcase', 1)
str_capitalize = StdObjspaceMultiMethod('capitalize', 1)
str_title      = StdObjspaceMultiMethod('title', 1)
str_find       = StdObjspaceMultiMethod('find', 4, defaults=(0, maxint))
str_rfind      = StdObjspaceMultiMethod('rfind', 4, defaults=(0, maxint))
str_index      = StdObjspaceMultiMethod('index', 4, defaults=(0, maxint))
str_rindex     = StdObjspaceMultiMethod('rindex', 4, defaults=(0, maxint))
str_replace    = StdObjspaceMultiMethod('replace', 4, defaults=(-1,))
str_zfill      = StdObjspaceMultiMethod('zfill', 2)
str_strip      = StdObjspaceMultiMethod('strip',  2, defaults=(None,))
str_rstrip     = StdObjspaceMultiMethod('rstrip', 2, defaults=(None,))
str_lstrip     = StdObjspaceMultiMethod('lstrip', 2, defaults=(None,))
str_center     = StdObjspaceMultiMethod('center', 3, defaults=(' ',))
str_count      = StdObjspaceMultiMethod('count', 4, defaults=(0, maxint))      
str_endswith   = StdObjspaceMultiMethod('endswith', 4, defaults=(0, maxint))
str_expandtabs = StdObjspaceMultiMethod('expandtabs', 2, defaults=(8,))
str_splitlines = StdObjspaceMultiMethod('splitlines', 2, defaults=(0,))
str_startswith = StdObjspaceMultiMethod('startswith', 4, defaults=(0, maxint))
str_translate  = StdObjspaceMultiMethod('translate', 3, defaults=('',)) #unicode mimic not supported now
str_decode     = StdObjspaceMultiMethod('decode', 3, defaults=(None, None))
str_encode     = StdObjspaceMultiMethod('encode', 3, defaults=(None, None))

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
