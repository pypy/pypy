from pypy.objspace.std.objspace import *
from typeobject import W_TypeObject


class W_ListType(W_TypeObject):

    typename = 'list'

    list_append = MultiMethod('append', 2)
    list_insert = MultiMethod('insert', 3)
    list_extend = MultiMethod('extend', 2)
    list_pop    = MultiMethod('pop',    2)
    list_remove = MultiMethod('remove', 2)
    list_index  = MultiMethod('index',  2)
    list_count  = MultiMethod('count',  2)
    list_reverse= MultiMethod('reverse',1)


# XXX right now, this is responsible for building a whole new list
# XXX we'll worry about the __new__/__init__ distinction later
def listtype_new(space, w_listtype, w_args, w_kwds):
    if space.is_true(w_kwds):
        raise OperationError(space.w_TypeError,
                             space.wrap("no keyword arguments expected"))
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        list_w = []
    elif len(args) == 1:
        list_w = space.unpackiterable(args[0])
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("list() takes at most 1 argument"))
    return space.newlist(list_w)

StdObjSpace.new.register(listtype_new, W_ListType, W_ANY, W_ANY)
