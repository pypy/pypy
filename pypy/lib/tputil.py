"""

application level support module for transparent proxies. 
This currently contains a BaseDispatcher class
whose subclasses may define "op_METH" where METH 
is the original method operation name for 
the proxied object. 

"""
from pypymagic import transparent_proxy 
from types import MethodType

class BaseDispatcher(object):
    def __init__(self, realobj, typ=None):
        self.realobj = realobj 
        if typ is None:
            typ = type(realobj) 
        self.proxyobj = transparent_proxy(typ, self.invoke)

    def invoke(self, operation, *args, **kwargs):
        """ return result from dispatching to proxied operation. """
        realmethod = getattr(self.realobj, operation) 
        print "operation", operation
        dispmethod = getattr(self, "op_" + operation, None)
        if dispmethod is None:
            dispmethod = self.op_default 
        res = dispmethod(realmethod, *args, **kwargs)
        return res

    def op___getattribute__(self, realmethod, *args, **kwargs):
        res = realmethod(*args, **kwargs)
        if (isinstance(res, MethodType) and
             res.im_self is self.realobj):
            res= MethodType(res.im_func, self.proxyobj, res.im_class)
        return res
        
    def op_default(self, realmethod, *args, **kwargs):
        return realmethod(*args, **kwargs)

