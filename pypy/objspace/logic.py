from pypy.objspace.proxy import patch_space_in_place
from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError
from pypy.rpython.objectmodel import we_are_translated
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject
from pypy.objspace.std.dictobject import W_DictObject

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
    from pypy.module.stackless.interp_coroutine import Coroutine, AbstractThunk

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
            self.runnable_uthreads[uthread] = True

        def remove_from_runnable(self, uthread):
            del self.runnable_uthreads[uthread]

        def have_runnable_threads(self):
            return bool(self.runnable_uthreads)

        def have_blocked_threads(self):
            return bool(self.uthreads_blocked_on)

        def add_to_blocked(self, w_var, uthread):
            if w_var in self.uthreads_blocked_on:
                blocked = self.uthreads_blocked_on[w_var]
            else:
                blocked = []
                self.uthreads_blocked_on[w_var] = blocked
            blocked.append(uthread)

        def pop_blocked_on(self, w_var):
            if w_var not in self.uthreads_blocked_on:
                return []
            blocked = self.uthreads_blocked_on[w_var]
            del self.uthreads_blocked_on[w_var]
            return blocked

        def add_to_blocked_byneed(self, w_var, uthread):
            #print " adding", uthread, "to byneed on", w_var
            if w_var in self.uthreads_blocked_byneed:
                blocked = self.uthreads_blocked_byneed[w_var]
            else:
                blocked = []
                self.uthreads_blocked_byneed[w_var] = blocked
            blocked.append(uthread)

        def pop_blocked_byneed_on(self, w_var):
            if w_var not in self.uthreads_blocked_byneed:
                #print " there was nobody to remove for", w_var
                return []
            blocked = self.uthreads_blocked_byneed[w_var]
            del self.uthreads_blocked_byneed[w_var]
            #print " removing", blocked, "from byneed on", w_var
            return blocked


    schedule_state = ScheduleState()

    class Thunk(AbstractThunk):
        def __init__(self, space, w_callable, args, w_Result):
            self.space = space
            self.w_callable = w_callable
            self.args = args
            self.w_Result = w_Result # the upper-case R is because it is a logic variable

        def call(self):
            bind(self.space, self.w_Result,
                 self.space.call_args(self.w_callable, self.args))

    class GreenletCoroutine(object):
        def bind(self, thunk):
            self.greenlet = greenlet(thunk.call)

        def switch(self):
            self.greenlet.switch()

        def is_alive(self):
            return bool(self.greenlet)

        def getcurrent():
            result = GreenletCoroutine()
            result.greenlet = greenlet.getcurrent()
            return result
        getcurrent = staticmethod(getcurrent)

        def __hash__(self):
            return hash(self.greenlet)

        def __eq__(self, other):
            return self.greenlet == other.greenlet

        def __ne__(self, other):
            return not (self == other)

        def __repr__(self):
            return '<greenlet %s>' % id(self)

    def construct_coroutine():
        if we_are_translated():
            return Coroutine()
        else:
            return GreenletCoroutine()

    def get_current_coroutine():
        if we_are_translated():
            return Coroutine.getcurrent()
        else:
            return GreenletCoroutine.getcurrent()

    def uthread(space, w_callable, __args__):
        args = __args__.normalize()
        w_Result = W_Var()
        thunk = Thunk(space, w_callable, args, w_Result)
        coro = construct_coroutine()
        coro.bind(thunk)
        current = get_current_coroutine()
        schedule_state.add_to_runnable(current)
        coro.switch()
        while schedule_state.have_runnable_threads():
            next_coro = schedule_state.pop_runnable_thread()
            if next_coro.is_alive() and next_coro != current:
                schedule_state.add_to_runnable(current)
                next_coro.switch()
        return w_Result
    app_uthread = gateway.interp2app(uthread, unwrap_spec=[baseobjspace.ObjSpace,
                                                           baseobjspace.W_Root,
                                                           argument.Arguments])
    

#-- VARIABLE ---------------------

class W_Var(baseobjspace.W_Root, object):
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

def wait(space, w_self):
    while 1:
        if not isinstance(w_self, W_Var):
            return w_self
        print " :wait", w_self
        if space.is_true(is_free(space, w_self)):
            if not have_uthreads():
                raise OperationError(space.w_RuntimeError,
                                     space.wrap("trying to perform an operation on an unbound variable"))
            else:
                # notify wait_needed clients, give them a chance to run
                w_self.w_needed = True
                for w_alias in aliases(space, w_self):
                    need_waiters = schedule_state.pop_blocked_byneed_on(w_alias)
                    w_alias.w_needed = True
                    for waiter in need_waiters:
                        print "  :byneed waiter", waiter, "awaken on", w_alias
                        schedule_state.add_to_runnable(waiter)
                # set curr thread to blocked, switch to runnable thread
                current = get_current_coroutine()
                schedule_state.add_to_blocked(w_self, current)
                while schedule_state.have_runnable_threads():
                    next_coro = schedule_state.pop_runnable_thread()
                    if next_coro.is_alive():
                        print "  :waiter is switching"
                        next_coro.switch()
                        #print " waiter is back"
                        # hope there is a value here now
                        break
                else:
                    raise OperationError(space.w_RuntimeError,
                                         space.wrap("blocked on variable, but no uthread that can bind it"))
        else:
            return w_self.w_bound_to
app_wait = gateway.interp2app(wait)

def wait_needed(space, w_self):
    while 1:
        if not isinstance(w_self, W_Var):
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("wait_needed operates only on logic variables"))
        print " :needed", w_self
        if space.is_true(is_free(space, w_self)):
            if w_self.w_needed:
                break # we're done
            if not have_uthreads():
                raise OperationError(space.w_RuntimeError,
                                     space.wrap("oh please oh FIXME !"))
            else:
                # add current thread to blocked byneed and switch
                current = get_current_coroutine()
                for w_alias in aliases(space, w_self):
                    schedule_state.add_to_blocked_byneed(w_alias, current)
                while schedule_state.have_runnable_threads():
                    next_coro = schedule_state.pop_runnable_thread()
                    if next_coro.is_alive():
                        print "  :needed is switching"
                        next_coro.switch()
                        #print " byneed is back"
                        # there might be some need right now
                        break
                else:
                    raise OperationError(space.w_RuntimeError,
                                         space.wrap("blocked on need, but no uthread that can wait"))
            
        else:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("wait_needed only supported on unbound variables"))
app_wait_needed = gateway.interp2app(wait_needed)            


#-- PREDICATES --------------------

def is_aliased(space, w_var): # FIXME: this appears to block
    if space.is_true(space.is_nb_(deref(space, w_var), w_var)):
        return space.newbool(False)
    return space.newbool(True)
app_is_aliased = gateway.interp2app(is_aliased)

def is_free(space, w_var):
    if not isinstance(w_var, W_Var):
        return space.newbool(False)
    return space.newbool(isinstance(w_var.w_bound_to, W_Var))
app_is_free = gateway.interp2app(is_free)

def is_bound(space, w_var):
    return space.newbool(not space.is_true(is_free(space, w_var)))
app_is_bound = gateway.interp2app(is_bound)


def alias_of(space, w_var1, w_var2): # FIXME: appears to block
    assert space.is_true(is_free(space, w_var1))
    assert space.is_true(is_free(space, w_var2))
    # w_var2 could be a right-alias of w_var2
    # or the other way around
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

def disp(space, w_var):
    print w_var
app_disp = gateway.interp2app(disp)

def disp_aliases(space, w_var):
    print "Aliases of ", w_var, "are", 
    for w_al in aliases(space, w_var):
        print w_al,
    print

def deref(space, w_var):
    """gets the value of a bound variable
       user has to ensure boundness of the var"""
    assert isinstance(w_var, W_Var)
    return w_var.w_bound_to

def aliases(space, w_var):
    """return the aliases of a var, including itself"""
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
    w_curr = w_start
    while 1:
        w_next = w_curr.w_bound_to
        if space.is_true(space.is_nb_(w_next, w_start)):
            return w_curr
        w_curr = w_next


def fail(space, w_obj1, w_obj2):
    """raises a specific exception for bind/unify"""
    print "can't unify", w_obj1, w_obj2
    raise OperationError(space.w_RuntimeError,
                         space.wrap("UnificationFailure"))

def check_and_memoize_pair(space, w_x, w_y):
    pass

def reset_memo():
    pass

def prettyfy_id(a_str):
    l = len(a_str) - 1
    return a_str[l-3:l]

def _sleep(space, w_var, w_barrier):
    wait(space, w_var)
    bind(space, w_barrier, space.newint(1))
#app_sleep = gateway.interp2app(sleep)

def wait_two(space, w_1, w_2):
    """waits until one out of two logic variables
       becomes bound, then tells which one,
       with a bias toward the first if both are
       suddenly bound"""
    w_barrier = newvar(space)
    uthread(space, space.wrap(_sleep),
            argument.Arguments(space, [w_1, w_barrier]))
    uthread(space, space.wrap(_sleep),
            argument.Arguments(space, [w_2, w_barrier]))
    wait(space, w_barrier)
    if space.is_true(is_free(space, w_2)):
        return space.newint(1)
    return space.newint(2)
app_wait_two = gateway.interp2app(wait_two)

#-- BIND -----------------------------

def bind(space, w_var, w_obj):
    """1. aliasing of unbound variables
       2. assign bound var to unbound var
       3. assign value to unbound var
    """
    print " :bind", w_var, w_obj
    assert isinstance(w_var, W_Var)
    if isinstance(w_obj, W_Var):
        if space.is_true(is_bound(space, w_var)):
            if space.is_true(is_bound(space, w_obj)):
                return unify(space, 
                             deref(space, w_var),
                             deref(space, w_obj))
            # 2. a (obj unbound, var bound)
            return _assign(space, w_obj, deref(space, w_var))
        elif space.is_true(is_bound(space, w_obj)):
            # 2. b (var unbound, obj bound)
            return _assign(space, w_var, deref(space, w_obj))
        else: # 1. both are unbound
            return _alias(space, w_var, w_obj)
    else: # 3. w_obj is a value
        if space.is_true(is_free(space, w_var)):
            return _assign(space, w_var, w_obj)
        # should not be reachable as of 27-03-2006
        raise OperationError(space.w_RuntimeError,
                             space.wrap("Unreachable code in bind"))
app_bind = gateway.interp2app(bind)

def _assign(space, w_var, w_val):
    print "  :assign", w_var, w_val, '[',
    w_curr = w_var
    ass_count = 0
    while 1:
        w_next = w_curr.w_bound_to
        w_curr.w_bound_to = w_val
        print w_curr, 
        ass_count += 1
        # notify the blocked threads
        to_awake = schedule_state.pop_blocked_on(w_curr)
        for thread in to_awake:
            schedule_state.add_to_runnable(thread)
        if space.is_true(space.is_nb_(w_next, w_var)):
            break
        # switch to next
        w_curr = w_next
    print "] (to", ass_count, "aliases)"
    return space.w_None
    
def _alias(space, w_v1, w_v2):
    """appends one var to the alias chain of another
       user must ensure freeness of both vars"""
    print "  :alias", w_v1, w_v2
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
    print "   :add to aliases", w_v1, w_v2
    w_tail = w_v1.w_bound_to
    w_v1.w_bound_to = w_v2
    w_v2.w_bound_to = w_tail
    return space.w_None
    
def _merge_aliases(space, w_v1, w_v2):
    print "   :merge aliases", w_v1, w_v2
    w_tail1 = get_ring_tail(space, w_v1)
    w_tail2 = get_ring_tail(space, w_v2)
    w_tail1.w_bound_to = w_v2
    w_tail2.w_bound_to = w_v1
    return space.w_None

#-- UNIFY -------------------------

def unify(space, w_x, w_y):
    print " :unify", w_x, w_y
    check_and_memoize_pair(space, w_x, w_y)
    if not isinstance(w_x, W_Var):
        if not isinstance(w_y, W_Var):
            # x, y not vars
            return _unify_values(space, w_x, w_y)
        # x not var, reverse args. order
        return unify(space, w_y, w_x)
    elif not isinstance(w_y, W_Var):
        # x var, y value
        if space.is_true(is_bound(space, w_x)):
            return unify(space, deref(space, w_x), w_y)            
        return bind(space, w_x, w_y)
    # x, y are vars
    elif space.is_true(is_bound(space, w_x)):
        if space.is_true(is_bound(space, w_y)):
            return _unify_values(space,
                                 deref(space, w_x), 
                                 deref(space, w_y))
        return bind(space, w_y, w_x)
    # aliasing x & y ?
    else:
        return bind(space, w_x, w_y) # aliasing
    reset_memo()
app_unify = gateway.interp2app(unify)

    
def _unify_values(space, w_v1, w_v2):
    print "  :unify values", w_v1, w_v2
    # unify object of the same type ... FIXME
    if not space.is_w(space.type(w_v1),
                      space.type(w_v2)):
        fail(space, w_v1, w_v2)
    # ... elements of a list/tuple ...
    if (isinstance(w_v1, W_ListObject) and \
        isinstance(w_v2, W_ListObject)) or \
        (isinstance(w_v1, W_TupleObject) and \
         isinstance(w_v1, W_TupleObject)):
        return _unify_iterables(space, w_v1, w_v2)
    elif isinstance(w_v1, W_DictObject) and \
        isinstance(w_v1, W_DictObject):
        return _unify_mappings(space, w_v1, w_v2)
        # ... token equality
    if not space.eq_w(w_v1, w_v2):
        return _unify_instances(space, w_v1, w_v2)
        #fail(space, w_v1, w_v2)
    return space.w_None

def _unify_instances(space, w_i1, w_i2):
    print "   :unify instances"
    return _unify_mappings(space,
                           w_i1.getdict(),
                           w_i2.getdict())

def _unify_iterables(space, w_i1, w_i2):
    print "   :unify iterables", w_i1, w_i2
    # assert lengths
    if len(w_i1.wrappeditems) != len(w_i2.wrappeditems):
        fail(space, w_i1, w_i2)
    # co-iterate and unify elts
    idx, top = (-1, space.int_w(space.len(w_i1))-1)
    while idx < top:
        idx += 1
        w_xi = space.getitem(w_i1, space.newint(idx))
        w_yi = space.getitem(w_i2, space.newint(idx))
        if space.is_true(space.is_nb_(w_xi, w_yi)):
            continue
        unify(space, w_xi, w_yi)

def _unify_mappings(space, w_m1, w_m2):
    print "   :unify mappings", w_m1, w_m2
##     if len(w_m1.wrappeditems) != len(w_m2.wrappeditems):
##         fail(space, w_i1, w_i2)
    for w_xk in w_m1.content.keys():
        w_xi = space.getitem(w_m1, w_xk)
        w_yi = space.getitem(w_m2, w_xk)
        if space.is_true(space.is_nb_(w_xi, w_yi)):
            continue
        unify(space, w_xi, w_yi)
        
        

# multimethod version of unify
## def unify__W_Var_W_Var(space, w_v1, w_v2):
##     return bind(space, w_v1, w_v2)
    
## def unify__W_Var_W_ObjectObject(space, w_var, w_obj):
##     return bind(space, w_v1, w_obj)

## def unify_W_ObjectObject_W_Var(space, w_obj, w_var):
##     return unify__W_Var_W_ObjectObject(space, w_var, w_obj)

## def unify__W_ObjectObject_W_ObjectObject(space, w_obj1, w_obj2):
##     if not space.eq(w_obj1, w_obj2):
##         fail(space, w_obj1, w_obj2)
##     return space.w_None

## def unify__W_ListObject_W_ListObject(space, w_list1, w_list2):
##     if len(w_list1) != len(w_list2): # .wrappeditems ?
##         fail(space, w_list1, w_list2)
##     for e1, e2 in zip(w_list1, w_list2): # .wrappeditems ?
##         space.wrap(unify(space, e1, e2)) # ... ?

# questions : how to make this available to applevel ?


# __________________________________________________________________________

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
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(True)
        if space.is_true(is_free(space, w_obj1)):
            if space.is_true(is_free(space, w_obj2)):
                if space.is_true(alias_of(space, w_obj1, w_obj2)):
                    return space.newbool(True) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return eq

def isproxy(space, parentfn):
    def is_(w_obj1, w_obj2):
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(True)
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return is_

def cmpproxy(space, parentfn):
    def cmp(w_obj1, w_obj2):
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(0)
        if space.is_true(is_free(space, w_obj1)):
            if space.is_true(is_free(space, w_obj2)):
                if space.is_true(alias_of(space, w_obj1, w_obj2)):
                    return space.newbool(0) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return cmp

def neproxy(space, parentfn):
    def ne(w_obj1, w_obj2):
        if space.is_true(space.is_nb_(w_obj1, w_obj2)):
            return space.newbool(False)
        if space.is_true(is_free(space, w_obj1)):
            if space.is_true(is_free(space, w_obj2)):
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




from pypy.objspace.std.model import StdObjSpaceMultiMethod
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std import stdtypedef 
from pypy.tool.sourcetools import func_with_new_name

def foo__Int_Int(space, w_a, w_b):
    print "i'm foo int int"

def foo__Int_Float(space, w_a, w_b):
    print "i'm foo int float"

def foo__Float_Int(space, w_a, w_b):
    space.foo(w_b, w_a)


foo_mm = StdObjSpaceMultiMethod('foo', 2)
foo_mm.register(foo__Int_Int, W_IntObject, W_IntObject)
foo_mm.register(foo__Int_Float, W_IntObject, W_FloatObject)
foo_mm.register(foo__Float_Int, W_FloatObject, W_IntObject)

def my_foo(space, w_1, w_2):
    space.foo(w_1, w_2)
app_foo = gateway.interp2app(my_foo)

def Space(*args, **kwds):
    # for now, always make up a wrapped StdObjSpace
    from pypy.objspace import std
    space = std.Space(*args, **kwds)

    # multimethods hack
    name = 'foo'
    exprargs, expr, miniglobals, fallback = (
        foo_mm.install_not_sliced(space.model.typeorder, baked_perform_call=False))
    func = stdtypedef.make_perform_trampoline('__foo_mm_'+name,
                                              exprargs, expr, miniglobals,
                                              foo_mm)
    # e.g. add(space, w_x, w_y)
    def make_boundmethod(func=func):
        def boundmethod(*args):
            return func(space, *args)
        return func_with_new_name(boundmethod, 'boundmethod_'+name)
    boundmethod = make_boundmethod()
    setattr(space, name, boundmethod)  # store into 'space' instance
    # /multimethod hack


    is_nb_ = space.is_ # capture the original is_ op (?)
    patch_space_in_place(space, 'logic', proxymaker)
    space.is_nb_ = is_nb_
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
    space.setitem(space.builtin.w_dict, space.wrap('disp'),
                 space.wrap(app_disp))
    space.setitem(space.builtin.w_dict, space.wrap('bind'),
                 space.wrap(app_bind))
    space.setitem(space.builtin.w_dict, space.wrap('unify'),
                 space.wrap(app_unify))
    space.setitem(space.builtin.w_dict, space.wrap('foo'),
                 space.wrap(app_foo))
    if USE_COROUTINES:
        import os
        def exitfunc():
            current = get_current_coroutine()
            while schedule_state.have_runnable_threads():
                next_coro = schedule_state.pop_runnable_thread()
                if next_coro.is_alive and next_coro != current:
                    schedule_state.add_to_runnable(current)
                    next_coro.switch()
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
    return space

