from pypy.rpython.rarithmetic import r_longlong
from pypy.interpreter.gateway import interp2app, W_Root
from pypy.interpreter.baseobjspace import ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef, interp_attrproperty, GetSetProperty

class SomeClass(object):
    def __init__(self, x):
        # hook for caching wrapped trades
        self.w_cache = None
        self.x = x

class W_SomeClass(Wrappable):
    def __init__(self, space, someclass):
        self.space = space
        assert isinstance(someclass, SomeClass)
        self.someclass = someclass

    def multiply(self, w_y):
        space = self.space
        y = space.int_w(w_y)
        return space.wrap(self.someclass.x * y)
    
    def fget_x(space, self):
        return space.wrap(self.someclass.x)

    def fset_x(space, self, w_value):
        self.someclass.x = space.int_w(w_value)

    def descr__str__(self, space):
        return space.wrap("someclass")

    def descr__mul__(self, space, w_y):
        y = space.int_w(w_y)
        self.someclass.x = self.someclass.x * y
        return space.wrap(self)

# XXX special methods dont work yet
#descr__str__ = interp2app(W_SomeClass.descr__str__, unwrap_spec=['self', ObjSpace])
#descr__mul__ = interp2app(W_SomeClass.descr__mul__, unwrap_spec=['self', ObjSpace, W_Root])
getset_x = GetSetProperty(W_SomeClass.fget_x, W_SomeClass.fset_x, cls=W_SomeClass)
getset_x_read = GetSetProperty(W_SomeClass.fget_x, None, cls=W_SomeClass)
W_SomeClass.typedef = TypeDef("SomeClass",
                              x        = getset_x,
                              x_read   = getset_x_read,
                              multiply = interp2app(W_SomeClass.multiply))
                              #__mul__  = descr__mul__,
                              #__str__  = descr__str__)

def _wrapsomeclass(space, somecls):
    if somecls.w_cache is None:
        w_somecls = W_SomeClass(space, somecls)
        somecls.w_cache = w_somecls        
    else:
        assert isinstance(somecls, SomeClass)
        w_somecls = somecls.w_cache
    assert w_somecls is not None
    return space.wrap(w_somecls)

def new_someclass(space, x):
    longlong_x = r_longlong(x)
    somecls = SomeClass(longlong_x)
    return _wrapsomeclass(space, somecls)

new_someclass.unwrap_spec = [ObjSpace, int]


def someclassbig(space, x):
    longlong_x = r_longlong(x) * 10 ** 9
    longlong_x *= 10
    somecls = SomeClass(longlong_x)
    return _wrapsomeclass(space, somecls)

someclassbig.unwrap_spec = [ObjSpace, int]
