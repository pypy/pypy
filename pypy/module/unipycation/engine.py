from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import W_Root

import prolog.interpreter.continuation as pcont

class UnipycationContinuation(pcont.Continuation):                                       
    def __init__(self, engine, var_to_pos, write):                              
        pcont.Continuation.__init__(self, engine, pcont.DoneSuccessContinuation(engine))    
        self.var_to_pos = var_to_pos                                            
        self.write = write                  

    def activate(self, fcont, heap):
        print(fcont)    # XXX unpack this and expose to Python
        return pcont.DoneSuccessContinuation(self.engine), fcont, heap

def engine_new__(space, w_subtype, __args__):
    w_anything = __args__.firstarg()                                            
    e = W_Engine(space, w_anything)
    return space.wrap(e)

def printmessage(x):
    print(type(x))
    print(x)

class W_Engine(W_Root):
    def __init__(self, space, w_anything):
        self.space = space                      # Stash space
        self.engine = e = pcont.Engine()        # We embed an instance of prolog
        e.runstring(space.str_w(w_anything))    # Load the database with the first arg

    def query(self, w_anything):
        query_raw = self.space.str_w(w_anything)
        goals, var_to_pos = self.engine.parse(query_raw)

        cont =UnipycationContinuation(self.engine, var_to_pos, printmessage)
        for g in goals:
            self.engine.run(g, self.engine.modulewrapper.current_module, cont)

W_Engine.typedef = TypeDef("Engine",
    __new__ = interp2app(engine_new__),
    query = interp2app(W_Engine.query),
)

W_Engine.typedef.acceptable_as_base_class = False
