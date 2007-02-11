from pypy.objspace.std.stdtypedef import *
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

def _compareproxymethod(opname):
    def compare(space, w_obj1, w_obj2):
        from pypy.objspace.std.dictproxyobject import W_DictProxyObject
        if not isinstance(w_obj1, W_DictProxyObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap("expected dictproxy"))
        return getattr(space, opname)(w_obj1.w_dict, w_obj2)
    return gateway.interp2app(compare)

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
    __lt__ = _compareproxymethod('lt'),
    __le__ = _compareproxymethod('le'),
    __eq__ = _compareproxymethod('eq'),
    __ne__ = _compareproxymethod('ne'),
    __gt__ = _compareproxymethod('gt'),
    __ge__ = _compareproxymethod('ge'),
)
dictproxy_typedef.registermethods(globals())
