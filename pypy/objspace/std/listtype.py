from pypy.objspace.std.stdtypedef import *
from sys import maxint

list_append = MultiMethod('append', 2)
list_insert = MultiMethod('insert', 3)
list_extend = MultiMethod('extend', 2)
list_pop    = MultiMethod('pop',    2, defaults=(-1,))
list_remove = MultiMethod('remove', 2)
list_index  = MultiMethod('index',  4, defaults=(0,maxint))
list_count  = MultiMethod('count',  2)
list_reverse= MultiMethod('reverse',1)
list_sort   = MultiMethod('sort',   2, defaults=(None,))

# ____________________________________________________________

def descr__new__(space, w_listtype, *args_w, **kwds_w):
    from listobject import W_ListObject
    w_obj = space.allocate_instance(W_ListObject, w_listtype)
    w_obj.__init__(space, [])
    return w_obj

# ____________________________________________________________

list_typedef = StdTypeDef("list",
    __new__ = newmethod(descr__new__),
    )
list_typedef.registermethods(globals())
