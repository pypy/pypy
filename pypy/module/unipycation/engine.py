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
from pypy.module.unipycation import objects

from rpython.rlib.streamio import open_file_as_stream
from rpython.rlib import rstring

class W_SolutionIterator(W_Root):
    """
    An interface that allows retreival of multiple solutions
    """

    def __init__(self, space, w_unbound_vars, w_goal_term, w_engine):
        self.w_engine = w_engine
        self.w_unbound_vars = w_unbound_vars

        w_goal_term = space.interp_w(objects.W_Term, w_goal_term)
        self.w_goal_term = w_goal_term

        self.space = space
        self.d_result = None    # Current result, populated on the fly

        # The state of the prolog interpreter continuation.
        # Used for enumerating results.
        self.fcont = None
        self.heap = None

    def _populate_result(self, w_unbound_vars, fcont, heap):
        """ Called interally by the activation of the continuation """

        for w_var in self.space.listview(w_unbound_vars):
            # it's the equivalent problem
            # we need a test that does this:
            # e.query_iter(term, [1, 2, 3])

            w_var = self.space.interp_w(objects.W_Var, w_var)

            w_binding = conv.w_of_p(self.space, w_var.p_var.dereference(heap))
            self.space.setitem(self.d_result, w_var, w_binding)

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
                    self.w_engine, self.w_unbound_vars, self)
            try:
                r = self.w_engine.engine.run(self.w_goal_term.p_term, cur_mod, cont)
            except perr.UnificationFailed:
                # contradiction - no solutions
                raise OperationError(self.space.w_StopIteration, self.space.w_None)
            except perr.CatchableError:
                w_GoalError = util.get_from_module(self.space, "unipycation", "GoalError")
                raise OperationError(w_GoalError, self.space.wrap("Undefined goal"))

            self.w_goal_term = None # allow GC
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
    def __init__(self, w_engine, w_unbound_vars, w_solution_iter):
        p_engine = w_engine.engine

        pcont.Continuation.__init__(self, p_engine, pcont.DoneSuccessContinuation(p_engine))

        # stash
        self.w_unbound_vars = w_unbound_vars
        self.w_engine = w_engine
        self.w_solution_iter = w_solution_iter

    def activate(self, fcont, heap):
        self.w_solution_iter._populate_result(self.w_unbound_vars, fcont, heap)
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

    @staticmethod
    def from_file(space, w_cls, w_filename):
        filename = space.str0_w(w_filename)

        # have to use rpython io
        hndl = open_file_as_stream(filename)
        prog = db = hndl.readall()
        hndl.close()

        return space.wrap(W_Engine(space, space.wrap(db)))

    def query_iter(self, w_goal_term, w_unbound_vars):
        """ Returns an iterator by which to acquire multiple solutions """
        return W_SolutionIterator(self.space, w_unbound_vars, w_goal_term, self)

    def query_single(self, w_goal_term, w_unbound_vars):
        try:
            return self.query_iter(w_goal_term, w_unbound_vars).next_w()
        except OperationError, e:
            if not e.match(self.space, self.space.w_StopIteration):
                raise
            return self.space.w_None

W_Engine.typedef = TypeDef("Engine",
    __new__ = interp2app(engine_new__),
    from_file = interp2app(W_Engine.from_file, as_classmethod=True),
    query_iter = interp2app(W_Engine.query_iter),
    query_single = interp2app(W_Engine.query_single),
)

W_Engine.typedef.acceptable_as_base_class = False
