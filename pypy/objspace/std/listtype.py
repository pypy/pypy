from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_ListType(W_TypeObject):

    typename = 'list'

    list_append = MultiMethod('append', 2)
    list_insert = MultiMethod('insert', 3)
    list_extend = MultiMethod('extend', 2)
    list_pop    = MultiMethod('pop',    2, defaults=(-1,))
    list_remove = MultiMethod('remove', 2)
    list_index  = MultiMethod('index',  2)
    list_count  = MultiMethod('count',  2)
    list_reverse= MultiMethod('reverse',1)
    list_sort   = MultiMethod('sort',   1)

registerimplementation(W_ListType)


def type_new__ListType_ListType(space, w_basetype, w_listtype, w_args, w_kwds):
    return space.newlist([]), True

register_all(vars())
