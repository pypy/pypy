
""" transparent.py - Several transparent proxy helpers
"""

from pypy.interpreter import gateway
from pypy.interpreter.function import Function
from pypy.interpreter.error import OperationError
from pypy.objspace.std.proxyobject import *
from pypy.objspace.std.typeobject import W_TypeObject

def proxy(space, w_type, w_controller):
    """tproxy(typ, controller) -> obj
Return something that looks like it is of type typ. It's behaviour is
completely controlled by the controller."""
    from pypy.interpreter.typedef import Function, PyTraceback, PyFrame, \
        PyCode, GeneratorIterator
    
    if not space.is_true(space.callable(w_controller)):
        raise OperationError(space.w_TypeError, space.wrap("controller should be function"))
    
    if isinstance(w_type, W_TypeObject):
        if space.is_true(space.issubtype(w_type, space.w_list)):
            return W_TransparentList(space, w_type, w_controller)
        if space.is_true(space.issubtype(w_type, space.w_dict)):
            return W_TransparentDict(space, w_type, w_controller)
        if space.is_true(space.issubtype(w_type, space.gettypeobject(Function.typedef))):
            return W_TransparentFunction(space, w_type, w_controller)
        if space.is_true(space.issubtype(w_type, space.gettypeobject(PyTraceback.typedef))):
            return W_TransparentTraceback(space, w_type, w_controller)
        if space.is_true(space.issubtype(w_type, space.gettypeobject(PyFrame.typedef))):
            return W_TransparentFrame(space, w_type, w_controller)
        if space.is_true(space.issubtype(w_type, space.gettypeobject(GeneratorIterator.typedef))):
            return W_TransparentGenerator(space, w_type, w_controller)
        if space.is_true(space.issubtype(w_type, space.gettypeobject(PyCode.typedef))):
            return W_TransparentCode(space, w_type, w_controller)
        if w_type.instancetypedef is space.w_object.instancetypedef:
            return W_Transparent(space, w_type, w_controller)
    else:
        raise OperationError(space.w_TypeError, space.wrap("type expected as first argument"))
    #return type_cache[w_type or w_type.w_bestbase]
    raise OperationError(space.w_TypeError, space.wrap("Object type %s could not "\
          "be wrapped (YET)" % w_type.getname(space, "?")))

def proxy_controller(space, w_object):
    """get_tproxy_controller(obj) -> controller
If obj is really a transparent proxy, return its controller. Otherwise return
None."""
    if isinstance(w_object, W_Transparent):
        return w_object.w_controller
    if isinstance(w_object, W_TransparentObject):
        return w_object.w_controller
    return None

app_proxy = gateway.interp2app(proxy, unwrap_spec=[gateway.ObjSpace, gateway.W_Root, \
    gateway.W_Root])
app_proxy_controller = gateway.interp2app(proxy_controller, unwrap_spec=[gateway.ObjSpace, gateway.W_Root])
