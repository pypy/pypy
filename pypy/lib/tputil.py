"""

application level support module for transparent proxies. 
This currently contains a BaseDispatcher class
whose subclasses may define "op_METH" where METH 
is the original method operation name for 
the proxied object. 

"""
from pypymagic import transparent_proxy 
from types import MethodType

def make_proxy(instance, invokefunc=None, typ=None): 
    if typ is None:
        typ = type(instance) 
    def perform(opname, *args, **kwargs):
        invocation = Invocation(tp, instance, opname, args, kwargs)
        return invokefunc(invocation) 
    tp = transparent_proxy(typ, perform) 
    return tp 

class Invocation(object):
    def __init__(self, proxyobj, realobj, opname, args, kwargs):
        self.proxyobj = proxyobj
        self.realobj = realobj 
        self.opname = opname 
        self.args = args
        self.kwargs = kwargs
        self.realmethod = getattr(realobj, opname) 

    def perform(self):
        res = self.realmethod(*self.args, **self.kwargs)
        if self.opname == "__getattribute__": 
            if (isinstance(res, MethodType) and
                res.im_self is self.realobj):
                res = MethodType(res.im_func, self.proxyobj, res.im_class)
        return res 

    def __repr__(self):
        return "<Invocation %s(*%r, **%r)" %(self.realmethod, 
                                             self.args, self.kwargs)
