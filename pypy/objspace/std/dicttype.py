from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all

dict_copy       = MultiMethod('copy',          1)
dict_items      = MultiMethod('items',         1)
dict_keys       = MultiMethod('keys',          1)
dict_values     = MultiMethod('values',        1)
dict_has_key    = MultiMethod('has_key',       2)
dict_clear      = MultiMethod('clear',         1)
dict_get        = MultiMethod('get',           3, defaults=(None,))
dict_pop        = MultiMethod('pop',           2, w_varargs=True)
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
# gateway is imported in the stdtypedef module
app = gateway.applevel('''

    def update(d, o):
        for k in o.keys():
            d[k] = o[k]

    def popitem(d):
        k = d.keys()
        if not k:
            raise KeyError("popitem(): dictionary is empty")
        k = k[0]
        v = d[k]
        del d[k]
        return k, v

    def get(d, k, v=None):
        if k in d:
            return d[k]
        else:
            return v

    def setdefault(d, k, v=None):
        if k in d:
            return d[k]
        else:
            d[k] = v
            return v

    def pop(d, k, defaults):     # XXX defaults is actually *defaults
        if len(defaults) > 1:
            raise TypeError, "pop expected at most 2 arguments, got %d" % (
                1 + len(defaults))
        try:
            v = d[k]
            del d[k]
        except KeyError, e:
            if defaults:
                return defaults[0]
            else:
                raise e
        return v

    def iteritems(d):
        return iter(d.items())

    def iterkeys(d):
        return iter(d.keys())

    def itervalues(d):
        return iter(d.values())
''')
#XXX what about dict.fromkeys()?

dict_update__ANY_ANY         = app.interphook("update")
dict_popitem__ANY            = app.interphook("popitem")
dict_get__ANY_ANY_ANY        = app.interphook("get")
dict_setdefault__ANY_ANY_ANY = app.interphook("setdefault")
dict_pop__ANY_ANY            = app.interphook("pop")
dict_iteritems__ANY          = app.interphook("iteritems")
dict_iterkeys__ANY           = app.interphook("iterkeys")
dict_itervalues__ANY         = app.interphook("itervalues")

register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_dicttype, __args__):
    from pypy.objspace.std.dictobject import W_DictObject
    w_obj = space.allocate_instance(W_DictObject, w_dicttype)
    w_obj.__init__(space, [])
    return w_obj

# ____________________________________________________________

dict_typedef = StdTypeDef("dict",
    __new__ = newmethod(descr__new__,
                        unwrap_spec=[gateway.ObjSpace,gateway.W_Root,gateway.Arguments]),
    )
dict_typedef.registermethods(globals())
