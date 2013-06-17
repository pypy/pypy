from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import W_Root

def engine_new__(space, w_subtype, __args__):
    w_anything = __args__.firstarg()                                            
    x = space.allocate_instance(W_Engine, w_subtype)                            
    x = space.interp_w(W_Engine, x)                                             
    W_Engine.__init__(x, space, w_anything)                                     
    return space.wrap(x)

class W_Engine(W_Root):
    def __init__(self, space, w_anything):
        print("INITIALISING A PROLOG ENGINE")

W_Engine.typedef = TypeDef("Engine",
    __new__ = interp2app(engine_new__)
)
