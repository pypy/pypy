from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef
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
    w_obj = space.newlist([])
    return space.w_list.check_user_subclass(w_listtype, w_obj)

# ____________________________________________________________

list_typedef = StdTypeDef("list", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
list_typedef.registermethods(globals())
