from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from pypy.interpreter.error import OperationError

# ____________________________________________________________

def _proxymethod(name):
    def fget(space, w_obj):
        from pypy.objspace.std.dictproxyobject import W_DictProxyObject
        if not isinstance(w_obj, W_DictProxyObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("expected dictproxy"))
        return space.getattr(w_obj.w_dict, space.wrap(name))
    return GetSetProperty(fget)

# ____________________________________________________________

dictproxy_typedef = StdTypeDef("dictproxy",
    has_key = _proxymethod('has_key'),
    get = _proxymethod('get'),
    keys = _proxymethod('keys'),
    values = _proxymethod('values'),
    items = _proxymethod('items'),
    iterkeys = _proxymethod('iterkeys'),
    itervalues = _proxymethod('itervalues'),
    iteritems = _proxymethod('iteritems'),
    copy = _proxymethod('copy'),
    __len__ = _proxymethod('__len__'),
    __getitem__ = _proxymethod('__getitem__'),
    __contains__ = _proxymethod('__contains__'),
    __str__ = _proxymethod('__str__'),
    __iter__ = _proxymethod('__iter__'),
    #__cmp__ = _proxymethod('__cmp__'),
    # you cannot have it here if it is not in dict
    __lt__ = _proxymethod('__lt__'),
    __le__ = _proxymethod('__le__'),
    __eq__ = _proxymethod('__eq__'),
    __ne__ = _proxymethod('__ne__'),
    __gt__ = _proxymethod('__gt__'),
    __ge__ = _proxymethod('__ge__'),
)
dictproxy_typedef.registermethods(globals())
