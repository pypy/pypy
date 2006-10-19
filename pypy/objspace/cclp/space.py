from pypy.rpython.objectmodel import we_are_translated
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
     W_CVar, W_AbstractDomain, W_AbstractDistributor
from pypy.objspace.cclp.interp_var import interp_bind, interp_free
from pypy.objspace.cclp.constraint.distributor import distribute
from pypy.objspace.cclp.scheduler import W_ThreadGroupScheduler

from pypy.rpython.rgc import gc_swap_pool, gc_clone

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
    assert isinstance(w_n, W_IntObject)
    n = space.int_w(w_n)
    cspace = get_current_cspace(space)
    if cspace is not None:
        assert isinstance(cspace, W_CSpace)
        try:
            return cspace.choose(w_n.intval)
        except ConsistencyError:
            raise OperationError(space.w_ConsistencyError,
                                 space.wrap("the space is failed"))
    raise OperationError(space.w_RuntimeError,
                         space.wrap("choose is forbidden from the top-level space"))
app_choose = gateway.interp2app(choose)


from pypy.objspace.cclp.constraint import constraint

def tell(space, w_constraint):
    assert isinstance(w_constraint, constraint.W_AbstractConstraint)
    get_current_cspace(space).tell(w_constraint)
app_tell = gateway.interp2app(tell)

if not we_are_translated():
    def fresh_distributor(space, w_dist):
        cspace = w_dist._cspace
        while w_dist.distributable():
            choice = cspace.choose(w_dist.fanout())
            w_dist.w_distribute(choice)
    app_fresh_distributor = gateway.interp2app(fresh_distributor)


class W_CSpace(W_ThreadGroupScheduler):
    local_pool = None

    def __init__(self, space, dist_thread):
        W_ThreadGroupScheduler.__init__(self, space)
        dist_thread._cspace = self
        self._init_head(dist_thread)
        self._next = self._prev = self
        sched.uler.add_new_group(self)

        self.distributor = None # dist instance != thread
        self._container = None # thread that 'contains' us
        # choice mgmt
        self._choice = newvar(space)
        self._committed = newvar(space)
        # status, merging
        self._solution = newvar(space)
        self._finished = newvar(space)
        self._failed = False
        # constraint store ...
        self._store = {} # name -> var
        if not we_are_translated():
            self._constraints = []
        
    def register_var(self, cvar):
        self._store[cvar.name] = cvar

    def w_clone(self):
        if we_are_translated():
            w("<> cloning the space")
            if self.local_pool is None:
                self.local_pool = gc_swap_pool(gc_swap_pool(None))
            new_cspace, new_cspace.local_pool = gc_clone(self, self.local_pool)
            w("<> add cloned cspace to new group")
            assert isinstance(new_cspace, W_CSpace)
            new_cspace._next = new_cspace._prev = new_cspace
            sched.uler.add_new_group(new_cspace)
            w("<> returning clone ")
            return new_cspace
        else:
            raise NotImplementedError


    def w_ask(self):
        self.wait_stable()
        self.space.wait(self._choice)
        choice = self._choice.w_bound_to
        self._choice = newvar(self.space)
        assert isinstance(choice, W_IntObject)
        self._last_choice = self.space.int_w(choice)
        return choice

    def choose(self, n):
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
        if not we_are_translated():
            w("PROPAGATOR in thread", str(id(w_coro)))
            self._constraints.append(w_constraint)
        self.add_new_thread(w_coro)

    def fail(self):
        self._failed = True
        interp_bind(self._finished, self.space.w_True)
        interp_bind(self._choice, self.space.newint(0))

    def is_failed(self):
        return self._failed

    def w_merge(self):
        # let's bind the solution variables
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
    for elt in lst:
        if isinstance(elt, W_CVar):
            return True
    return False


W_CSpace.typedef = typedef.TypeDef("W_CSpace",
    ask = gateway.interp2app(W_CSpace.w_ask),
    commit = gateway.interp2app(W_CSpace.w_commit),
    clone = gateway.interp2app(W_CSpace.w_clone),
    merge = gateway.interp2app(W_CSpace.w_merge))
