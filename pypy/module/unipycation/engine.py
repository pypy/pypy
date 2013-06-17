from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import W_Root

from prolog.interpreter.continuation import Engine

def engine_new__(space, w_subtype, __args__):
    w_anything = __args__.firstarg()                                            
    e = W_Engine(space, w_anything)
    return space.wrap(e)

class W_Engine(W_Root):
    def __init__(self, space, w_anything):
        self.engine = e = Engine()              # We embed an instance of prolog
        e.runstring(space.str_w(w_anything))    # Load the database with the first arg
        print("INITIALISED A PROLOG ENGINE")

W_Engine.typedef = TypeDef("Engine",
    __new__ = interp2app(engine_new__)
)

W_Engine.typedef.acceptable_as_base_class = False
