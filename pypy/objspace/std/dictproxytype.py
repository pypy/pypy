from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from pypy.interpreter.error import OperationError

# ____________________________________________________________

def proxymethod(name):
    def fget(space, w_obj):
        obj = space.unwrap_builtin(w_obj)
        return space.getattr(obj.w_dict, space.wrap(name))
    return GetSetProperty(fget)

# ____________________________________________________________

dictproxy_typedef = StdTypeDef("dictproxy",
    has_key = proxymethod('has_key'),
    get = proxymethod('get'),
    keys = proxymethod('keys'),
    values = proxymethod('values'),
    items = proxymethod('items'),
    iterkeys = proxymethod('iterkeys'),
    itervalues = proxymethod('itervalues'),
    iteritems = proxymethod('iteritems'),
    copy = proxymethod('copy'),
    __len__ = proxymethod('__len__'),
    __getitem__ = proxymethod('__getitem__'),
    __contains__ = proxymethod('__contains__'),
    __str__ = proxymethod('__str__'),
    __iter__ = proxymethod('__iter__'),
    __cmp__ = proxymethod('__cmp__'),
    __lt__ = proxymethod('__lt__'),
    __le__ = proxymethod('__le__'),
    __eq__ = proxymethod('__eq__'),
    __ne__ = proxymethod('__ne__'),
    __gt__ = proxymethod('__gt__'),
    __ge__ = proxymethod('__ge__'),
)
dictproxy_typedef.registermethods(globals())
