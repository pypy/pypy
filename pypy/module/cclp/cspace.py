from pypy.rlib.objectmodel import we_are_translated
from pypy.interpreter import baseobjspace, gateway, argument, typedef
from pypy.interpreter.function import Function
from pypy.interpreter.pycode import PyCode

from pypy.interpreter.error import OperationError

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject

from pypy.module._stackless.interp_coroutine import AbstractThunk

from pypy.module.cclp.misc import get_current_cspace, w
from pypy.module.cclp.thunk import CSpaceThunk, PropagatorThunk
from pypy.module.cclp.global_state import sched
from pypy.module.cclp.variable import newvar
from pypy.module.cclp.types import ConsistencyError, Solution, W_Var, \
     W_CVar, W_AbstractDomain, W_AbstractDistributor, SpaceCoroutine
from pypy.module.cclp.interp_var import interp_bind, interp_free
from pypy.module.cclp.constraint.distributor import distribute
from pypy.module.cclp.scheduler import W_ThreadGroupScheduler
from pypy.module._stackless.clonable import AppClonableCoroutine
from pypy.module._stackless.coroutine import AppCoroutine
from pypy.rlib.rgc import gc_clone




def newspace(space, w_callable, __args__):
    "application level creation of a new computation space"
    args = __args__.normalize()
    dist_thread = SpaceCoroutine(space)
    thunk = CSpaceThunk(space, w_callable, args, dist_thread)
    dist_thread.bind(thunk)
    dist_thread.hello_local_pool()
    try:
        w_space = W_CSpace(space, dist_thread)
    finally:
        dist_thread.goodbye_local_pool()
    if not we_are_translated():
        w("NEWSPACE, (distributor) thread",
          str(id(dist_thread)), "for", str(w_callable.name))
    return w_space
newspace.unwrap_spec=[baseobjspace.ObjSpace,
                      baseobjspace.W_Root,
                      argument.Arguments]

def choose(space, w_n):
    if not isinstance(w_n, W_IntObject):
        raise OperationError(space.w_TypeError,
                             space.wrap('choose only accepts an integer.'))
    n = space.int_w(w_n)
    if n < 2:
        raise OperationError(space.w_ValueError,
                             space.wrap("choose takes an int > 1"))
    # XXX sanity check for 1 <= n <= last_choice
    cspace = get_current_cspace(space)
    if not isinstance(cspace, W_CSpace):
        raise OperationError(space.w_TypeError,
                             space.wrap('choose does not work from within '
                                        'the top-level computatoin space.'))
    if not interp_free(cspace._finished):
        raise OperationError(space.w_RuntimeError,
                             space.wrap("this space is finished"))
    try:
        return cspace.choose(n)
    except ConsistencyError:
        raise OperationError(space.w_ConsistencyError,
                             space.wrap("this space is failed"))
choose.unwrap_spec = [baseobjspace.ObjSpace,
                      baseobjspace.W_Root]

from pypy.module.cclp.constraint import constraint

def tell(space, w_constraint):
    if not isinstance(w_constraint, constraint.W_AbstractConstraint):
        raise OperationError(space.w_TypeError,
                             space.wrap('Tell only accepts object of '
                                        '(sub-)types Constraint.'))
    get_current_cspace(space).tell(w_constraint)
tell.unwrap_spec = [baseobjspace.ObjSpace,
                    baseobjspace.W_Root]


class W_CSpace(W_ThreadGroupScheduler):

    def __init__(self, space, dist_thread):
        W_ThreadGroupScheduler.__init__(self, space)
        dist_thread._cspace = self
        self._init_head(dist_thread)
        self.main_thread = dist_thread
        sched.uler.add_new_group(self)
        self.distributor = None # dist instance != thread
        # choice mgmt
        self._choices = newvar(space)
        self._committed = newvar(space)
        # status, merging
        self._solution = newvar(space)
        self._failed = False
        self._merged = False
        self._finished = newvar(space)
        # constraint store ...
        self._store = {} # name -> var

##     def hello(self):
##         self.main_thread.hello_local_pool()

##     def goodbye(self):
##         self.main_thread.goodbye_local_pool()

    def register_var(self, cvar):
        self._store[cvar.name] = cvar

    def w_clone(self):
        cl_thread = self.main_thread._clone()
        cl_thread._cspace.finalize_cloning( self, cl_thread )
        cl_thread._cspace.main_thread = cl_thread
        sched.uler.add_new_group(cl_thread._cspace)
        return self.space.wrap(cl_thread._cspace)

    def finalize_cloning(self, orig_cspace, cl_thread ):
        # We need to walk all threads references from this cloned
        # space and replace
        # 1. our cloned thread get's a new thread ID
        orig_tid = orig_cspace.main_thread.tid
        sched.uler.register_thread( cl_thread )
        self.main_thread = cl_thread
        # walk the thread ring buffer to replace the cloned threads
        cl_thread._cspace._init_head( cl_thread ) # XXX enough for now with only one thread
        self.replace_thread( orig_tid, cl_thread )

    def report_bad_state_to_applevel(self):
        if not interp_free(self._finished):
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("space is finished"))

    def w_ask(self):
        try:
            self.report_bad_state_to_applevel()
        except: # we're dead, let's avoid wait_stable ...
            return self._choices
        self.wait_stable()
        self.space.wait(self._choices)
        choices = self._choices.w_bound_to
        self.main_thread.hello_local_pool()
        self._choices = newvar(self.space)
        self.main_thread.goodbye_local_pool()
        assert isinstance(choices, W_IntObject)
        self._last_choice = self.space.int_w(choices)
        return choices

    def choose(self, n):
        # solver probably asks
        self.wait_stable()
        if self._failed: #XXX set by any propagator while we were not looking
            raise ConsistencyError
        assert interp_free(self._choices) 
        assert interp_free(self._committed)
        # XXX we wrap it a bit prematurely, so as to satisfy
        # type requirements (logic variables do not support rpython types)
        interp_bind(self._choices, self.space.wrap(n)) # unblock the solver
        # now we wait on a solver commit
        self.space.wait(self._committed)
        committed = self._committed.w_bound_to
        self._committed = newvar(self.space)
        return committed

    def w_commit(self, w_n):
        self.report_bad_state_to_applevel()
        assert isinstance(w_n, W_IntObject)
        n = w_n.intval
        assert interp_free(self._committed)
        if n < 1 or n > self._last_choice:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap("need 0<commit<=%d" % self._last_choice))
        interp_bind(self._committed, w_n)

    def tell(self, w_constraint):
        space = self.space
        w_coro = AppCoroutine(space)
        w_coro._next = w_coro._prev = w_coro
        w_coro._cspace = self
        thunk = PropagatorThunk(space, w_constraint, w_coro)
        w_coro.bind(thunk)
        self.add_new_thread(w_coro)

    def fail(self):
        self._failed = True
        space = self.space
        interp_bind(self._finished, space.w_True)
        interp_bind(self._choices, space.wrap(0))

    def w_fail(self):
        self.fail()

    def is_failed(self):
        return self._failed

    def w_merge(self):
        # let's bind the solution variables
        if self._merged:
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("space is already merged"))
        self._merged = True
        sol = self._solution.w_bound_to
        if isinstance(sol, W_ListObject):
            self._bind_solution_variables(sol.wrappeditems)
        elif isinstance(sol, W_TupleObject):
            self._bind_solution_variables(sol.wrappeditems)
        return self._solution

    def __ne__(self, other):
        if other is self:
            return False
        return True

    def _bind_solution_variables(self, solution):
        if contains_cvar(solution): # was a constraint script
            for var in solution:
                assert isinstance(var, W_CVar)
                realvar = self._store[var.name]
                dom = realvar.w_dom
                assert isinstance(dom, W_AbstractDomain)
                assert dom.size() == 1
                interp_bind(var, dom.get_values()[0])


def contains_cvar(lst):
    return isinstance(lst[0], W_CVar)


W_CSpace.typedef = typedef.TypeDef("W_CSpace",
    ask = gateway.interp2app(W_CSpace.w_ask),
    commit = gateway.interp2app(W_CSpace.w_commit),
    clone = gateway.interp2app(W_CSpace.w_clone),
    merge = gateway.interp2app(W_CSpace.w_merge),
    fail = gateway.interp2app(W_CSpace.w_fail))
