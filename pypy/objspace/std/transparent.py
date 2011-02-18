
""" transparent.py - Several transparent proxy helpers
"""

from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.objspace.std.proxyobject import *
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.rlib.objectmodel import r_dict
from pypy.rlib.unroll import unrolling_iterable

class TypeCache(object):
    def __init__(self):
        self.cache = []

    def _freeze_(self):
        self.cache = unrolling_iterable(self.cache)
        return True

type_cache = TypeCache()


def setup(space):
    """Add proxy functions to the __pypy__ module."""
    w___pypy__ = space.getbuiltinmodule("__pypy__")
    space.setattr(w___pypy__, space.wrap('tproxy'), space.wrap(app_proxy))
    space.setattr(w___pypy__, space.wrap('get_tproxy_controller'),
                  space.wrap(app_proxy_controller))



def proxy(space, w_type, w_controller):
    """tproxy(typ, controller) -> obj
Return something that looks like it is of type typ. Its behaviour is
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
    w_lookup = w_type
    for k, v in type_cache.cache:
        if w_lookup == k:
            return v(space, w_type, w_controller)
    raise operationerrfmt(space.w_TypeError, 
        "'%s' object could not be wrapped (YET)",
        w_type.getname(space))

def register_proxyable(space, cls):
    tpdef = cls.typedef
    class W_TransparentUserCreated(W_Transparent):
        typedef = tpdef
    type_cache.cache.append((space.gettypeobject(tpdef), W_TransparentUserCreated))

def proxy_controller(space, w_object):
    """get_tproxy_controller(obj) -> controller
If obj is really a transparent proxy, return its controller. Otherwise return
None."""
    if isinstance(w_object, W_Transparent):
        return w_object.w_controller
    if isinstance(w_object, W_TransparentObject):
        return w_object.w_controller
    return None

app_proxy = gateway.interp2app(proxy)
app_proxy_controller = gateway.interp2app(proxy_controller)
