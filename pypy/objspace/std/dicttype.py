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
    
# XXX we'll worry about the __new__/__init__ distinction later
def dicttype_new(space, w_listtype, w_args, w_kwds):
    # w_kwds = w_kwds.copy() w unwrap & rewrap, but that should not be needed
    args = space.unpackiterable(w_args)
    if len(args) == 0:
        pass
    elif len(args) == 1:
        list_of_w_pairs = space.unpackiterable(args[0])
        list_of_w_pairs.reverse()
        for pair_w in list_of_w_pairs:
            pair = space.unpackiterable(pair_w)
            if len(pair)!=2:
                raise OperationError(space.w_ValueError,
                             space.wrap("dict() takes a sequence of pairs"))
            k, v = pair
            if not space.is_true(space.contains(w_kwds, k)):
                space.setitem(w_kwds, k, v)
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("dict() takes at most 1 argument"))
    return w_kwds

StdObjSpace.new.register(dicttype_new, W_DictType, W_ANY, W_ANY)
