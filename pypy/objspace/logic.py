from pypy.objspace.proxy import patch_space_in_place
from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError
from pypy.rpython.objectmodel import we_are_translated
from pypy.tool.uid import uid

# wrapped types, mm stuff
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject
from pypy.objspace.std.dictobject import W_DictObject
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.model import StdObjSpaceMultiMethod

#
from pypy.interpreter.error import OperationError

# misc
import os

NO_DEBUG_INFO = [False]
def w(*msgs):
    """writeln"""
    if NO_DEBUG_INFO[0]: return
    v(*msgs)
    os.write(1, ' \n')

def v(*msgs):
    """write"""
    if NO_DEBUG_INFO[0]: return
    for msg in msgs:
        os.write(1, msg)
        os.write(1, ' ')

#-- THE BUILTINS ----------------------------------------------------------------------

# this collects all multimethods to be made part of the Space
all_mms = {}
W_Root = baseobjspace.W_Root
Wrappable = baseobjspace.Wrappable

#-- THREADING/COROUTINING -----------------------------------

USE_COROUTINES = True
HAVE_GREENLETS = True
try:
    from py.magic import greenlet
    del greenlet
except ImportError:
    HAVE_GREENLETS = False

def have_uthreads():
    if USE_COROUTINES:
        if we_are_translated():
            return True
        else:
            return HAVE_GREENLETS
    return False

assert USE_COROUTINES # once & for all

from pypy.module._stackless.coroutine import _AppThunk
from pypy.module._stackless.coroutine import Coroutine # XXX (that's for main)
from pypy.module._stackless.interp_clonable import ClonableCoroutine

class Scheduler(object):

    def __init__(self, space):
        self.space = space
        self._main = ClonableCoroutine.w_getcurrent(space)
        self._init_head(self._main)
        self._init_blocked()
        self._switch_count = 0
        w (".. MAIN THREAD = ", str(id(self._main)))

    def _init_blocked(self):
        self._blocked = {} # thread set
        self._blocked_on = {} # var -> threads
        self._blocked_byneed = {} # var -> threads

    def _init_head(self, coro):
        self._head = coro
        self._head.next = self._head.prev = self._head

    def _set_head(self, thread):
        self._head = thread

    def _check_initial_conditions(self):
        try:
            assert self._head.next == self._head.prev == self._head
            assert self._head not in self._blocked
            assert self._head not in self._blocked_on
            assert self._head not in self._blocked_byneed
        except:
            self.display_head()
            w("BLOCKED", str(self._blocked))
            all = {}
            all.update(self._blocked_on)
            all.update(self._blocked_byneed)
            w(str(all))
            raise
            
    def _chain_insert(self, thread):
        assert thread.next is None
        assert thread.prev is None
        if self._head is None:
            thread.next = thread
            thread.prev = thread
            self._set_head(thread)
        else:
            r = self._head
            l = r.prev
            l.next = thread
            r.prev = thread
            thread.prev = l
            thread.next = r

    def remove_thread(self, thread):
        #XXX don't we need to notify the consumers ?
        w(".. REMOVING", str(id(thread)))
        assert thread not in self._blocked
        l = thread.prev
        r = thread.next
        l.next = r
        r.prev = l
        if r == thread:
            w("DUH !")
            self.display_head()
        thread.next = thread.next = None
        return thread

    #-- to be used by logic objspace

    def schedule(self):
        to_be_run = self._select_next()
        w(".. SWITCHING", str(id(ClonableCoroutine.w_getcurrent(self.space))), "=>", str(id(to_be_run)))
        self._switch_count += 1
        to_be_run.w_switch() 
        
    def _select_next(self):
        to_be_run = self._head
        sentinel = to_be_run
        current = ClonableCoroutine.w_getcurrent(self.space)
        while (to_be_run in self._blocked) \
                  or (to_be_run == current) \
                  or to_be_run.is_dead():
            to_be_run = to_be_run.next
            if to_be_run == sentinel:
                self.display_head()
                ## we RESET sched state so as to keep being usable beyond that
                #  (for instance, allow other tests to be run)
                self._init_head(self._main)
                self._init_blocked()
                w(".. SCHEDULER reinitialized")
                raise OperationError(self.space.w_RuntimeError,
                                     self.space.wrap("can't schedule, possible deadlock in sight"))
        return to_be_run

    def __len__(self):
        "count of known threads (including dead ones)"
        curr = self._head
        sentinel = curr
        count = 1 # there is always a main thread
        while curr.next != sentinel:
            curr = curr.next
            count += 1
        return count

    def display_head(self):
        curr = self._head
        v('Threads : [', '-'.join([str(id(curr)), str(curr in self._blocked)]))
        while curr.next != self._head:
            curr = curr.next
            v('-'.join([str(id(curr)), str(curr in self._blocked)]))
        w(']')

    def add_new_thread(self, thread):
        "insert 'thread' at end of running queue"
        assert isinstance(thread, ClonableCoroutine)
        self._chain_insert(thread)

    def add_to_blocked_on(self, w_var, uthread):
        w(".. we BLOCK thread", str(id(uthread)), "on var", str(id(w_var)))
        assert isinstance(w_var, W_Var)
        assert isinstance(uthread, Coroutine)
        assert uthread not in self._blocked
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
        else:
            blocked = []
            self._blocked_on[w_var] = blocked
        blocked.append(uthread)
        self._blocked[uthread] = True

    def unblock_on(self, w_var):
        v(".. we UNBLOCK threads dependants of var", str(id(w_var)))
        assert isinstance(w_var, W_Var)
        blocked = []
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
            del self._blocked_on[w_var]
        w(str([id(thr) for thr in blocked]))
        for thr in blocked: del self._blocked[thr]

    def add_to_blocked_byneed(self, w_var, uthread):
        w(".. we BLOCK BYNEED thread", str(id(uthread)), "on var", str(id(w_var)))
        assert isinstance(w_var, W_Var)
        assert isinstance(uthread, ClonableCoroutine)
        if w_var in self._blocked_byneed:
            blocked = self._blocked_byneed[w_var]
        else:
            blocked = []
            self._blocked_byneed[w_var] = blocked
        blocked.append(uthread)
        self._blocked[uthread] = True

    def unblock_byneed_on(self, space, w_var):
        v(".. we UNBLOCK BYNEED dependants of var", str(id(w_var)))
        assert isinstance(w_var, W_Var)
        blocked = []
        for w_alias in aliases(space, w_var):
            if w_alias in self._blocked_byneed:
                blocked += self._blocked_byneed[w_alias]
                del self._blocked_byneed[w_alias]
            w_alias.w_needed = True
        w(str([id(thr) for thr in blocked]))
        for thr in blocked: del self._blocked[thr]

scheduler = []

class FutureThunk(_AppThunk):
    def __init__(self, space, w_callable, args, w_Result, coro):
        _AppThunk.__init__(self, space, coro.costate, w_callable, args)
        self.w_Result = w_Result 
        self._coro = coro

    def call(self):
        try:
            try:
                _AppThunk.call(self)
            except Exception, exc:
                w(".. exceptional EXIT of", str(id(self._coro)), "with", str(exc))
                bind(self.space, self.w_Result, W_FailedValue(exc))
                self._coro._dead = True
            else:
                w(".. clean EXIT of", str(id(self._coro)),
                  "-- setting future result to",
                  str(self.costate.w_tempval))
                unify(self.space, self.w_Result, self.costate.w_tempval)
        finally:
            scheduler[0].remove_thread(self._coro)
            scheduler[0].schedule()

def future(space, w_callable, __args__):
    """returns a future result"""
    v(".. THREAD")
    args = __args__.normalize()
    w_Future = W_Future(space)
    # coro init
    coro = ClonableCoroutine(space)
    # prepare thread chaining, create missing slots
    coro.next = coro.prev = None
    # feed the coro
    thunk = FutureThunk(space, w_callable, args, w_Future, coro)
    coro.bind(thunk)
    w(str(id(coro)))
    scheduler[0].add_new_thread(coro)
    # XXX we should think about a way to make it read-only for the client
    #     (i.e the originator), aka true futures
    return w_Future
app_future = gateway.interp2app(future, unwrap_spec=[baseobjspace.ObjSpace,
                                                     baseobjspace.W_Root,
                                                     argument.Arguments])
    
# need : getcurrent(), getmain(), 
# wrapper for schedule() ?

def sched_stats(space):
    sched = scheduler[0]
    w_ret = space.newdict([])
    space.setitem(w_ret, space.wrap('switches'), space.wrap(sched._switch_count))
    space.setitem(w_ret, space.wrap('threads'), space.wrap(len(sched)))
    space.setitem(w_ret, space.wrap('blocked'), space.wrap(len(sched._blocked)))
    space.setitem(w_ret, space.wrap('blocked_on'), space.wrap(len(sched._blocked_on)))
    space.setitem(w_ret, space.wrap('blocked_byneed'), space.wrap(len(sched._blocked_byneed)))
    return w_ret
app_sched_stats = gateway.interp2app(sched_stats)

#-- VARIABLE ---------------------

#-- Exceptions -------

## what we can know:

##     location of new var
##     transmission of vars to threads

##     => possibility to propagate exceptions amongst all threads that share a var
##     (kind of process linking in Erlang, where giving var => do link)

## what is sane ?

##      reraising FailedValues (case of futures)
##      XXX

#-- /Exceptions ------

class W_Var(W_Root, object):
    def __init__(w_self):
        w_self.w_bound_to = w_self 
        w_self.w_needed = False    

    def __repr__(w_self):
        if w_self.w_bound_to:
            if isinstance(w_self.w_bound_to, W_Var):
                return '<?@%s>' % prettyfy_id(str(id(w_self)))
            return '<%s@%s>' % (w_self.w_bound_to,
                                prettyfy_id(str(id(w_self))))

def newvar(space):
    return W_Var()
app_newvar = gateway.interp2app(newvar)

class W_Future(W_Var):
    def __init__(w_self, space):
        W_Var.__init__(w_self)
        w_self.client = ClonableCoroutine.w_getcurrent(space)

class W_FailedValue(W_Root, object):
    """wraps an exception raised in some coro, to be re-raised in
       some dependant coro sometime later
    """
    def __init__(w_self, exc):
        w_self.exc = exc

#-- wait/needed ----

def wait__Root(space, w_obj):
    return w_obj

def wait__Var(space, w_var):
    w(":wait", str(id(ClonableCoroutine.w_getcurrent(space))))
    if space.is_true(space.is_free(w_var)):
        scheduler[0].unblock_byneed_on(space, w_var)
        scheduler[0].add_to_blocked_on(w_var, ClonableCoroutine.w_getcurrent(space))
        scheduler[0].schedule()
    assert space.is_true(space.is_bound(w_var))
    w_ret = w_var.w_bound_to
    if isinstance(w_ret, W_FailedValue):
        w(".. reraising Failed Value")
        raise w_ret.exc
    return w_ret

def wait(space, w_obj):
    assert isinstance(w_obj, W_Root)
    return space.wait(w_obj)
app_wait = gateway.interp2app(wait)

wait_mm = StdObjSpaceMultiMethod('wait', 1)
wait_mm.register(wait__Var, W_Var)
wait_mm.register(wait__Root, W_Root)
all_mms['wait'] = wait_mm


def wait_needed__Var(space, w_var):
    #print " :needed", w_var
    if space.is_true(space.is_free(w_var)):
        if w_var.w_needed:
            return
        scheduler[0].add_to_blocked_byneed(w_var, ClonableCoroutine.w_getcurrent(space))
        scheduler[0].schedule()
    else:
        raise OperationError(space.w_RuntimeError,
                             space.wrap("wait_needed only supported on unbound variables"))

def wait_needed(space, w_var):
    assert isinstance(w_var, W_Var)
    return space.wait_needed(w_var)
app_wait_needed = gateway.interp2app(wait_needed)            

wait_needed_mm = StdObjSpaceMultiMethod('wait_needed', 1)
wait_needed_mm.register(wait_needed__Var, W_Var)
all_mms['wait_needed'] = wait_needed_mm


#-- PREDICATES --------------------

def is_aliased(space, w_var): # FIXME: this appears to block
    assert isinstance(w_var, W_Var)
    if space.is_true(space.is_nb_(deref(space, w_var), w_var)):
        return space.newbool(False)
    return space.newbool(True)
app_is_aliased = gateway.interp2app(is_aliased)

def is_free(space, w_obj):
    assert isinstance(w_obj, W_Root)
    return space.is_free(w_obj)
app_is_free = gateway.interp2app(is_free)

def is_free__Root(space, w_obj):
    return space.newbool(False)

def is_free__Var(space, w_var):
    return space.newbool(isinstance(w_var.w_bound_to, W_Var))

is_free_mm = StdObjSpaceMultiMethod('is_free', 1)
is_free_mm.register(is_free__Root, W_Root)
is_free_mm.register(is_free__Var, W_Var)
all_mms['is_free'] = is_free_mm

def is_bound(space, w_obj):
    assert isinstance(w_obj, W_Root)
    return space.is_bound(w_obj)
app_is_bound = gateway.interp2app(is_bound)

def is_bound__Root(space, w_obj):
    return space.newbool(True)

def is_bound__Var(space, w_var):
    return space.newbool(not isinstance(w_var.w_bound_to, W_Var))

is_bound_mm = StdObjSpaceMultiMethod('is_bound', 1)
is_bound_mm.register(is_bound__Root, W_Root)
is_bound_mm.register(is_bound__Var, W_Var)
all_mms['is_bound'] = is_bound_mm


def alias_of(space, w_var1, w_var2): # FIXME: appears to block
    assert isinstance(w_var1, W_Var)
    assert isinstance(w_var2, W_Var)
    assert space.is_true(space.is_free(w_var1))
    assert space.is_true(space.is_free(w_var2))
    w_curr = w_var1
    while 1:
        w_next = w_curr.w_bound_to
        if space.is_true(space.is_nb_(w_next, w_var2)):
            return space.newbool(True)
        if space.is_true(space.is_nb_(w_next, w_var1)):
            break
        w_curr = w_next
    return space.newbool(False)
app_alias_of = gateway.interp2app(alias_of)


#-- HELPERS ----------------------

def deref(space, w_var):
    """gets the value of a bound variable
       user has to ensure boundness of the var"""
    assert isinstance(w_var, W_Var)
    return w_var.w_bound_to

def aliases(space, w_var):
    """return the aliases of a var, including itself"""
    assert isinstance(w_var, W_Var)
    al = []
    w_curr = w_var
    while 1:
        w_next = w_curr.w_bound_to
        al.append(w_curr)
        if space.is_true(space.is_nb_(w_next, w_var)):
            break
        w_curr = w_next
    return al

def get_ring_tail(space, w_start):
    """returns the last var of a ring of aliases"""
    assert isinstance(w_start, W_Var)
    w_curr = w_start
    while 1:
        w_next = w_curr.w_bound_to
        if space.is_true(space.is_nb_(w_next, w_start)):
            return w_curr
        w_curr = w_next


def fail(space, w_obj1, w_obj2):
    """raises a specific exception for bind/unify"""
    #FIXME : really raise some specific exception
    assert isinstance(w_obj1, W_Root)
    assert isinstance(w_obj2, W_Root)
    raise OperationError(space.w_RuntimeError,
                         space.wrap("Unification failure"))


def prettyfy_id(a_str):
    assert isinstance(a_str, str)
    l = len(a_str) - 1
    return a_str[l-3:l]

def interp_id(space, w_obj):
    assert isinstance(w_obj, W_Root) # or W_Wrappable ?
    return space.newint(id(w_obj))
app_interp_id = gateway.interp2app(interp_id)

def switch_debug_info(space):
    NO_DEBUG_INFO[0] = not NO_DEBUG_INFO[0]
app_switch_debug_info = gateway.interp2app(switch_debug_info)

#-- BIND -----------------------------

def bind(space, w_var, w_obj):
    """1. aliasing of unbound variables
       2. assign bound var to unbound var
       3. assign value to unbound var
    """
    v(" :bind")
    assert isinstance(w_var, W_Var)
    assert isinstance(w_obj, W_Root)
    space.bind(w_var, w_obj)
app_bind = gateway.interp2app(bind)

def bind__Var_Root(space, w_var, w_obj):
    w("var val", str(id(w_var)))
    # 3. var and value
    if space.is_true(space.is_free(w_var)):
        return _assign(space, w_var, w_obj)
    if space.is_true(space.eq(w_var.w_bound_to, w_obj)):
        return
    raise OperationError(space.w_RuntimeError,
                         space.wrap("Cannot bind twice"))

def bind__Future_Root(space, w_fut, w_obj):
    #v("future val", str(id(w_fut)))
    if w_fut.client == ClonableCoroutine.w_getcurrent(space):
        raise OperationError(space.w_RuntimeError,
                             space.wrap("This future is read-only for you, pal"))
    bind__Var_Root(space, w_fut, w_obj) # call-next-method ?

def bind__Var_Var(space, w_v1, w_v2):
    w("var var")
    if space.is_true(space.is_bound(w_v1)):
        if space.is_true(space.is_bound(w_v2)):
            # we allow re-binding to same value, see 3.
            return unify(space,
                         deref(space, w_v1),
                         deref(space, w_v2))
        # 2. a (obj unbound, var bound)
        return _assign(space, w_v2, deref(space, w_v1))
    elif space.is_true(space.is_bound(w_v2)):
        # 2. b (var unbound, obj bound)
        return _assign(space, w_v1, deref(space, w_v2))
    else: # 1. both are unbound
        return _alias(space, w_v1, w_v2)

def bind__Future_Var(space, w_fut, w_var):
    #v("future var")
    if w_fut.client == ClonableCoroutine.w_getcurrent(space):
        raise OperationError(space.w_RuntimeError,
                             space.wrap("This future is read-only for you, pal"))
    bind__Var_Var(space, w_fut, w_var)

#XXX Var_Future would just alias or assign, this is ok
    
bind_mm = StdObjSpaceMultiMethod('bind', 2)
bind_mm.register(bind__Var_Root, W_Var, W_Root)
bind_mm.register(bind__Var_Var, W_Var, W_Var)
bind_mm.register(bind__Future_Root, W_Future, W_Root)
bind_mm.register(bind__Future_Var, W_Future, W_Var)
all_mms['bind'] = bind_mm

def _assign(space, w_var, w_val):
    w("  :assign")
    assert isinstance(w_var, W_Var)
    assert isinstance(w_val, W_Root)
    w_curr = w_var
    while 1:
        w_next = w_curr.w_bound_to
        w_curr.w_bound_to = w_val
        # notify the blocked threads
        scheduler[0].unblock_on(w_curr)
        if space.is_true(space.is_nb_(w_next, w_var)):
            break
        # switch to next
        w_curr = w_next
    w("  :assigned")
    return space.w_None
    
def _alias(space, w_v1, w_v2):
    """appends one var to the alias chain of another
       user must ensure freeness of both vars"""
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    w("  :alias", str(id(w_v1)), str(id(w_v2)))
    if space.is_true(space.is_nb_(w_v1, w_v2)):
        return space.w_None
    if space.is_true(is_aliased(space, w_v1)):
        if space.is_true(is_aliased(space, w_v2)):
            return _merge_aliases(space, w_v1, w_v2)
        return _add_to_aliases(space, w_v1, w_v2)
    if space.is_true(is_aliased(space, w_v2)):
        return _add_to_aliases(space, w_v2, w_v1)
    # we have two unaliased vars
    w_v1.w_bound_to = w_v2
    w_v2.w_bound_to = w_v1
    return space.w_None

def _add_to_aliases(space, w_v1, w_v2):
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    w("   :add to aliases")
    w_tail = w_v1.w_bound_to
    w_v1.w_bound_to = w_v2
    w_v2.w_bound_to = w_tail
    return space.w_None
    
def _merge_aliases(space, w_v1, w_v2):
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    w("   :merge aliases")
    w_tail1 = get_ring_tail(space, w_v1)
    w_tail2 = get_ring_tail(space, w_v2)
    w_tail1.w_bound_to = w_v2
    w_tail2.w_bound_to = w_v1
    return space.w_None

#-- UNIFY -------------------------

def unify(space, w_x, w_y):
    assert isinstance(w_x, W_Root)
    assert isinstance(w_y, W_Root)
    #w(":unify ", str(id(w_x)), str(id(w_y)))
    return space.unify(w_x, w_y)
app_unify = gateway.interp2app(unify)

def unify__Root_Root(space, w_x, w_y):
    if not space.eq_w(w_x, w_y):
        w_d1 = w_x.getdict() #returns wrapped dict or unwrapped None ...
        w_d2 = w_y.getdict()
        if None in [w_d1, w_d2]:
            fail(space, w_x, w_y)
        else:
            return space.unify(w_d1, w_d2)
    return space.w_None
    
def unify__Var_Var(space, w_x, w_y):
    #w(":unify var var", str(id(w_x)), str(id(w_y)))
    if space.is_true(space.is_bound(w_x)):
        if space.is_true(space.is_bound(w_y)):
            return space.unify(deref(space, w_x), 
                               deref(space, w_y))
        return space.bind(w_y, w_x)
    # binding or aliasing x & y
    else:
        return space.bind(w_x, w_y) 
    
def unify__Var_Root(space, w_x, w_y):
    #w(" :unify var val", str(id(w_x)), str(w_y))
    if space.is_true(space.is_bound(w_x)):
        return space.unify(deref(space, w_x), w_y)            
    return space.bind(w_x, w_y)

def unify__Root_Var(space, w_x, w_y):
    return space.unify(w_y, w_x)

def unify__Tuple_Tuple(space, w_i1, w_i2):
    if len(w_i1.wrappeditems) != len(w_i2.wrappeditems):
        fail(space, w_i1, w_i2)
    idx, top = (-1, space.int_w(space.len(w_i1))-1)
    while idx < top:
        idx += 1
        w_xi = space.getitem(w_i1, space.newint(idx))
        w_yi = space.getitem(w_i2, space.newint(idx))
        if space.is_true(space.is_nb_(w_xi, w_yi)):
            continue
        unify(space, w_xi, w_yi)
    return space.w_None

def unify__List_List(space, w_i1, w_i2):
    if len(w_i1.wrappeditems) != len(w_i2.wrappeditems):
        fail(space, w_i1, w_i2)
    idx, top = (-1, space.int_w(space.len(w_i1))-1)
    while idx < top:
        idx += 1
        w_xi = space.getitem(w_i1, space.newint(idx))
        w_yi = space.getitem(w_i2, space.newint(idx))
        if space.is_true(space.is_nb_(w_xi, w_yi)):
            continue
        unify(space, w_xi, w_yi)
    return space.w_None


def unify__Dict_Dict(space, w_m1, w_m2):
    assert isinstance(w_m1, W_DictObject)
    assert isinstance(w_m2, W_DictObject)
    #print " :unify mappings", w_m1, w_m2
    for w_xk in w_m1.content.keys():
        w_xi = space.getitem(w_m1, w_xk)
        w_yi = space.getitem(w_m2, w_xk)
        if space.is_true(space.is_nb_(w_xi, w_yi)):
            continue
        space.unify(w_xi, w_yi)
    return space.w_None


unify_mm = StdObjSpaceMultiMethod('unify', 2)
unify_mm.register(unify__Root_Root, W_Root, W_Root)
unify_mm.register(unify__Var_Var, W_Var, W_Var)
unify_mm.register(unify__Var_Root, W_Var, W_Root)
unify_mm.register(unify__Root_Var, W_Root, W_Var)
unify_mm.register(unify__Tuple_Tuple, W_TupleObject, W_TupleObject)
unify_mm.register(unify__List_List, W_ListObject, W_ListObject)
unify_mm.register(unify__Dict_Dict, W_DictObject, W_DictObject)

all_mms['unify'] = unify_mm

#-- SPACE HELPERS -------------------------------------

nb_forcing_args = {}

def setup():
    nb_forcing_args.update({
        'setattr': 2,   # instead of 3
        'setitem': 2,   # instead of 3
        'get': 2,       # instead of 3
        # ---- irregular operations ----
        'wrap': 0,
        'str_w': 1,
        'int_w': 1,
        'float_w': 1,
        'uint_w': 1,
        'interpclass_w': 1,
        'unwrap': 1,
        'is_true': 1,
        'is_w': 2,
        'newtuple': 0,
        'newlist': 0,
        'newstring': 0,
        'newunicode': 0,
        'newdict': 0,
        'newslice': 0,
        'call_args': 1,
        'marshal_w': 1,
        'log': 1,
        })
    for opname, _, arity, _ in baseobjspace.ObjSpace.MethodTable:
        nb_forcing_args.setdefault(opname, arity)
    for opname in baseobjspace.ObjSpace.IrregularOpTable:
        assert opname in nb_forcing_args, "missing %r" % opname

setup()
del setup

def eqproxy(space, parentfn):
    """shortcuts wait filtering"""
    def eq(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        # check identity
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(True)
        # check aliasing
        if space.is_true(space.is_free(w_obj1)):
            if space.is_true(space.is_free(w_obj2)):
                if space.is_true(alias_of(space, w_obj1, w_obj2)):
                    return space.newbool(True) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return eq

def isproxy(space, parentfn):
    def is_(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(True)
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return is_

def cmpproxy(space, parentfn):
    def cmp(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(0)
        if space.is_true(space.is_free(w_obj1)):
            if space.is_true(space.is_free(w_obj2)):
                if space.is_true(alias_of(space, w_obj1, w_obj2)):
                    return space.newbool(0) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return cmp

def neproxy(space, parentfn):
    def ne(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(False)
        if space.is_true(space.is_free(w_obj1)):
            if space.is_true(space.is_free(w_obj2)):
                if space.is_true(alias_of(space, w_obj1, w_obj2)):
                    return space.newbool(False) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return ne

def proxymaker(space, opname, parentfn):
    if opname == "eq":
        return eqproxy(space, parentfn)
    if opname == "is_": # FIXME : is_, is_w ?
        return isproxy(space, parentfn)
    if opname == "ne":
        return neproxy(space, parentfn)
    if opname == "cmp":
        return cmpproxy(space, parentfn)
    nb_args = nb_forcing_args[opname]
    if nb_args == 0:
        proxy = None
    elif nb_args == 1:
        def proxy(w1, *extra):
            w1 = wait(space, w1)
            return parentfn(w1, *extra)
    elif nb_args == 2:
        def proxy(w1, w2, *extra):
            w1 = wait(space, w1)
            w2 = wait(space, w2)
            return parentfn(w1, w2, *extra)
    elif nb_args == 3:
        def proxy(w1, w2, w3, *extra):
            w1 = wait(space, w1)
            w2 = wait(space, w2)
            w3 = wait(space, w3)
            return parentfn(w1, w2, w3, *extra)
    else:
        raise NotImplementedError("operation %r has arity %d" %
                                  (opname, nb_args))
    return proxy


## #------ domains ------------------
## from pypy.objspace.constraint import domain 
## all_mms.update(domain.all_mms)

## W_FiniteDomain = domain.W_FiniteDomain

## #-------- computationspace --------
## from pypy.objspace.constraint import computationspace
## all_mms.update(computationspace.all_mms)

## W_ComputationSpace = computationspace.W_ComputationSpace

## # ---- constraints ----------------
## from pypy.objspace.constraint import constraint
## all_mms.update(constraint.all_mms)

## #----- distributors ---------------
## from pypy.objspace.constraint import distributor


#-- THE SPACE ---------------------------------------

#class UnificationError(w_RuntimeError):
#    pass

from pypy.objspace.std import stdtypedef 
from pypy.tool.sourcetools import func_with_new_name


def Space(*args, **kwds):
    # for now, always make up a wrapped StdObjSpace
    from pypy.objspace import std
    space = std.Space(*args, **kwds)

    # multimethods hack
    space.model.typeorder[W_Var] = [(W_Var, None), (W_Root, None)] # None means no conversion
    space.model.typeorder[W_Future] = [(W_Future, None), (W_Var, None)]
##     space.model.typeorder[W_FiniteDomain] = [(W_FiniteDomain, None), (W_Root, None)] 


    for name in all_mms.keys():
        exprargs, expr, miniglobals, fallback = (
            all_mms[name].install_not_sliced(space.model.typeorder, baked_perform_call=False))
        func = stdtypedef.make_perform_trampoline('__mm_' + name,
                                                  exprargs, expr, miniglobals,
                                                  all_mms[name])
        # e.g. add(space, w_x, w_y)
        def make_boundmethod(func=func):
            def boundmethod(*args):
                return func(space, *args)
            return func_with_new_name(boundmethod, 'boundmethod_'+name)
        boundmethod = make_boundmethod()
        setattr(space, name, boundmethod)  # store into 'space' instance
    # /multimethods hack

    # XXXprovide a UnificationError exception
    # patching the table in-place?  
    #space.ExceptionTable.append('UnificationError')
    #space.ExceptionTable.sort() # hmmm

    space.setitem(space.builtin.w_dict, space.wrap('newvar'),
                  space.wrap(app_newvar))
    space.setitem(space.builtin.w_dict, space.wrap('is_free'),
                  space.wrap(app_is_free))
    space.setitem(space.builtin.w_dict, space.wrap('is_bound'),
                  space.wrap(app_is_bound))
    space.setitem(space.builtin.w_dict, space.wrap('alias_of'),
                  space.wrap(app_alias_of))
    space.setitem(space.builtin.w_dict, space.wrap('is_aliased'),
                  space.wrap(app_is_aliased))
    space.setitem(space.builtin.w_dict, space.wrap('bind'),
                 space.wrap(app_bind))
    space.setitem(space.builtin.w_dict, space.wrap('unify'),
                 space.wrap(app_unify))
##     #-- comp space ---
##     space.setitem(space.builtin.w_dict, space.wrap('newspace'),
##                  space.wrap(computationspace.app_newspace))
##     #-- domain -------
##     space.setitem(space.builtin.w_dict, space.wrap('FiniteDomain'),
##                  space.wrap(domain.app_make_fd))
##     space.setitem(space.builtin.w_dict, space.wrap('intersection'),
##                  space.wrap(domain.app_intersection))
##     #-- constraint ----
##     space.setitem(space.builtin.w_dict, space.wrap('make_expression'),
##                  space.wrap(constraint.app_make_expression))
##     space.setitem(space.builtin.w_dict, space.wrap('AllDistinct'),
##                  space.wrap(constraint.app_make_alldistinct))
##     #-- distributor --
##     space.setitem(space.builtin.w_dict, space.wrap('NaiveDistributor'),
##                  space.wrap(distributor.app_make_naive_distributor))
##     space.setitem(space.builtin.w_dict, space.wrap('SplitDistributor'),
##                  space.wrap(distributor.app_make_split_distributor))
##     space.setitem(space.builtin.w_dict, space.wrap('DichotomyDistributor'),
##                  space.wrap(distributor.app_make_dichotomy_distributor))
    #-- threading --
    space.setitem(space.builtin.w_dict, space.wrap('future'),
                 space.wrap(app_future))
    space.setitem(space.builtin.w_dict, space.wrap('wait'),
                 space.wrap(app_wait))
    space.setitem(space.builtin.w_dict, space.wrap('wait_needed'),
                  space.wrap(app_wait_needed))
    space.setitem(space.builtin.w_dict, space.wrap('sched_stats'),
                  space.wrap(app_sched_stats))

    #-- misc -----
    space.setitem(space.builtin.w_dict, space.wrap('interp_id'),
                  space.wrap(app_interp_id))
    space.setitem(space.builtin.w_dict, space.wrap('switch_debug_info'),
                  space.wrap(app_switch_debug_info))

    #-- path to the applevel modules --
    import pypy.objspace.constraint
    import os
    dir = os.path.dirname(pypy.objspace.constraint.__file__)
    dir = os.path.join(dir, 'applevel')
    space.call_method(space.sys.get('path'), 'append', space.wrap(dir))

    # make sure that _stackless is imported
    w_modules = space.getbuiltinmodule('_stackless')
    # cleanup func called from space.finish()
    def exitfunc():
        pass
    
    app_exitfunc = gateway.interp2app(exitfunc, unwrap_spec=[])
    space.setitem(space.sys.w_dict, space.wrap("exitfunc"), space.wrap(app_exitfunc))

    # capture one non-blocking op
    space.is_nb_ = space.is_

    # do the magic
    patch_space_in_place(space, 'logic', proxymaker)

    # instantiate singleton scheduler
    scheduler.append(Scheduler(space))
    return space
