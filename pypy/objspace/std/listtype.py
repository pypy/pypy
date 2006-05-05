from __future__ import generators
from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from sys import maxint

list_append   = StdObjSpaceMultiMethod('append', 2)
list_insert   = StdObjSpaceMultiMethod('insert', 3)
list_extend   = StdObjSpaceMultiMethod('extend', 2)
list_pop      = StdObjSpaceMultiMethod('pop',    2, defaults=(-1,))
list_remove   = StdObjSpaceMultiMethod('remove', 2)
list_index    = StdObjSpaceMultiMethod('index',  4, defaults=(0,maxint))
list_count    = StdObjSpaceMultiMethod('count',  2)
list_reverse  = StdObjSpaceMultiMethod('reverse',1)
list_sort     = StdObjSpaceMultiMethod('sort',   4, defaults=(None, None, False), argnames=['cmp', 'key', 'reverse'])
list_reversed = StdObjSpaceMultiMethod('__reversed__', 1)
##
##list_reversed__ANY = gateway.applevel('''
##    # NOT_RPYTHON -- uses yield
##
##    def reversed(lst):
##        return iter([x for x in lst[::-1]])
##    #    for index in range(len(lst)-1, -1, -1):
##    #        yield lst[index]
##
##''', filename=__file__).interphook('reversed')
def list_reversed__ANY(space, w_list):
    from pypy.objspace.std.iterobject import W_ReverseSeqIterObject
    return W_ReverseSeqIterObject(space, w_list, -1)

register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_listtype, __args__):
    from pypy.objspace.std.listobject import W_ListObject
    w_obj = space.allocate_instance(W_ListObject, w_listtype)
    W_ListObject.__init__(w_obj, [])
    return w_obj

# ____________________________________________________________

list_typedef = StdTypeDef("list",
    __doc__ = '''list() -> new list
list(sequence) -> new list initialized from sequence's items''',
    __new__ = newmethod(descr__new__, unwrap_spec=[gateway.ObjSpace,
                                                   gateway.W_Root,
                                                   gateway.Arguments]),
    __hash__ = no_hash_descr,
    )
list_typedef.registermethods(globals())
