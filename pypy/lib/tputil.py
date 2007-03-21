"""

application level support module for transparent proxies. 
This currently contains a BaseDispatcher class
whose subclasses may define "op_METH" where METH 
is the original method operation name for 
the proxied object. 

"""
from __pypy__ import tproxy 
from types import MethodType

_dummy = object()
origtype = type

def make_proxy(controller, type=_dummy, obj=_dummy): 
    """ return a tranparent proxy controlled by the given 
        'controller' callable.  The proxy will appear 
        as a completely regular instance of the given 
        type but all operations on it are send to the 
        specified controller - which receices on 
        ProxyOperation instance on each such call.  A non-specified 
        type will default to type(obj) if obj is specified. 
    """
    if type is _dummy: 
        if obj is _dummy: 
            raise TypeError("you must specify a type or an instance obj") 
        type = origtype(obj) 
    def perform(opname, *args, **kwargs):
        operation = ProxyOperation(tp, type, obj, opname, args, kwargs)
        return controller(operation) 
    tp = tproxy(type, perform) 
    return tp 

class ProxyOperation(object):
    def __init__(self, proxyobj, type, obj, opname, args, kwargs):
        self.proxyobj = proxyobj
        self.opname = opname 
        self.args = args
        self.kwargs = kwargs
        self.type = type 
        if obj is not _dummy: 
            self.obj = obj 

    def delegate(self):
        """ return result from delegating this operation to the 
            underyling self.obj - which must exist and is usually 
            provided through the initial make_proxy(..., obj=...) 
            creation. 
        """ 
        try:
            obj = getattr(self, 'obj')
        except AttributeError: 
            raise TypeError("proxy does not have an underlying 'obj', "
                            "cannot delegate")
        objattr = getattr(obj, self.opname) 
        res = objattr(*self.args, **self.kwargs) 
        if self.opname == "__getattribute__": 
            if (isinstance(res, MethodType) and
                res.im_self is self.instance):
                res = MethodType(res.im_func, self.proxyobj, res.im_class)
        if res is self.obj: 
            res = self.proxyobj
        return res 

    def __repr__(self):
        return "<ProxyOperation %s(*%r, **%r) %x>" %(
                    self.opname, self.args, self.kwargs, id(self))
