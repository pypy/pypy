"""
Reviewed 03-06-22
"""

from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject

class _no_object: pass

class W_DictType(W_TypeObject):

    typename = 'dict'

    dict_copy       = MultiMethod('copy',       1)
    dict_items      = MultiMethod('items',      1)
    dict_keys       = MultiMethod('keys',       1)
    dict_values     = MultiMethod('values',     1)
    dict_has_key    = MultiMethod('has_key',    2)
    dict_clear      = MultiMethod('clear',      1)
    dict_get        = MultiMethod('get',        3, defaults=(None,))
    dict_pop        = MultiMethod('pop',        3, defaults=(_no_object,))
    dict_popitem    = MultiMethod('popitem',    1)
    dict_setdefault = MultiMethod('setdefault', 3)
    dict_update     = MultiMethod('update',     2)
    dict_iteritems  = MultiMethod('iteritems',  1)
    dict_iterkeys   = MultiMethod('iterkeys',   1)
    dict_itervalues = MultiMethod('itervalues', 1)
    
