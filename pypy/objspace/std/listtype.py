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

# gateway is imported in the stdtypedef module
list_reversed__ANY = gateway.applevel('''
    # NOT_RPYTHON -- uses yield

    def reversed(lst):
        for index in range(len(lst)-1, -1, -1):
            yield lst[index]

''', filename=__file__).interphook('reversed')

register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_listtype, __args__):
    from pypy.objspace.std.listobject import W_ListObject
    w_obj = space.allocate_instance(W_ListObject, w_listtype)
    W_ListObject.__init__(w_obj, space, [])
    return w_obj

# ____________________________________________________________

list_typedef = StdTypeDef("list",
    __new__ = newmethod(descr__new__, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.Arguments]),
    )
list_typedef.registermethods(globals())
