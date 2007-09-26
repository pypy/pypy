from pypy.rlib.objectmodel import we_are_translated
from pypy.interpreter import baseobjspace, gateway, argument, typedef

from pypy.interpreter.error import OperationError

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.module.cclp.misc import get_current_cspace, w, v
from pypy.module.cclp.thunk import CSpaceThunk, PropagatorThunk
from pypy.module.cclp.global_state import sched
from pypy.module.cclp.variable import newvar
from pypy.module.cclp.types import FailedSpace, ConsistencyError, W_Var, W_CVar
from pypy.module.cclp.interp_var import interp_bind, interp_free
from pypy.module.cclp.scheduler import W_ThreadGroupScheduler
from pypy.module._cslib import fd
from pypy.rlib.cslib import rdistributor as rd

from pypy.module._stackless.interp_coroutine import AppCoroutine

import pypy.rlib.rgc as rgc

def gc_swap_pool(pool):
    if we_are_translated():
        return rgc.gc_swap_pool(pool)

def gc_clone(data, pool):
    if we_are_translated():
        return rgc.gc_clone(data, pool)
        
def newspace(space, w_callable, __args__):
    "application level creation of a new computation space"
    args = __args__.normalize()
    # allocate in a new pool
    saved_pool = gc_swap_pool(None)
    dist_thread = AppCoroutine(space)
    thunk = CSpaceThunk(space, w_callable, args, dist_thread)
    dist_thread.bind(thunk)
    w_space = W_CSpace(space, dist_thread, saved_pool)
    w_space.goodbye_local_pool()
    # /allocate
    if not we_are_translated():
        w("NEWSPACE, (distributor) thread %d for %s" %
          ( id(dist_thread), str(w_callable.name) ) )
    return w_space

newspace.unwrap_spec=[baseobjspace.ObjSpace,
                      baseobjspace.W_Root,
                      argument.Arguments]


def dorkspace(space, w_callable, __args__):
    "application level creation of a new complicated computation space"
    args = __args__.normalize()
    dist_thread = AppCoroutine(space)
    thunk = CSpaceThunk(space, w_callable, args, dist_thread)
    dist_thread.bind(thunk)

    saved_pool = gc_swap_pool(None)
    try:
        w_space = W_ComplicatedSpace(space, dist_thread, saved_pool)
        w_space.goodbye_local_pool()
    except:
        gc_swap_pool(saved_pool)
        raise OperationError(space.w_RuntimeError,
                             space.wrap("Unknown error in newspace"))
    if not we_are_translated():
        w("NEWSPACE, (distributor) thread %d for %s" %
          ( id(dist_thread), str(w_callable.name) ) )
    return w_space

dorkspace.unwrap_spec=[baseobjspace.ObjSpace,
                       baseobjspace.W_Root,
                       argument.Arguments]


def choose(space, w_n):
    "non deterministic choice from within a c.space"
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
    except Exception, e:
        if not we_are_translated():
            import traceback
            traceback.print_exc()
        w('whack whack whack')
        raise OperationError(space.w_RuntimeError,
                             space.wrap("something wacky happened %s" % e))
choose.unwrap_spec = [baseobjspace.ObjSpace,
                      baseobjspace.W_Root]

from pypy.module._cslib.constraint import W_AbstractConstraint

def tell(space, w_constraint):
    "adding a constraint to a c.space (from within)"
    if not isinstance(w_constraint, W_AbstractConstraint):
        raise OperationError(space.w_TypeError,
                             space.wrap('Tell only accepts object of '
                                        '(sub-)types Constraint.'))
    get_current_cspace(space).tell(w_constraint.constraint)
tell.unwrap_spec = [baseobjspace.ObjSpace,
                    baseobjspace.W_Root]


def distribute(space, w_strategy):
    assert isinstance(w_strategy, W_StringObject)
    strat = space.str_w(w_strategy)
    cspace = get_current_cspace(space)
    # constraint distributor thread main loop
    cspace.distribute(strat)
distribute.unwrap_spec = [baseobjspace.ObjSpace,
                          baseobjspace.W_Root]


# base space
# non concurrent propagators
# hence much less weird synchronization stuff
# a specific pool object
# XXX maybe use a descr_method__new__ to create the pool before allocation
class W_CSpace(W_ThreadGroupScheduler):
    local_pool = None

    def dump(self):
        w('-- DUMPing C.Space data --')
        w(':local pool %s' % id(self.local_pool))
        w(':saved pool %s' % id(self.saved_pool))
        v(':threads :')
        curr = stop = self._head
        while 1:
            v('%s ' % id(curr))
            curr = curr._next
            if curr == stop:
                break
        w('')
        v(':blocked :')
        for th in self._blocked.keys():
            v('%s ' % id(th))
        w('')
        w(':blocked_on')
        for var, thl in self._blocked_on.items():
            v('  var %s : ' % id(var))
            for th in thl:
                v('%s ' % id(th))
            w('')
        w(':blocked_byneed')
        for var, thl in self._blocked_byneed.items():
            v('  var %s : ' % id(var))
            for th in thl:
                v('%s ' % id(th))
            w('')
        w(':traced vars')
        for th, varl in self._traced.items():
            v('  thread %s : ' % id(th))
            for var in varl:
                v('%s ' % id(var))
            w('')
        w('-- /DUMP --')
    
    def __init__(self, space, dist_thread, saved_pool):
        W_ThreadGroupScheduler.__init__(self, space)
        # pool
        self.local_pool = None
        self.saved_pool = saved_pool
        # /pool
        # thread ring
        dist_thread._cspace = self
        self._init_head(dist_thread)
        # /ring
        sched.uler.add_new_group(self)
        # choice mgmt
        self._choices = newvar(space)
        self._committed = newvar(space)
        # status, merging
        self._solution = newvar(space)
        self._failed = False
        self._merged = False
        self._finished = newvar(space)
        # constraint store ...
        self._constraints = []
        self._domains = {} # varname -> domain
        self._variables = [] # varnames
        self._varconst = {} # varname -> constraints
        self._cqueue = [] # constraint queue to be processed 

    #-- POOL & cloning stuff

    def hello_local_pool(self):
        if we_are_translated():
            self.saved_pool = gc_swap_pool(self.local_pool)

    def goodbye_local_pool(self):
        if we_are_translated():
            self.local_pool = gc_swap_pool(self.saved_pool)
            self.saved_pool = None

    def w_clone(self):
        # all this stuff is created in the local pool so that
        # gc_clone can clone it. every object we want to clone
        # must be reachable through objects allocated in this
        # local pool via the data tuple.
        self.report_bad_condition_to_applevel()
        head = curr = self._head
        new_shells = []
        # within new POOL
        self.hello_local_pool()
        coroutines_to_clone = []
        while 1:
            coroutines_to_clone.append((curr, curr.frame, curr.subctx))
            self.goodbye_local_pool()
            # outside new POOL, build new fresh coro shells
            new = AppCoroutine(self.space, state = curr.costate)
            new.parent = curr.parent
            new_shells.append(new)
            self.hello_local_pool()
            # /outside
            curr = curr._next
            if curr == head:
                break
        data = (self, coroutines_to_clone)
        # /within new POOL
        self.goodbye_local_pool()
        
        (copy, copied_coros), copypool = gc_clone(data, self.local_pool)
        copy.local_pool = copypool
        copy.finalize_cloning(copied_coros, new_shells)
        sched.uler.add_new_group(copy)
        self.dump()
        copy.dump()
        return self.space.wrap(copy)

    def finalize_cloning(self, copied_coros, new_shells):
        # We need to walk all threads references from this cloned
        # space and replace
        # 1. our cloned thread gets a new thread ID
        w('finalize cloning in c.space %s' % id(self))
        self._head = None
        for i in range(len(copied_coros)):
            coro, cloned_frame, cloned_subctx = copied_coros[i]
            # bolt cloned stuff on new coro shells
            cloned_coro = new_shells[i]
            cloned_coro.frame = cloned_frame
            cloned_coro.subctx = cloned_subctx
            cloned_coro._cspace = self
            cloned_coro.thunk = coro.thunk
            self.replace_thread(coro, cloned_coro)

    def replace_thread(self, old, new):
        # walk the list of _blocked threads:
        if old in self._blocked.keys():
            w('blocked : %s replaced %s' % (id(new), id(old)))
            del self._blocked[old]
            self._blocked[new] = True

        # walk the mappings var->threads
        for w_var in self._blocked_on:
            threads = self._blocked_on[w_var]
            for k in range(len(threads)):
                if threads[k] is old:
                    w('blocked_on : %s replaced %s' % (id(new), id(old)))
                    threads[k] = new
                    
        for w_var in self._blocked_byneed:
            threads = self._blocked_byneed[w_var]
            for k in range(len(threads)):
                if threads[k] is old:
                    w('blocked_byneed : %s replaced %s' % (id(new), id(old)))
                    threads[k] = new

        # handled traced thread
        for th in self._traced.keys():
            if th is old:
                lvars = self._traced[th]
                del self._traced[th]
                self._traced[new] = lvars

        # insert the thread in the linked list
        if self._head is None:
            w('head was initialized with %s' % id(new))
            self._head = new._next = new._prev = new
        else:
            w('%s was inserted in the runqueue' % id(new))
            r = self._head
            l = r._prev
            l._next = new
            r._prev = new
            new._prev = l
            new._next = r
            assert new._next is not new
            assert new._prev is not new

    def _newvar(self):
        """
        ensure a new space-local variable is allocated
        in the right space/pool
        """
        self.hello_local_pool()
        var = newvar(self.space)
        self.goodbye_local_pool()
        return var

    #-- / POOL 

    def register_var(self, cvar):
        name = cvar.name
        dom = cvar.w_dom.domain
        self._domains[name] = dom
        self._varconst[name] = []

    def tell(self, rconst):
        w('telling %s' % rconst)
        self._constraints.append(rconst)
        for var in rconst._variables:
            self._varconst[var].append(rconst)

    def untell(self, constraint):
        "entailed constraint are allowed to go away"
        self._constraints.remove(constraint)
        for var in constraint._variables:
            self._varconst[var].remove(constraint)

    def distributable(self):
        for dom in self._domains.values():
            if dom.size() > 1:
                return True
        return False        

    def distribute(self, strat):
        w('SP:start constraint propagation & distribution loop')
        space = self.space
        if strat == 'dichotomy':
            dist = rd.DichotomyDistributor()
        elif strat == 'allornothing':
            dist = rd.AllOrNothingDistributor()
        else:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("please pick a strategy in "
                                            "(allornothing, dichotomy)."))
        # initialize constraint queue
        self._cqueue = [(constr.estimate_cost(self._domains), constr)
                        for constr in self._constraints]
        self.wait_stable() # hmm
        self.propagate()
        while self.distributable():
            w('SP:distribute loop')
            w_choice = self.choose(2) # yes, two, always, all the time
            choice = space.int_w(w_choice)
            small_dom_var = dist.find_smallest_domain(self._domains)
            dom = self._domains[small_dom_var]
            dist._distribute_on_choice(dom, choice)
            for constraint in self._varconst[small_dom_var]:
                self._cqueue.append((0, constraint)) # *uck the cost
            dom._changed = False
            self.propagate()

    def propagate(self): # XXX pasted from rlib.cslib.rpropagation, mixin me
        """Prunes the domains of the variables
        This method calls constraint.narrow() and queues constraints
        that are affected by recent changes in the domains.
        Returns True if a solution was found"""

        # XXX : _queue.sort()
        w('SP:propagating')
        _queue = self._cqueue
        _affected_constraints = {}
        while True:
            if not _queue:
                # refill the queue if some constraints have been affected
                _queue = [(constr.estimate_cost(self._domains), constr)
                          for constr in _affected_constraints]
                if not _queue:
                    break
                # XXX _queue.sort()
                _affected_constraints.clear()
            cost, constraint = _queue.pop(0)
            entailed = constraint.revise(self._domains)
            for var in constraint._variables:
                # affected constraints are listeners of
                # affected variables of this constraint
                dom = self._domains[var]
                if not dom._changed: # XXX
                    continue
                for constr in self._varconst[var]:
                    if constr is not constraint:
                        _affected_constraints[constr] = True
                dom._changed = False
            if entailed:
                self.untell(constraint)
                if constraint in _affected_constraints:
                    del _affected_constraints[constraint]
                
        for domain in self._domains.values():
            if domain.size() != 1:
                return 0
        return 1

    #-- Public ops

    def report_bad_condition_to_applevel(self):
        """
        a couple of checks for methods on spaces
        but forbidden within
        """
        currspace = get_current_cspace(self.space)
        if currspace is self:
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("you can't do this operation"
                                                 "on the current computation space"))
        if not interp_free(self._finished):
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("space is finished"))


    def w_ask(self):
        try:
            self.report_bad_condition_to_applevel()
        except: # we're dead, let's avoid wait_stable ...
            return self.space.wrap(self._last_choice)
        self.wait_stable()
        self.space.wait(self._choices)
        choices = self._choices.w_bound_to
        self._choices = self._newvar()
        assert isinstance(choices, W_IntObject)
        self._last_choice = self.space.int_w(choices)
        return choices

    def choose(self, n):
        assert interp_free(self._choices)
        assert interp_free(self._committed)
        # XXX we wrap it a bit prematurely, so as to satisfy
        # type requirements (logic variables only accept W_Roots)
        interp_bind(self._choices, self.space.wrap(n)) # unblock the solver
        # now we wait on a solver commit
        self.space.wait(self._committed) 
        committed = self._committed.w_bound_to
        self._committed = newvar(self.space)
        return committed

    def w_commit(self, w_n):
        self.report_bad_condition_to_applevel()
        if not isinstance(w_n, W_IntObject):
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap('commit accepts only ints.'))
        n = self.space.int_w(w_n)
        assert interp_free(self._committed)
        if n < 1 or n > self._last_choice:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap("need 0<commit<=%d" %
                                                 self._last_choice))
        interp_bind(self._committed, w_n) 

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
        if self._merged:
            return self._solution
        # let's bind the solution variables
        self._merged = True
        sol = self._solution.w_bound_to
        if isinstance(sol, W_ListObject):
            self._bind_solution_variables(sol.wrappeditems)
        elif isinstance(sol, W_TupleObject):
            self._bind_solution_variables(sol.wrappeditems)
        return self._solution

    #-- / Public ops

    def __ne__(self, other):
        if other is self:
            return False
        return True

    def _bind_solution_variables(self, solution):
        if contains_cvar(solution): # was a constraint script
            for var in solution:
                assert isinstance(var, W_CVar)
                dom = self._domains[var.name]
                assert isinstance(dom, fd._FiniteDomain)
                assert dom.size() == 1
                interp_bind(var, dom.get_wvalues_in_rlist()[0])


def contains_cvar(lst):
    return isinstance(lst[0], W_CVar)


W_CSpace.typedef = typedef.TypeDef("W_CSpace",
    ask = gateway.interp2app(W_CSpace.w_ask),
    commit = gateway.interp2app(W_CSpace.w_commit),
    clone = gateway.interp2app(W_CSpace.w_clone),
    merge = gateway.interp2app(W_CSpace.w_merge),
    fail = gateway.interp2app(W_CSpace.w_fail))


import pypy.rlib.cslib.rdistributor as rd
from pypy.module.cclp.constraint.domain import _DorkFiniteDomain


class W_ComplicatedSpace(W_CSpace):
    """
    a space with concurrent propagators inside
    it performs poorly, is needlessly complicated
    the author should be shot
    """

    def __init__(self, space, dist_thread, saved_pool):
        W_ThreadGroupScheduler.__init__(self, space)
        # thread ring
        dist_thread._cspace = self
        self._init_head(dist_thread)
        # /ring
        # pool
        self.local_pool = None
        self.saved_pool = saved_pool
        # /pool
        sched.uler.add_new_group(self)
        self.dist = None # dist instance != thread
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
        self._domains = {} # varname -> domain


    def register_var(self, cvar):
        name = cvar.name
        self._store[name] = cvar
        # let's switch to dork-style finite domains
        basic_dom = cvar.w_dom.domain
        dom = _DorkFiniteDomain(self.space,
                                basic_dom.vlist,
                                basic_dom._values)
        cvar.w_dom.domain = dom
        self._domains[name] = dom
        
    def distribute(self, strat):
        space = self.space
        if strat == 'dichotomy':
            dist = rd.DichotomyDistributor()
        elif strat == 'allornothing':
            dist = rd.AllOrNothingDistributor()
        else:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("please pick a strategy in "
                                            "(allornothing, dichotomy)."))
        self.wait_stable()
        while self.distributable():
            w_choice = self.choose(2)
            choice = space.int_w(w_choice)
            small_dom_var = dist.find_smallest_domain(self._domains)
            dom = self._domains[small_dom_var]
            w('ABOUT TO DISTRIBUTE')
            dist._distribute_on_choice(dom, choice)
            self.wait_stable()

    def tell(self, constraint):
        space = self.space
        w_coro = AppCoroutine(space)
        w_coro._next = w_coro._prev = w_coro
        w_coro._cspace = self
        thunk = PropagatorThunk(space, constraint, w_coro)
        w_coro.bind(thunk)
        self.add_new_thread(w_coro)

    
    def _bind_solution_variables(self, solution):
        if contains_cvar(solution): # was a constraint script
            for var in solution:
                assert isinstance(var, W_CVar)
                realvar = self._store[var.name]
                dom = realvar.w_dom.domain
                assert isinstance(dom, fd._FiniteDomain)
                assert dom.size() == 1
                interp_bind(var, dom.get_wvalues_in_rlist()[0])
