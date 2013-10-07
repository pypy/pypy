from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError

from prolog.interpreter import continuation
from prolog.interpreter import error
from prolog.interpreter import parsing
from prolog.interpreter import term
from prolog.interpreter import helper
from prolog.interpreter.signature import Signature

import pypy.module.unipycation.util as util
from pypy.module.unipycation import objects, conversion

from rpython.rlib.streamio import open_file_as_stream
from rpython.rlib import rstring, jit

UNROLL_SIZE = 10

@jit.look_inside_iff(lambda space, list_w, unroll: unroll)
def _typecheck_list_of_vars(space, list_w, unroll):
    return [space.interp_w(objects.W_Var, w_var)
                for w_var in list_w]

colonsignature = Signature.getsignature(":", 2)

class ContinuationHolder(object):
    def __init__(self):
        # The state of the prolog interpreter continuation.
        # Used for enumerating results.
        self.fcont = None
        self.heap = None

    def _store_fcont_heap(self, fcont, heap):
        self.fcont = fcont
        self.heap = heap


class W_CoreSolutionIterator(W_Root):
    """
    An interface that allows retrieval of multiple solutions
    """

    def __init__(self, space, w_unbound_vars, w_goal_term, w_engine):
        self.w_engine = w_engine
        self.w_unbound_vars = w_unbound_vars

        list_w = space.listview(w_unbound_vars)
        unroll = jit.isconstant(len(list_w)) or len(list_w) < UNROLL_SIZE
        self.unroll_result_creation = unroll
        self.unbound_vars_w = _typecheck_list_of_vars(space, list_w, unroll)

        w_goal_term = space.interp_w(objects.W_Term, w_goal_term)
        self.w_goal_term = w_goal_term

        self.space = space

        self.continuation_holder = ContinuationHolder()

    @jit.look_inside_iff(lambda self: self.unroll_result_creation)
    def _create_result(self):
        """ Called internally after the activation of the continuation """
        values_w = [conversion.w_of_p(self.space, w_var.p_var.dereference(None))
                        for w_var in self.unbound_vars_w]
        return W_Solution(self.space, self.unbound_vars_w, values_w)

    def iter_w(self): return self

    def next_w(self):
        """ Obtain the next solution (if there is one) """

        p_goal_term = cont = None

        first_iteration = self.continuation_holder.fcont is None
        if first_iteration:
            # The first iteration is special. Here we set up the continuation
            # for subsequent iterations.
            cont = UnipycationContinuation(
                    self.w_engine, self.continuation_holder)
            p_goal_term = self.w_goal_term.p_term
            self.w_goal_term = None # allow GC
        try:
            if first_iteration:
                r = self.w_engine.engine.run_query_in_current(p_goal_term, cont)
            else:
                fcont = self.continuation_holder.fcont
                heap = self.continuation_holder.heap
                continuation.driver(*fcont.fail(heap))
        except error.UnificationFailed:
            # contradiction - no solutions
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        except (error.CatchableError, error.UncaughtError) as ex:
            w_PrologError = util.get_from_module(self.space, "unipycation", "PrologError")
            w_term = conversion.w_of_p(self.space, ex.term)
            engine = self.w_engine.engine
            w_str = self.space.wrap(ex.get_errstr(engine))
            w_ex = self.space.call_function(w_PrologError, w_str, w_term)
            raise OperationError(w_PrologError, w_ex)

        return self._create_result()

W_CoreSolutionIterator.typedef = TypeDef("CoreSolutionIterator",
    __iter__ = interp2app(W_CoreSolutionIterator.iter_w),
    next = interp2app(W_CoreSolutionIterator.next_w),
)

W_CoreSolutionIterator.typedef.acceptable_as_base_class = False

# ---

class UnipycationContinuation(continuation.Continuation):
    def __init__(self, w_engine, continuation_holder):
        p_engine = w_engine.engine

        continuation.Continuation.__init__(self,
                p_engine, continuation.DoneSuccessContinuation(p_engine))

        # stash
        self.w_engine = w_engine
        self.continuation_holder = continuation_holder

    def activate(self, fcont, heap):
        self.continuation_holder._store_fcont_heap(fcont, heap)
        return continuation.DoneSuccessContinuation(self.engine), fcont, heap

# ---

class W_Solution(W_Root):
    def __init__(self, space, unbound_vars_w, values_w):
        self.space = space
        self.unbound_vars_w = unbound_vars_w
        self.values_w = values_w
        assert len(unbound_vars_w) == len(values_w)
        self.w_dict = None

    def _create_dict(self):
        if self.w_dict is None:
            self.w_dict = self.space.newdict()
            for i, w_var in enumerate(self.unbound_vars_w):
                self.space.setitem(self.w_dict, w_var, self.values_w[i])

    def descr_length(self):
        return self.space.wrap(len(self.unbound_vars_w))

    def descr_getitem(self, w_key):
        self._create_dict()
        return self.space.getitem(self.w_dict, w_key)

    def get_values_in_order(self):
        return self.space.newtuple(self.values_w)

W_Solution.typedef = TypeDef("Solution",
    __getitem__ = interp2app(W_Solution.descr_getitem),
    __len__ = interp2app(W_Solution.descr_length),
    get_values_in_order = interp2app(W_Solution.get_values_in_order),
)

W_Solution.typedef.acceptable_as_base_class = False


# ---

@unwrap_spec(prolog_code=str)
def engine_new__(space, w_subtype, prolog_code, w_namespace=None):
    e = space.allocate_instance(W_CoreEngine, w_subtype)
    W_CoreEngine.__init__(e, space, prolog_code, w_namespace)
    return space.wrap(e)

class W_CoreEngine(W_Root):

    _immutable_fields_ = ["engine"]

    def __init__(self, space, prolog_code, w_python_namespace=None):
        self.space = space                      # Stash space
        self.engine = e = continuation.Engine(load_system=True) # We embed an instance of prolog
        e.modulewrapper.python_engine = self
        self.w_python_namespace = w_python_namespace

        try:
            e.runstring(prolog_code)# Load the database with the first arg
        except error.PrologParseError as e:
            w_ParseError = util.get_from_module(self.space, "unipycation", "ParseError")
            raise OperationError(w_ParseError, self.space.wrap(e.message))

    @staticmethod
    def from_file(space, w_cls, w_filename):
        filename = space.str0_w(w_filename)

        # have to use rpython io
        hndl = open_file_as_stream(filename)
        db = hndl.readall()
        hndl.close()

        return space.call_function(w_cls, space.wrap(db))

    def query_iter(self, w_goal_term, w_unbound_vars):
        """ Returns an iterator by which to acquire multiple solutions """
        return W_CoreSolutionIterator(self.space, w_unbound_vars, w_goal_term, self)

    def query_single(self, w_goal_term, w_unbound_vars):
        try:
            return self.query_iter(w_goal_term, w_unbound_vars).next_w()
        except OperationError, e:
            if not e.match(self.space, self.space.w_StopIteration):
                raise
            return self.space.w_None

    @jit.unroll_safe
    def python_call_from_prolog(self, p_term, scont, fcont, heap):
        space = self.space
        if self.w_python_namespace is None:
            raise OperationError(
                    space.w_TypeError,
                    space.wrap("no python namespace given in CoreEngine constructor"))
        names_w, p_term = self._unwrap_name_chain(p_term)
        args_w, returnarg = self._prepare_python_call_args(p_term)
        try:
            w_obj = space.getitem(self.w_python_namespace, names_w[0])
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
            # try builtins
            w_obj = space.findattr(space.builtin, names_w[0])
            if w_obj is None:
                w_obj = space.findattr(space.getbuiltinmodule('operator'), names_w[0])
                if w_obj is None:
                    raise

        for i in range(1, len(names_w)):
            w_name = names_w[i]
            w_obj = space.getattr(w_obj, w_name)
        w_res = space.call(w_obj, space.newlist(args_w))
        return self._return_python_result(w_res, returnarg, scont, fcont, heap)

    @jit.unroll_safe
    def python_method_call_from_prolog(self, p_obj, p_term, scont, fcont, heap):
        space = self.space
        w_obj = conversion.w_of_p(space, p_obj)
        names_w, p_term = self._unwrap_name_chain(p_term)
        args_w, returnarg = self._prepare_python_call_args(p_term)
        for w_name in names_w:
            w_obj = space.getattr(w_obj, w_name)
        w_res = space.call(w_obj, space.newlist(args_w))
        return self._return_python_result(w_res, returnarg, scont, fcont, heap)

    @jit.unroll_safe
    def _prepare_python_call_args(self, p_term):
        space = self.space
        numargs = p_term.argument_count()
        if numargs == 0:
            raise OperationError(
                    space.w_TypeError,
                    space.wrap("at least one argument (return value) is required"))
        returnarg = p_term.argument_at(numargs - 1)
        args_w = [conversion.w_of_p(space, p_term.argument_at(i))
                    for i in range(numargs - 1)]
        return args_w, returnarg

    @jit.unroll_safe
    def _unwrap_name_chain(self, p_term):
        space = self.space
        result_w = []
        while p_term.signature().eq(colonsignature):
            name = helper.unwrap_atom(p_term.argument_at(0))
            result_w.append(space.wrap(name))
            p_term = p_term.argument_at(1)
        result_w.append(space.wrap(p_term.name()))
        return result_w, p_term

    def _return_python_result(self, w_res, returnarg, scont, fcont, heap):
        space = self.space
        if space.findattr(w_res, space.wrap("next")) is not None:
            # many solutions
            return continue_python_iter(
                self.engine, scont, fcont, heap, returnarg, space, w_res)
        returnarg.unify(conversion.p_of_w(space, w_res), heap)
        return scont, fcont, heap

@continuation.make_failure_continuation
def continue_python_iter(Choice, engine, scont, fcont, heap, resultvar, space, w_iter):
    try:
        w_res = _call_next_maybe_hidden(space, w_iter)
    except OperationError, e:
        if not e.match(space, space.w_StopIteration):
            raise
        return fcont.fail(heap) # no more solutions
    fcont = Choice(engine, scont, fcont, heap, resultvar, space, w_iter)
    heap = heap.branch()
    try:
        resultvar.unify(conversion.p_of_w(space, w_res), heap)
    except error.UnificationFailed:
        return fcont.fail(heap)
    return scont, fcont, heap

def _call_next_maybe_hidden(space, w_iter):
    from pypy.interpreter import generator
    if isinstance(w_iter, generator.GeneratorIterator):
        # GeneratorIterator triggers weird JIT behaviour, hide it for now
        return _call_next_hidden(space, w_iter)
    else:
        return space.next(w_iter)

@jit.dont_look_inside
def _call_next_hidden(space, w_iter):
    return w_iter.descr_next()


W_CoreEngine.typedef = TypeDef("CoreEngine",
    __new__ = interp2app(engine_new__),
    from_file = interp2app(W_CoreEngine.from_file, as_classmethod=True),
    query_iter = interp2app(W_CoreEngine.query_iter),
    query_single = interp2app(W_CoreEngine.query_single),
)

