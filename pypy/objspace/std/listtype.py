from __future__ import generators
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from sys import maxint

list_append   = MultiMethod('append', 2)
list_insert   = MultiMethod('insert', 3)
list_extend   = MultiMethod('extend', 2)
list_pop      = MultiMethod('pop',    2, defaults=(-1,))
list_remove   = MultiMethod('remove', 2)
list_index    = MultiMethod('index',  4, defaults=(0,maxint))
list_count    = MultiMethod('count',  2)
list_reverse  = MultiMethod('reverse',1)
list_sort     = MultiMethod('sort',   4, defaults=(None, None, False), argnames=['cmp', 'key', 'reverse'])
list_reversed = MultiMethod('__reversed__', 1)

def app_list_reversed__ANY(lst):
    def reversed_gen(local_iterable):
        len_iterable = len(local_iterable)
        for index in range(len_iterable-1, -1, -1):
            yield local_iterable[index]
    return reversed_gen(lst)

# gateway is imported in the stdtypedef module
gateway.importall(globals())
register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_listtype, __args__):
    from pypy.objspace.std.listobject import W_ListObject
    w_obj = space.allocate_instance(W_ListObject, w_listtype)
    w_obj.__init__(space, [])
    return w_obj

# ____________________________________________________________

list_typedef = StdTypeDef("list",
    __new__ = newmethod(descr__new__),
    )
list_typedef.registermethods(globals())
