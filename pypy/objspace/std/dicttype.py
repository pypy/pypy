from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.objecttype import object_typedef
from pypy.objspace.std.register_all import register_all

dict_copy       = MultiMethod('copy',          1)
dict_items      = MultiMethod('items',         1)
dict_keys       = MultiMethod('keys',          1)
dict_values     = MultiMethod('values',        1)
dict_has_key    = MultiMethod('has_key',       2)
dict_clear      = MultiMethod('clear',         1)
dict_get        = MultiMethod('get',           3, defaults=(None,))
dict_pop        = MultiMethod('pop',           2, varargs=True)
dict_popitem    = MultiMethod('popitem',       1)
dict_setdefault = MultiMethod('setdefault',    3, defaults=(None,))
dict_update     = MultiMethod('update',        2)
dict_iteritems  = MultiMethod('iteritems',     1)
dict_iterkeys   = MultiMethod('iterkeys',      1)
dict_itervalues = MultiMethod('itervalues',    1)
#dict_fromkeys   = MultiMethod('fromkeys',      2, varargs=True)
# This can return when multimethods have been fixed
#dict_str        = StdObjSpace.str

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

#def app_dict_fromkeys__ANY_List(d, seq, value):
#    d = {}
#    if value:
#        value = value[0]
#    else:
#        value = None
#    for item in seq:
#        d[item] = value
#    return d
#XXX implement dict.fromkeys() which must be a static method
#XXX accepting any iterable

# This can return when multimethods have been fixed
"""
def app_dict_str__ANY(d):
    items = []
    for k, v in d.iteritems():
        items.append("%r: %r" % (k, v))
    return "{%s}" % ', '.join(items)
"""
gateway.importall(globals())
register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_dicttype, *args_w, **kwds_w):
    from pypy.objspace.std.dictobject import W_DictObject
    w_obj = W_DictObject(space, [])
    return space.w_dict.check_user_subclass(w_dicttype, w_obj)

# ____________________________________________________________

dict_typedef = StdTypeDef("dict", [object_typedef],
    __new__ = newmethod(descr__new__),
    )
dict_typedef.registermethods(globals())
