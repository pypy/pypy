"""
Reviewed 03-06-22
"""

from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway
from typeobject import W_TypeObject

class W_DictType(W_TypeObject):

    typename = 'dict'

    dict_copy       = MultiMethod('copy',       1)
    dict_items      = MultiMethod('items',      1)
    dict_keys       = MultiMethod('keys',       1)
    dict_values     = MultiMethod('values',     1)
    dict_has_key    = MultiMethod('has_key',    2)
    dict_clear      = MultiMethod('clear',      1)
    dict_get        = MultiMethod('get',        3, defaults=(None,))
    dict_pop        = MultiMethod('pop',        2, varargs=True)
    dict_popitem    = MultiMethod('popitem',    1)
    dict_setdefault = MultiMethod('setdefault', 3, defaults=(None,))
    dict_update     = MultiMethod('update',     2)
    dict_iteritems  = MultiMethod('iteritems',  1)
    dict_iterkeys   = MultiMethod('iterkeys',   1)
    dict_itervalues = MultiMethod('itervalues', 1)
    # This can return when multimethods have been fixed
    #dict_str        = StdObjSpace.str

registerimplementation(W_DictType)


def type_new__DictType_DictType(space, w_basetype, w_dicttype, w_args, w_kwds):
    return space.newdict([]), True


# default application-level implementations for some operations

def app_dict_update__ANY_ANY(d, o):
    for k in o.keys():
        d[k] = o[k]

def app_dict_popitem__ANY(d):
    k = d.keys()
    if not k:
        raise KeyError("popitem(): dictionary is empty")
    k = k[0]
    v = d[k]
    del d[k]
    return k, v

def app_dict_get__ANY_ANY_ANY(d, k, v=None):
    if d.has_key(k):
        return d[k]
    return v

def app_dict_setdefault__ANY_ANY_ANY(d, k, v):
    if d.has_key(k):
        return d[k]
    d[k] = v
    return v

def app_dict_pop__ANY_ANY(d, k, default):
    if len(default) > 1:
        raise TypeError, "pop expected at most 2 arguments, got %d" % (
            1 + len(default))
    try:
        v = d[k]
        del d[k]
    except KeyError, e:
        if default:
            return default[0]
        else:
            raise e
    return v

def app_dict_iteritems__ANY(d):
    return iter(d.items())

def app_dict_iterkeys__ANY(d):
    return iter(d.keys())

def app_dict_itervalues__ANY(d):
    return iter(d.values())

# This can return when multimethods have been fixed
"""
def app_dict_str__ANY(d):
    items = []
    for k, v in d.iteritems():
        items.append("%r: %r" % (k, v))
    return "{%s}" % ', '.join(items)
"""
gateway.importall(globals())
register_all(vars(), W_DictType)
