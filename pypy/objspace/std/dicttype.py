from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_DictType(W_TypeObject):

    typename = 'dict'

    dict_copy   = MultiMethod('copy',   1)
    dict_items  = MultiMethod('items',  1)
    dict_keys   = MultiMethod('keys',   1)
    dict_values = MultiMethod('values', 1)
