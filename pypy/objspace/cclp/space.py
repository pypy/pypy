from pypy.rpython.objectmodel import we_are_translated
from pypy.interpreter import baseobjspace, gateway, argument, typedef
from pypy.interpreter.function import Function
from pypy.interpreter.pycode import PyCode

from pypy.interpreter.error import OperationError

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject

from pypy.objspace.cclp.misc import ClonableCoroutine, get_current_cspace, w
from pypy.objspace.cclp.thunk import CSpaceThunk, PropagatorThunk
from pypy.objspace.cclp.global_state import sched
from pypy.objspace.cclp.variable import newvar
from pypy.objspace.cclp.types import ConsistencyError, Solution, W_Var, \
     W_CVar, W_AbstractDomain, W_AbstractDistributor
from pypy.objspace.cclp.interp_var import interp_bind, interp_free
from pypy.objspace.cclp.constraint.distributor import distribute

def newspace(space, w_callable, __args__):
    args = __args__.normalize()
    # coro init
    w_coro = ClonableCoroutine(space)
    #w_callable : a logic or constraint script ????
    thunk = CSpaceThunk(space, w_callable, args, w_coro)
    w_coro.bind(thunk)
    if not we_are_translated():
        w("NEWSPACE, thread", str(id(w_coro)), "for", str(w_callable.name))
    w_space = W_CSpace(space)
    w_coro._cspace = w_space

    sched.uler.add_new_thread(w_coro)
    sched.uler.schedule()

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

class W_CSpace(baseobjspace.Wrappable):

    def __init__(self, space):
        self.space = space # the object space ;-)
        self.distributor = None
        self.threads = []
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

    def clone(self):
        if not we_are_translated():
            # build fresh cspace & distributor thread
            thread = ClonableCoroutine(self.space)
            new_cspace = W_CSpace(self.space)
            thread._cspace = new_cspace
            # new distributor instance
            old_dist = self.distributor
            new_dist = old_dist.__class__(self.space, old_dist._fanout)
            new_dist._cspace = new_cspace
            new_cspace.distributor = new_dist
            # copy the store
            for var in self._store.values():
                new_cspace.register_var(var.copy(self.space))
            # new distributor thunk & thread
            f = Function(self.space,
                         app_fresh_distributor._code,
                         self.space.newdict())
            thunk = CSpaceThunk(self.space, f,
                                argument.Arguments(self.space, [new_dist]),
                                thread)
            thread.bind(thunk)
            sched.uler.add_new_thread(thread)
            # rebuild propagators
            new_cspace._last_choice = self._last_choice
            new_cspace._solution = newvar(self.space)
            # copy solution variables
            self.space.unify(new_cspace._solution,
                             self.space.newlist([var.copy(self.space)
                                                 for var in self._store.values()]))
            # constraints
            for const in self._constraints:
                ccopy = const.copy()
                new_cspace.tell(ccopy)
            sched.uler.wait_stable(new_cspace)
            return new_cspace
        else:
            # need to copy distributor & propagator threads???
            # but, where are we going to find them ?
            raise NotImplementedError
            #new_cspace = W_CSpace(self.space)
            #for th in self.threads:
            #    new_cspace.threads.append(th.clone())

    def w_ask(self):
        sched.uler.wait_stable(self)
        self.space.wait(self._choice)
        choice = self._choice.w_bound_to
        self._choice = newvar(self.space)
        assert isinstance(choice, W_IntObject)
        self._last_choice = self.space.int_w(choice)
        return choice

    def choose(self, n):
        assert n > 1
        sched.uler.wait_stable(self)
        if self._failed: #XXX set by any propagator
            raise ConsistencyError
        assert interp_free(self._choice)
        assert interp_free(self._committed)
        interp_bind(self._choice, self.space.wrap(n))
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
        w_coro = ClonableCoroutine(space)
        w_coro._cspace = self
        thunk = PropagatorThunk(space, w_constraint, w_coro)
        w_coro.bind(thunk)
        if not we_are_translated():
            w("PROPAGATOR in thread", str(id(w_coro)))
            self._constraints.append(w_constraint)
        sched.uler.add_new_thread(w_coro)
        sched.uler.schedule()

    def fail(self):
        self._failed = True
        interp_bind(self._finished, self.space.w_True)
        interp_bind(self._choice, self.space.newint(0))
        self._store = {}

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
    clone = gateway.interp2app(W_CSpace.clone),
    merge = gateway.interp2app(W_CSpace.w_merge))
