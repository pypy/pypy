from pypy.rlib.objectmodel import we_are_translated
from pypy.interpreter import baseobjspace, gateway, argument, typedef
from pypy.interpreter.function import Function
from pypy.interpreter.pycode import PyCode

from pypy.interpreter.error import OperationError

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject

from pypy.module._stackless.interp_coroutine import AbstractThunk

from pypy.objspace.cclp.misc import AppCoroutine, get_current_cspace, w
from pypy.objspace.cclp.thunk import CSpaceThunk, PropagatorThunk
from pypy.objspace.cclp.global_state import sched
from pypy.objspace.cclp.variable import newvar
from pypy.objspace.cclp.types import ConsistencyError, Solution, W_Var, \
     W_CVar, W_AbstractDomain, W_AbstractDistributor, Pool
from pypy.objspace.cclp.interp_var import interp_bind, interp_free
from pypy.objspace.cclp.constraint.distributor import distribute
from pypy.objspace.cclp.scheduler import W_ThreadGroupScheduler

def newspace(space, w_callable, __args__):
    "application level creation of a new computation space"
    args = __args__.normalize()
    dist_thread = AppCoroutine(space)
    dist_thread._next = dist_thread._prev = dist_thread
    thunk = CSpaceThunk(space, w_callable, args, dist_thread)
    dist_thread.bind(thunk)
    if not we_are_translated():
        w("NEWSPACE, (distributor) thread", str(id(dist_thread)), "for", str(w_callable.name))
    w_space = W_CSpace(space, dist_thread)
    return w_space
app_newspace = gateway.interp2app(newspace, unwrap_spec=[baseobjspace.ObjSpace,
                                                         baseobjspace.W_Root,
                                                         argument.Arguments])


def choose(space, w_n):
    if not isinstance(w_n, W_IntObject):
        raise OperationError(space.w_TypeError,
                             space.wrap('Choose only accepts an integer.'))
    n = space.int_w(w_n)
    # XXX sanity check for 1 <= n <= last_choice
    cspace = get_current_cspace(space)
    if not isinstance(cspace, W_CSpace):
        raise OperationError(space.w_TypeError,
                             space.wrap('Choose does not work from within '
                                        'the top-level computatoin space.'))
    try:
        return cspace.choose(n)
    except ConsistencyError:
        raise OperationError(space.w_ConsistencyError,
                             space.wrap("the space is failed"))
app_choose = gateway.interp2app(choose)

from pypy.objspace.cclp.constraint import constraint

def tell(space, w_constraint):
    if not isinstance(w_constraint, constraint.W_AbstractConstraint):
        raise OperationError(space.w_TypeError,
                             space.wrap('Tell only accepts object of '
                                        '(sub-)types Constraint.'))
    get_current_cspace(space).tell(w_constraint)
app_tell = gateway.interp2app(tell)


class W_CSpace(W_ThreadGroupScheduler):

    def __init__(self, space, dist_thread):
        W_ThreadGroupScheduler.__init__(self, space)
        dist_thread._cspace = self
        self._init_head(dist_thread)
        self._next = self._prev = self
        self._pool = Pool(self)
        sched.uler.add_new_group(self)
        self.distributor = None # dist instance != thread
        # choice mgmt
        self._choice = newvar(space)
        self._committed = newvar(space)
        # status, merging
        self._solution = newvar(space)
        self._failed = False
        self._merged = False
        self._finished = newvar(space)
        # constraint store ...
        self._store = {} # name -> var
        
    def register_var(self, cvar):
        self._store[cvar.name] = cvar

    def w_clone(self):
        clone = self._pool.clone()
        return self.space.wrap(clone.cspace)

    def w_ask(self):
        if not interp_free(self._finished):
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("space is finished"))
        self.wait_stable()
        self.space.wait(self._choice)
        choice = self._choice.w_bound_to
        self._choice = newvar(self.space)
        assert isinstance(choice, W_IntObject)
        self._last_choice = self.space.int_w(choice)
        return choice

    def choose(self, n):
        if not interp_free(self._finished):
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("space is finished"))
        # solver probably asks
        assert n > 1
        self.wait_stable()
        if self._failed: #XXX set by any propagator
            raise ConsistencyError
        assert interp_free(self._choice) 
        assert interp_free(self._committed)
        interp_bind(self._choice, self.space.wrap(n)) # unblock the solver
        # now we wait on a solver commit
        self.space.wait(self._committed)
        committed = self._committed.w_bound_to
        self._committed = newvar(self.space)
        return committed

    def w_commit(self, w_n):
        if not interp_free(self._finished):
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("space is finished"))
        assert isinstance(w_n, W_IntObject)
        n = w_n.intval
        assert interp_free(self._committed)
        assert n > 0
        assert n <= self._last_choice
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
        interp_bind(self._finished, self.space.w_True)
        interp_bind(self._choice, self.space.newint(0))

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
    merge = gateway.interp2app(W_CSpace.w_merge))
