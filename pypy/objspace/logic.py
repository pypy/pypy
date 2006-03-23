from pypy.objspace.proxy import patch_space_in_place
from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError
from pypy.rpython.objectmodel import we_are_translated
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject

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
        w_self.w_bound_to = None # FIXME : make this a ring
        w_self.w_needed = False  # is it needed ?

    def __repr__(w_self):
        if w_self.w_bound_to:
            last = find_last_var_in_chain(w_self)
            if last.w_bound_to is not None:
                return '<%s@%s>' % (last.w_bound_to,
                                    prettyfy_id(str(id(w_self))))
        return '<?@%s>' % prettyfy_id(str(id(w_self)))

def find_last_var_in_chain(w_var):
    w_curr = w_var
    while 1:
        w_next = w_curr.w_bound_to
        if isinstance(w_next, W_Var):
            w_curr = w_next
        else:
            break
    return w_curr

def newvar(space):
    return W_Var()
app_newvar = gateway.interp2app(newvar)


def wait(space, w_self, w_caller=None):
    while 1:
        if not isinstance(w_self, W_Var):
            return w_self
        w_last = find_last_var_in_chain(w_self)
        w_obj = w_last.w_bound_to
        if w_obj is None:
            # XXX here we would have to suspend the current thread
            if not have_uthreads():
                raise OperationError(space.w_RuntimeError,
                                     space.wrap("trying to perform an operation on an unbound variable"))
            else:
                # notify wait_needed clients, give them a chance to run
                w_self.w_needed = True
                need_waiters = schedule_state.pop_blocked_byneed_on(w_self)
                for waiter in need_waiters:
                    schedule_state.add_to_runnable(waiter)
                # set curr thread to blocked, switch to runnable thread
                current = get_current_coroutine()
                schedule_state.add_to_blocked(w_last, current)
                while schedule_state.have_runnable_threads():
                    next_coro = schedule_state.pop_runnable_thread()
                    if next_coro.is_alive():
                        #print " waiter is switching"
                        try:
                            next_coro.switch()
                        except:
                            if w_caller: print "Wait", w_caller
                        #print " waiter is back"
                        # hope there is a value here now
                        break
                else:
                    raise OperationError(space.w_RuntimeError,
                                         space.wrap("blocked on variable, but no uthread that can bind it"))
        else:
            # actually attach the object directly to each variable
            # to remove indirections
            w_curr = w_self
            while 1:
                assert isinstance(w_curr, W_Var)
                w_next = w_curr.w_bound_to
                if not isinstance(w_next, W_Var):
                    break
                w_curr.w_bound_to = w_obj
                w_curr = w_next
            return w_obj
app_wait = gateway.interp2app(wait)

def wait_needed(space, w_self):
    while 1:
        if not isinstance(w_self, W_Var):
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("wait_needed operates only on logic variables"))
        w_last = find_last_var_in_chain(w_self)
        w_obj = w_last.w_bound_to
        if w_obj is None:
            if w_self.w_needed:
                break # we're done
            # XXX here we would have to FOO the current thread
            if not have_uthreads():
                raise OperationError(space.w_RuntimeError,
                                     space.wrap("oh please oh FIXME !"))
            else:
                # add current thread to blocked byneed and switch
                current = get_current_coroutine()
                schedule_state.add_to_blocked_byneed(w_self, current)
                while schedule_state.have_runnable_threads():
                    next_coro = schedule_state.pop_runnable_thread()
                    if next_coro.is_alive():
                        #print " byneed is switching"
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

def is_free(space, w_var):
    # XXX make me O(1)
    if not isinstance(w_var, W_Var):
        return space.newbool(False)
    w_last = find_last_var_in_chain(w_var)
    return space.newbool(space.is_w(w_last.w_bound_to, None))
app_is_free = gateway.interp2app(is_free)

def is_bound(space, w_var):
    # XXX make me O(1)
    # FIXME (i'm unreliable, where is_free is not)
    if space.is_true(is_free(space, w_var)):
        return space.newbool(False)
    else:
        return space.newbool(True)
app_is_bound = gateway.interp2app(is_bound)

def is_alias(space, w_var1, w_var2):
    assert space.is_true(is_free(space, w_var1))
    assert space.is_true(is_free(space, w_var2))
    # w_var2 could be a right-alias of w_var2
    # or the other way around
    a = _right_alias(space, w_var1, w_var2)
    b = _right_alias(space, w_var2, w_var1)
    return space.newbool(a or b)
app_is_alias = gateway.interp2app(is_alias)

def _right_alias(space, w_var1, w_var2):
    """checks wether a var is in the alias chain of another"""
    w_curr = w_var1.w_bound_to
    while w_curr != None:
        if space.is_true(space.is_nb_(w_curr, w_var2)):
            return True
        w_curr = w_curr.w_bound_to
    return False


#-- HELPERS ----------------------

def deref(space, w_var):
    """gets the value of a bound variable
       user has to ensure boundness of the var"""
    assert isinstance(w_var, W_Var)
    # FIXME don't need to walk the chain
    return find_last_var_in_chain(w_var).w_bound_to

def fail(space, w_obj1, w_obj2):
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

def aliases(space, w_var):
    al = []
    w_curr = w_var
    while w_curr is not None:
        al.append(w_curr)
        w_curr = w_curr.w_bound_to
    return al

def wait_two(space, w_1, w_2):
    """waits until one out of two logic variables
       becomes bound, then tells which one"""
    w_v = newvar(space)
    def sleep(space, w_var):
        wait(space, w_var)
        bind(space, w_var, space.newint(1))
    uthread(sleep, space, w_1)
    uthread(sleep, space, w_2)
    wait(space, w_c)
    if space.is_true(is_free(space, w_2)):
        return space.newint(1)
    return space.newint(2)

#-- BIND -----------------------------

def bind(space, w_var, w_obj):
    """1. aliasing of unbound variables
       2. assign unbound var to bound var
       3. assign value to self
    """
    print "bind", w_var, w_obj
    assert isinstance(w_var, W_Var)
    if isinstance(w_obj, W_Var):
        if space.is_true(is_bound(space, w_var)):
            if space.is_true(is_bound(space, w_obj)):
                unify(space,
                      deref(space, w_var),
                      deref(space, w_obj))
            _assign(space, w_obj, deref(space, w_var))
        elif space.is_true(is_bound(space, w_obj)):
            _assign(space, w_var, deref(space, w_obj))
        else: # 1. both are unbound
            _alias(space, w_var, w_obj)
    else: # 3. w_obj is a value
        if space.is_true(is_free(space, w_var)):
            _assign(space, w_var, w_obj)
        unify(space, deref(space, w_var), w_obj)
app_bind = gateway.interp2app(bind)

def _assign(space, w_var, w_val):
    w_curr = w_var
    while w_curr is not None:
        w_next = w_curr.w_bound_to
        w_curr.w_bound_to = w_val
        # awake the blocked threads
        to_awake = schedule_state.pop_blocked_on(w_curr)
        for thread in to_awake:
            schedule_state.add_to_runnable(thread)
        # switch to next
        w_curr = w_next
    return space.w_None
    
def _alias(space, w_v1, w_v2):
    """appends one var to the alias chain of another
       user must ensure freeness of both vars"""
    if space.is_true(space.is_nb_(w_v1, w_v2)):
        return space.w_None
    last = find_last_var_in_chain(w_v1)
    last.w_bound_to = w_v2
    return space.w_None

#-- UNIFY -------------------------

def unify(space, w_x, w_y):
    print "unify", w_x, w_y
    check_and_memoize_pair(space, w_x, w_y)
    if not isinstance(w_x, W_Var):
        if not isinstance(w_y, W_Var):
            # x, y not vars
            return _unify_values(space, w_x, w_y)
        # x not var, reverse args. order
        return unify(space, w_y, w_x)
    elif not isinstance(w_y, W_Var):
        # x var, y value
        return bind(space, w_x, w_y)
    # x, y are vars
    elif space.is_true(is_bound(space, w_x)) and \
         space.is_true(is_bound(space, w_x)):
        return _unify_values(space,
                             deref(space, w_x), 
                             deref(space, w_y))
    elif space.is_true(is_bound(space, w_x)):
        return bind(space, w_y, w_x)
    # aliasing x & y ?
    else:
        return bind(space, w_x, w_y) # aliasing
        #XXX: really do what's below :
        #return _unify_unbound(space, w_x, w_y)
    reset_memo()
app_unify = gateway.interp2app(unify)


def _unify_unbound(space, w_x, w_y):
    """sleeps until one of the two is bound
       then bind the other to its value"""
    w_bound = wait_two(space, w_x, w_y)
    if space.eq_w(w_bound, space.newint(1)):
        return bind(space, w_y, w_x)
    return bind(space, w_x, w_y)

def _unify_values(space, w_v1, w_v2):
    print " unify values", w_v1, w_v2
    # unify object of the same type ... FIXME
    if not space.is_w(space.type(w_v1),
                      space.type(w_v2)):
        fail(space, w_v1, w_v2)
    # ... elements of a list/tuple ...
    if isinstance(w_v1, W_ListObject) or \
       isinstance(w_v1, W_TupleObject):
        _unify_iterables(space, w_v1, w_v2)
    else:
        # ... token equality
        if not space.eq_w(w_v1, w_v2):
            fail(space, w_v1, w_v2)
        return space.w_None

def _unify_iterables(space, w_i1, w_i2):
    print " unify iterables", w_i1, w_i2
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
                if space.is_true(is_alias(space, w_obj1, w_obj2)):
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
                if space.is_true(is_alias(space, w_obj1, w_obj2)):
                    return space.newbool(0) # and just go on ...
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return cmp

def neproxy(space, parentfn):
    def ne(w_obj1, w_obj2):
        if space.is_true(is_free(space, w_obj1)) and \
           space.is_true(is_free(space, w_obj2)):
            w_var1 = find_last_var_in_chain(w_obj1)
            w_var2 = find_last_var_in_chain(w_obj2)
            if w_var1 is w_var2: # hmmm
                return space.w_False
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
            w1 = wait(space, w1, parentfn)
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


def Space(*args, **kwds):
    # for now, always make up a wrapped StdObjSpace
    from pypy.objspace import std
    space = std.Space(*args, **kwds)
    space.is_nb_ = space.is_ # capture the original is_ op
    patch_space_in_place(space, 'logic', proxymaker)
    space.setitem(space.builtin.w_dict, space.wrap('newvar'),
                  space.wrap(app_newvar))
    space.setitem(space.builtin.w_dict, space.wrap('is_free'),
                  space.wrap(app_is_free))
    space.setitem(space.builtin.w_dict, space.wrap('is_bound'),
                  space.wrap(app_is_bound))
    space.setitem(space.builtin.w_dict, space.wrap('is_alias'),
                  space.wrap(app_is_alias))
    space.setitem(space.builtin.w_dict, space.wrap('bind'),
                 space.wrap(app_bind))
    space.setitem(space.builtin.w_dict, space.wrap('unify'),
                 space.wrap(app_unify))
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
