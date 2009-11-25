from pypy.objspace.std.objspace import *

def descr_get_dictproxy(space, w_obj):
    return W_DictProxyObject(w_obj.getdict())

class W_DictProxyObject(W_Object):
    from pypy.objspace.std.dictproxytype import dictproxy_typedef as typedef
    
    def __init__(w_self, w_dict):
        w_self.w_dict = w_dict

registerimplementation(W_DictProxyObject)

register_all(vars())
