from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import W_Root

import prolog.interpreter.continuation as pcont
import prolog.interpreter.term as pterm

class UnipycationContinuation(pcont.Continuation):
    def __init__(self, engine, var_to_pos, w_engine):
        pcont.Continuation.__init__(self, engine, pcont.DoneSuccessContinuation(engine))
        self.var_to_pos = var_to_pos
        self.w_engine = w_engine

    def activate(self, fcont, heap):
        self.w_engine.populate_result(self.var_to_pos, heap)
        return pcont.DoneSuccessContinuation(self.engine), fcont, heap

def engine_new__(space, w_subtype, __args__):
    w_anything = __args__.firstarg()
    e = W_Engine(space, w_anything)
    return space.wrap(e)

class W_Engine(W_Root):
    def __init__(self, space, w_anything):
        self.space = space                      # Stash space
        self.engine = e = pcont.Engine()        # We embed an instance of prolog
        self.d_result = None                    # When we have a result, we will stash it here
        e.runstring(space.str_w(w_anything))    # Load the database with the first arg

    def query(self, w_anything):
        query_raw = self.space.str_w(w_anything)
        goals, var_to_pos = self.engine.parse(query_raw)

        cont = UnipycationContinuation(self.engine, var_to_pos, self)
        for g in goals:
            self.engine.run(g, self.engine.modulewrapper.current_module, cont)

        return self.d_result

    def populate_result(self, var_to_pos, heap):
        from prolog.builtin import formatting

        f = formatting.TermFormatter(self.engine, quoted=True, max_depth=20)
        self.d_result = self.space.newdict()
        for var, real_var in var_to_pos.iteritems():
            if var.startswith("_"):
                continue
            value = real_var.dereference(heap)
            val = f.format(value)
            if isinstance(value, pterm.AttVar):
                raise TypeError("XXX: What is an AttVar?")
            else:
                self.space.setitem(self.d_result, self.space.wrap(var), self.space.wrap(val))

    #def descr_getitem(self, space, w_key):
    #    print(type(w_key))
    #    print(type(space.str_w(w_key)))
    #    print("XXX::::")
    #    print(type(self.result["X"]))
    #    return self.result[w_key]
    #    return None

    def print_last_result(self):
        print(self.result)

W_Engine.typedef = TypeDef("Engine",
    __new__ = interp2app(engine_new__),
    #__getitem__ = interp2app(W_Engine.descr_getitem),
    query = interp2app(W_Engine.query),
    print_last_result = interp2app(W_Engine.print_last_result),
)

W_Engine.typedef.acceptable_as_base_class = False
