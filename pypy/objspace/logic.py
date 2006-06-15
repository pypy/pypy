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


#-- THE BUILTINS ----------------------------------------------------------------------

# this collects all multimethods to be made part of the Space
all_mms = {}
W_Root = baseobjspace.W_Root
Wrappable = baseobjspace.Wrappable

USE_COROUTINES = True
HAVE_GREENLETS = True
try:
    from py.magic import greenlet
except ImportError:
    HAVE_GREENLETS = False

def have_uthreads():
    if USE_COROUTINES:
        if we_are_translated():
            return True
        else:
            return HAVE_GREENLETS
    return False

if USE_COROUTINES:
    from pypy.module._stackless.coroutine import AppCoroutine, _AppThunk

    class ScheduleState(object):
        def __init__(self):
            self.runnable_uthreads = {}
            self.uthreads_blocked_on = {}
            self.uthreads_blocked_byneed = {}

        def pop_runnable_thread(self):
            # umpf, no popitem in RPython
            key = None
            for key, item in self.runnable_uthreads.iteritems():
                break
            del self.runnable_uthreads[key]
            return key 

        def add_to_runnable(self, uthread):
            assert isinstance(uthread, AppCoroutine)
            self.runnable_uthreads[uthread] = True

        def remove_from_runnable(self, uthread):
            assert isinstance(uthread, AppCoroutine)
            del self.runnable_uthreads[uthread]

        def have_runnable_threads(self):
            return bool(self.runnable_uthreads)

        def have_blocked_threads(self):
            return bool(self.uthreads_blocked_on)

        def add_to_blocked(self, w_var, uthread):
            assert isinstance(w_var, W_Var)
            assert isinstance(uthread, AppCoroutine)
            if w_var in self.uthreads_blocked_on:
                blocked = self.uthreads_blocked_on[w_var]
            else:
                blocked = []
                self.uthreads_blocked_on[w_var] = blocked
            blocked.append(uthread)

        def pop_blocked_on(self, w_var):
            assert isinstance(w_var, W_Var)
            if w_var not in self.uthreads_blocked_on:
                blocked = []
            else:
                blocked = self.uthreads_blocked_on[w_var]
                del self.uthreads_blocked_on[w_var]
            return blocked

        def add_to_blocked_byneed(self, w_var, uthread):
            assert isinstance(w_var, W_Var)
            assert isinstance(uthread, AppCoroutine)
            #print " adding", uthread, "to byneed on", w_var
            if w_var in self.uthreads_blocked_byneed:
                blocked = self.uthreads_blocked_byneed[w_var]
            else:
                blocked = []
                self.uthreads_blocked_byneed[w_var] = blocked
            blocked.append(uthread)

        def pop_blocked_byneed_on(self, w_var):
            assert isinstance(w_var, W_Var)
            if w_var not in self.uthreads_blocked_byneed:
                #print " there was nobody to remove for", w_var
                blocked = []
            else:
                blocked = self.uthreads_blocked_byneed[w_var]
                del self.uthreads_blocked_byneed[w_var]
            #print " removing", blocked, "from byneed on", w_var
            return blocked


    schedule_state = ScheduleState()

    class Thunk(_AppThunk):
        def __init__(self, space, state, w_callable, args, w_Result):
            _AppThunk.__init__(self, space, state, w_callable, args)
            self.w_Result = w_Result # the upper-case R is because it is a logic variable

        def call(self):
            costate = self.costate
            _AppThunk.call(self)
            bind(self.space, self.w_Result,
                 costate.w_tempval)

    def uthread(space, w_callable, __args__):
        args = __args__.normalize()
        w_Result = W_Var()
        coro = AppCoroutine(space)
        state = coro.costate
        thunk = Thunk(space, state, w_callable, args, w_Result)
        coro.bind(thunk)
        current = AppCoroutine.w_getcurrent(space)
        schedule_state.add_to_runnable(current)
        coro.w_switch()
        while schedule_state.have_runnable_threads():
            next_coro = schedule_state.pop_runnable_thread()
            if next_coro.is_alive() and next_coro != current:
                schedule_state.add_to_runnable(current)
                next_coro.w_switch()
        return w_Result
    app_uthread = gateway.interp2app(uthread, unwrap_spec=[baseobjspace.ObjSpace,
                                                           baseobjspace.W_Root,
                                                           argument.Arguments])
    

#-- VARIABLE ---------------------

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


def wait__Root(space, w_obj):
    return w_obj

def wait__Var(space, w_var):
    while 1:
        #print " :wait", w_var
        if space.is_true(space.is_free(w_var)):
            if not have_uthreads():
                raise OperationError(space.w_RuntimeError,
                                     space.wrap("trying to perform an operation on an unbound variable"))
            else:
                # notify wait_needed clients, give them a chance to run
                w_var.w_needed = True
                for w_alias in aliases(space, w_var):
                    need_waiters = schedule_state.pop_blocked_byneed_on(w_alias)
                    w_alias.w_needed = True
                    for waiter in need_waiters:
                        #print "  :byneed waiter", waiter, "awaken on", w_alias
                        schedule_state.add_to_runnable(waiter)
                # set curr thread to blocked, switch to runnable thread
                current = AppCoroutine.w_getcurrent(space)
                schedule_state.add_to_blocked(w_var, current)
                while schedule_state.have_runnable_threads():
                    next_coro = schedule_state.pop_runnable_thread()
                    if next_coro.is_alive():
                        #print "  :waiter is switching"
                        next_coro.w_switch()
                        #print " waiter is back"
                        # hope there is a value here now
                        break
                else:
                    raise OperationError(space.w_RuntimeError,
                                         space.wrap("blocked on variable, but no uthread that can bind it"))
        else:
            return w_var.w_bound_to

def wait(space, w_obj):
    assert isinstance(w_obj, W_Root)
    return space.wait(w_obj)
app_wait = gateway.interp2app(wait)

wait_mm = StdObjSpaceMultiMethod('wait', 1)
wait_mm.register(wait__Var, W_Var)
wait_mm.register(wait__Root, W_Root)
all_mms['wait'] = wait_mm


def wait_needed__Var(space, w_var):
    while 1:
        #print " :needed", w_var
        if space.is_true(space.is_free(w_var)):
            if w_var.w_needed:
                break # we're done
            if not have_uthreads():
                raise OperationError(space.w_RuntimeError,
                                     space.wrap("oh please oh FIXME !"))
            else:
                # add current thread to blocked byneed and switch
                current = AppCoroutine.w_getcurrent(space)
                for w_alias in aliases(space, w_var):
                    schedule_state.add_to_blocked_byneed(w_alias, current)
                while schedule_state.have_runnable_threads():
                    next_coro = schedule_state.pop_runnable_thread()
                    if next_coro.is_alive():
                        #print "  :needed is switching"
                        next_coro.w_switch()
                        #print " byneed is back"
                        # there might be some need right now
                        break
                else:
                    raise OperationError(space.w_RuntimeError,
                                         space.wrap("blocked on need, but no uthread that can wait"))
            
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

## def disp(space, w_var):
##     print w_var
## app_disp = gateway.interp2app(disp)

## def disp_aliases(space, w_var):
##     print "Aliases of ", w_var, "are", 
##     for w_al in aliases(space, w_var):
##         print w_al,
##     print

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
    #print "failed to bind/unify"
    assert isinstance(w_obj1, W_Root)
    assert isinstance(w_obj2, W_Root)
    raise OperationError(space.w_RuntimeError,
                         space.wrap("Unification failure"))

def check_and_memoize_pair(space, w_x, w_y):
    pass

def reset_memo():
    pass

def prettyfy_id(a_str):
    assert isinstance(a_str, W_StringObject)
    l = len(a_str) - 1
    return a_str[l-3:l]


#FIXME : does not work at all,
# even a pure applevel version ...
## def _sleep(space, w_var, w_barrier):
##     assert isinstance(w_var, W_Var)
##     assert isinstance(w_barrier, W_Var)
##     wait(space, w_var)
##     bind(space, w_barrier, space.newint(1))

## def wait_two(space, w_v1, w_v2):
##     """waits until one out of two logic variables
##        becomes bound, then tells which one,
##        with a bias toward the first if both are
##        suddenly bound"""
##     assert isinstance(w_v1, W_Var)
##     assert isinstance(w_v2, W_Var)
##     w_barrier = newvar(space)
##     uthread(space, space.wrap(_sleep),
##             argument.Arguments(space, [w_v1, w_barrier]))
##     uthread(space, space.wrap(_sleep),
##             argument.Arguments(space, [w_v2, w_barrier]))
##     wait(space, w_barrier)
##     if space.is_true(space.is_free(w_v2)):
##         return space.newint(1)
##     return space.newint(2)
## app_wait_two = gateway.interp2app(wait_two)

#-- BIND -----------------------------

def bind(space, w_var, w_obj):
    """1. aliasing of unbound variables
       2. assign bound var to unbound var
       3. assign value to unbound var
    """
    #print " :bind", w_var, w_obj
    assert isinstance(w_var, W_Var)
    assert isinstance(w_obj, W_Root)
    space.bind(w_var, w_obj)
app_bind = gateway.interp2app(bind)

def bind__Var_Var(space, w_v1, w_v2):
    if space.is_true(space.is_bound(w_v1)):
        if space.is_true(space.is_bound(w_v2)):
            return unify(space, #FIXME: we could just raise
                         deref(space, w_v1),
                         deref(space, w_v2))
        # 2. a (obj unbound, var bound)
        return _assign(space, w_v2, deref(space, w_v1))
    elif space.is_true(space.is_bound(w_v2)):
        # 2. b (var unbound, obj bound)
        return _assign(space, w_v1, deref(space, w_v2))
    else: # 1. both are unbound
        return _alias(space, w_v1, w_v2)


def bind__Var_Root(space, w_var, w_obj):
    # 3. var and value
    if space.is_true(space.is_free(w_var)):
        return _assign(space, w_var, w_obj)
    # for dataflow behaviour we should allow
    # rebinding of unifiable values
    raise OperationError(space.w_RuntimeError,
                         space.wrap("Cannot bind twice"))
    

bind_mm = StdObjSpaceMultiMethod('bind', 2)
bind_mm.register(bind__Var_Root, W_Var, W_Root)
bind_mm.register(bind__Var_Var, W_Var, W_Var)
all_mms['bind'] = bind_mm

def _assign(space, w_var, w_val):
    assert isinstance(w_var, W_Var)
    assert isinstance(w_val, W_Root)
    #print "  :assign", w_var, w_val, '[',
    w_curr = w_var
    ass_count = 0
    while 1:
        w_next = w_curr.w_bound_to
        w_curr.w_bound_to = w_val
        #print w_curr, 
        ass_count += 1
        # notify the blocked threads
        to_awake = schedule_state.pop_blocked_on(w_curr)
        for thread in to_awake:
            schedule_state.add_to_runnable(thread)
        if space.is_true(space.is_nb_(w_next, w_var)):
            break
        # switch to next
        w_curr = w_next
    #print "] (to", ass_count, "aliases)"
    return space.w_None
    
def _alias(space, w_v1, w_v2):
    """appends one var to the alias chain of another
       user must ensure freeness of both vars"""
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    #print "  :alias", w_v1, w_v2
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
    #print "   :add to aliases", w_v1, w_v2
    w_tail = w_v1.w_bound_to
    w_v1.w_bound_to = w_v2
    w_v2.w_bound_to = w_tail
    return space.w_None
    
def _merge_aliases(space, w_v1, w_v2):
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    #print "   :merge aliases", w_v1, w_v2
    w_tail1 = get_ring_tail(space, w_v1)
    w_tail2 = get_ring_tail(space, w_v2)
    w_tail1.w_bound_to = w_v2
    w_tail2.w_bound_to = w_v1
    return space.w_None

#-- UNIFY -------------------------

def unify(space, w_x, w_y):
    assert isinstance(w_x, W_Root)
    assert isinstance(w_y, W_Root)
    #print ":unify ", w_x, w_y
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
    #print " :unify of two vars"
    if space.is_true(space.is_bound(w_x)):
        if space.is_true(space.is_bound(w_y)):
            return space.unify(deref(space, w_x), 
                               deref(space, w_y))
        return bind(space, w_y, w_x)
    # binding or aliasing x & y
    else:
        return bind(space, w_x, w_y) 
    
def unify__Var_Root(space, w_x, w_y):
    #print " :unify var and value"
    if space.is_true(space.is_bound(w_x)):
        return space.unify(deref(space, w_x), w_y)            
    return bind(space, w_x, w_y)

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
    
## def _unify_iterables(space, w_i1, w_i2):
##     assert isinstance(w_i1, W_TupleObject) or isinstance(w_i1, W_ListObject)
##     assert isinstance(w_i2, W_TupleObject) or isinstance(w_i2, W_ListObject)
##     #print " :unify iterables", w_i1, w_i2

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
    def eq(w_obj1, w_obj2):
        assert isinstance(w_obj1, W_Root)
        assert isinstance(w_obj2, W_Root)
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(True)
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


#------ domains ------------------
from pypy.objspace.constraint import domain 
all_mms.update(domain.all_mms)

W_FiniteDomain = domain.W_FiniteDomain

#-------- computationspace --------
from pypy.objspace.constraint import computationspace
all_mms.update(computationspace.all_mms)

W_ComputationSpace = computationspace.W_ComputationSpace

# ---- constraints ----------------
from pypy.objspace.constraint import constraint
all_mms.update(constraint.all_mms)

#----- distributors ---------------
from pypy.objspace.constraint import distributor


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
    space.model.typeorder[W_FiniteDomain] = [(W_FiniteDomain, None), (W_Root, None)] 


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

    # provide a UnificationError exception
    space.ExceptionTable.append('UnificationError')
    space.ExceptionTable.sort() # hmmm

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
    #-- comp space ---
    space.setitem(space.builtin.w_dict, space.wrap('newspace'),
                 space.wrap(computationspace.app_newspace))
    #-- domain -------
    space.setitem(space.builtin.w_dict, space.wrap('FiniteDomain'),
                 space.wrap(domain.app_make_fd))
    space.setitem(space.builtin.w_dict, space.wrap('intersection'),
                 space.wrap(domain.app_intersection))
    #-- contraint ----
    space.setitem(space.builtin.w_dict, space.wrap('make_expression'),
                 space.wrap(constraint.app_make_expression))
    space.setitem(space.builtin.w_dict, space.wrap('AllDistinct'),
                 space.wrap(constraint.app_make_alldistinct))
    #-- distributor --
    space.setitem(space.builtin.w_dict, space.wrap('NaiveDistributor'),
                 space.wrap(distributor.app_make_naive_distributor))
    space.setitem(space.builtin.w_dict, space.wrap('SplitDistributor'),
                 space.wrap(distributor.app_make_split_distributor))
    space.setitem(space.builtin.w_dict, space.wrap('DichotomyDistributor'),
                 space.wrap(distributor.app_make_dichotomy_distributor))
    #-- path to the applevel modules --
    import pypy.objspace.constraint
    import os
    dir = os.path.dirname(pypy.objspace.constraint.__file__)
    dir = os.path.join(dir, 'applevel')
    space.call_method(space.sys.get('path'), 'append', space.wrap(dir))

    if USE_COROUTINES:
        import os
        # make sure that _stackless is imported
        w_modules = space.getbuiltinmodule('_stackless')
        def exitfunc():
            current = AppCoroutine.w_getcurrent(space)
            while schedule_state.have_runnable_threads():
                next_coro = schedule_state.pop_runnable_thread()
                if next_coro.is_alive() and next_coro != current:
                    schedule_state.add_to_runnable(current)
                    next_coro.w_switch()
                    schedule_state.remove_from_runnable(current)
            if schedule_state.have_blocked_threads():
                os.write(2, "there are still blocked uthreads!")
        app_exitfunc = gateway.interp2app(exitfunc, unwrap_spec=[])

        space.setitem(space.sys.w_dict, space.wrap("exitfunc"), space.wrap(app_exitfunc))
        space.setitem(space.builtin.w_dict, space.wrap('uthread'),
                     space.wrap(app_uthread))
        space.setitem(space.builtin.w_dict, space.wrap('wait'),
                     space.wrap(app_wait))
        space.setitem(space.builtin.w_dict, space.wrap('wait_needed'),
                      space.wrap(app_wait_needed))

    # capture a bunch of non-blocking ops
    space.is_nb_ = space.is_
        
    patch_space_in_place(space, 'logic', proxymaker)
    return space


