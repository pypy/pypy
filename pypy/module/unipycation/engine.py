from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError

import prolog.interpreter.continuation as pcont
import prolog.interpreter.term as pterm
import prolog.interpreter.error as perr
import prolog.interpreter.parsing as ppars
import pypy.module.unipycation.conversion as conv
import pypy.module.unipycation.util as util

class W_SolutionIterator(W_Root):
    """
    An interface that allows retreival of multiple solutions
    """

    def __init__(self, space, var_to_pos, goals, w_engine):
        # Stash some prolog structures
        self.w_engine = w_engine

        self.var_to_pos = var_to_pos
        if len(goals) != 1:
            w_GoalError = util.get_from_module(space, "unipycation", "GoalError")
            raise OperationError(w_GoalError, space.wrap("Please pass a single query"))

        self.goal = goals[0]

        self.space = space
        self.d_result = None    # Current result, populated on the fly

        # The state of the continuation (for enumerating results)
        self.fcont = None
        self.heap = None

    def _populate_result(self, var_to_pos, fcont, heap):
        """ Called interally by the activation of the continuation """

        for var, real_var in var_to_pos.iteritems():
            if var.startswith("_"): continue

            w_var = self.space.wrap(var)
            w_val = conv.w_of_p(self.space, real_var.dereference(heap))
            self.space.setitem(self.d_result, w_var, w_val)

        self.fcont = fcont
        self.heap = heap

    def iter_w(self): return self

    def next_w(self):
        """ Obtain the next solution (if there is one) """

        self.d_result = self.space.newdict()

        # The first iteration is special. Here we set up the continuation
        # for subsequent iterations.
        if self.fcont is None:
            cur_mod = self.w_engine.engine.modulewrapper.current_module
            cont = UnipycationContinuation(
                    self.w_engine, self.var_to_pos, self)
            try:
                r = self.w_engine.engine.run(self.goal, cur_mod, cont)
            except perr.UnificationFailed:
                # contradiction - no solutions
                raise OperationError(self.space.w_StopIteration, self.space.w_None)
            except perr.CatchableError:
                w_GoalError = util.get_from_module(self.space, "unipycation", "GoalError")
                raise OperationError(w_GoalError, self.space.wrap("Undefined goal"))

            self.goal = None # allow GC
        else:
            try:
                pcont.driver(*self.fcont.fail(self.heap))
            except perr.UnificationFailed:
                # enumerated all solutions
                raise OperationError(self.space.w_StopIteration, self.space.w_None)
            except perr.CatchableError:
                w_GoalError = util.get_from_module(self.space, "unipycation", "GoalError")
                raise OperationError(w_GoalError, self.space.wrap("Undefined goal"))

        return self.d_result

W_SolutionIterator.typedef = TypeDef("SolutionIterator",
    __iter__ = interp2app(W_SolutionIterator.iter_w),
    next = interp2app(W_SolutionIterator.next_w),
)

W_SolutionIterator.typedef.acceptable_as_base_class = False

# ---

class UnipycationContinuation(pcont.Continuation):
    def __init__(self, w_engine, var_to_pos, w_solution_iter):
        engine = w_engine.engine

        pcont.Continuation.__init__(self, engine, pcont.DoneSuccessContinuation(engine))

        # stash
        self.var_to_pos = var_to_pos
        self.w_engine = w_engine
        self.w_solution_iter = w_solution_iter

    def activate(self, fcont, heap):
        self.w_solution_iter._populate_result(self.var_to_pos, fcont, heap)
        return pcont.DoneSuccessContinuation(self.engine), fcont, heap

# ---

def engine_new__(space, w_subtype, __args__):
    w_anything = __args__.firstarg()
    e = W_Engine(space, w_anything)
    return space.wrap(e)

class W_Engine(W_Root):
    def __init__(self, space, w_anything):
        self.space = space                      # Stash space
        self.engine = e = pcont.Engine()        # We embed an instance of prolog
        self.d_result = None                    # When we have a result, we will stash it here

        try:
            e.runstring(space.str_w(w_anything))    # Load the database with the first arg
        except ppars.ParseError as e:
            w_ParseError = util.get_from_module(self.space, "unipycation", "ParseError")
            raise OperationError(w_ParseError, self.space.wrap(e.nice_error_message()))

    def query(self, w_query_str):
        """ Returns an iterator by which to acquire multiple solutions """
        query_raw = self.space.str_w(w_query_str)

        try:
            goals, var_to_pos = self.engine.parse(query_raw)
        except ppars.ParseError as e:
            w_ParseError = util.get_from_module(self.space, "unipycation", "ParseError")
            raise OperationError(w_ParseError, self.space.wrap(e.nice_error_message()))

        w_solution_iter = W_SolutionIterator(self.space, var_to_pos, goals, self)

        return w_solution_iter

    def query_single(self, w_query_str):
        return self.query(w_query_str).next_w()

W_Engine.typedef = TypeDef("Engine",
    __new__ = interp2app(engine_new__),
    query = interp2app(W_Engine.query),
    query_single = interp2app(W_Engine.query_single),
)

W_Engine.typedef.acceptable_as_base_class = False
