"""


"""
from pypy.interpreter.gateway import interp2app 

class TypeDef:
    def __init__(self, name, rawdict):
        self.name = name
        self.rawdict = rawdict 

    def mro(self, space):
        return [self, space.object_typedef]

class GetSetProperty:
    def __init__(self, fget, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.doc = doc

    def descr_property_get(space, w_property, w_obj, w_ignored):
        return space.unwrap(w_property).fget(space, w_obj)

    typedef = TypeDef("GetSetProperty", { 
        '__get__' : interp2app(descr_property_get),
    })

def attrproperty(name):
    def fget(space, w_obj):
        obj = space.unwrap(w_obj)
        return space.wrap(getattr(obj, name))
    return GetSetProperty(fget)

def attrproperty_w(name):
    def fget(space, w_obj):
        obj = space.unwrap(w_obj)
        w_value = getattr(obj, name)
        if w_value is None:
            return space.w_None
        else:
            return w_value 

    return GetSetProperty(fget)
