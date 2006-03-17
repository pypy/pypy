from pypy.objspace.proxy import patch_space_in_place
from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError
from pypy.rpython.objectmodel import we_are_translated

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
            print " adding", uthread, "to byneed on", w_var
            if w_var in self.uthreads_blocked_byneed:
                blocked = self.uthreads_blocked_byneed[w_var]
            else:
                blocked = []
                self.uthreads_blocked_byneed[w_var] = blocked
            blocked.append(uthread)

        def pop_blocked_byneed_on(self, w_var):
            if w_var not in self.uthreads_blocked_byneed:
                print " there was nobody to remove for", w_var
                return []
            blocked = self.uthreads_blocked_byneed[w_var]
            del self.uthreads_blocked_byneed[w_var]
            print " removing", blocked, "from byneed on", w_var
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


class W_Var(baseobjspace.W_Root, object):
    def __init__(w_self):
        w_self.w_bound_to = None
        w_self.w_needed = False

def find_last_var_in_chain(w_var):
    w_curr = w_var
    while 1:
        w_next = w_curr.w_bound_to
        if isinstance(w_next, W_Var):
            w_curr = w_next
        else:
            break
    return w_curr

def wait(space, w_self):
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
                        print " waiter is switching"
                        next_coro.switch()
                        print " waiter is back"
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
                        print " byneed is switching"
                        next_coro.switch()
                        print " byneed is back"
                        # there might be some need right now
                        break
                else:
                    raise OperationError(space.w_RuntimeError,
                                         space.wrap("blocked on need, but no uthread that can wait"))
            
        else:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("wait_needed only supported on unbound variables"))
app_wait_needed = gateway.interp2app(wait_needed)            


def newvar(space):
    return W_Var()
app_newvar = gateway.interp2app(newvar)

def is_unbound(space, w_var):
    if not isinstance(w_var, W_Var):
        return space.newbool(False)
    w_last = find_last_var_in_chain(w_var)
    return space.newbool(w_last.w_bound_to is None)
app_is_unbound = gateway.interp2app(is_unbound)

def bind(space, w_var, w_obj):
    if not isinstance(w_var, W_Var):
        raise OperationError(space.w_TypeError,
                             space.wrap("can only bind logic variable"))
    w_last = find_last_var_in_chain(w_var)
    if w_last.w_bound_to is not None:
         raise OperationError(space.w_TypeError,
                              space.wrap("can only bind unbound logic variable"))
    if isinstance(w_obj, W_Var):
        w_last2 = find_last_var_in_chain(w_obj)
        if w_last2.w_bound_to is not None:
            w_obj = w_last2
        elif w_last is w_last2:
            return space.w_None
        else:
            w_last.w_bound_to = w_last2
            return
    w_curr = w_var
    while w_curr is not None:
        assert isinstance(w_curr, W_Var)
        w_next = w_curr.w_bound_to
        w_curr.w_bound_to = w_obj
        w_curr = w_next
    if have_uthreads():
        now_unblocked_uthreads = schedule_state.pop_blocked_on(w_last)
        for uthread in now_unblocked_uthreads:
            schedule_state.add_to_runnable(uthread)
    return space.w_None
app_bind = gateway.interp2app(bind)


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

def isoreqproxy(space, parentfn):
    def isoreq(w_obj1, w_obj2):
        if space.is_true(is_unbound(space, w_obj1)):
            bind(space, w_obj1, w_obj2)
            return space.w_True
        if space.is_true(is_unbound(space, w_obj2)):
            bind(space, w_obj2, w_obj1)
            return space.w_True
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return isoreq

def cmpproxy(space, parentfn):
    def cmp(w_obj1, w_obj2):
        if space.is_true(is_unbound(space, w_obj1)):
            bind(space, w_obj1, w_obj2)
            return space.wrap(0)
        if space.is_true(is_unbound(space, w_obj2)):
            bind(space, w_obj2, w_obj1)
            return space.wrap(0)
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return cmp

def neproxy(space, parentfn):
    def ne(w_obj1, w_obj2):
        if (isinstance(w_obj1, W_Var) and isinstance(w_obj2, W_Var) and 
            space.is_true(is_unbound(space, w_obj1)) and
            space.is_true(is_unbound(space, w_obj2))):
            w_var1 = find_last_var_in_chain(w_obj1)
            w_var2 = find_last_var_in_chain(w_obj2)
            if w_var1 is w_var2:
                return space.w_False
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return ne

def is_wproxy(space, parentfn):
    def is_w(w_obj1, w_obj2):
        if space.is_true(is_unbound(space, w_obj1)):
            bind(space, w_obj1, w_obj2)
            return True
        if space.is_true(is_unbound(space, w_obj2)):
            bind(space, w_obj2, w_obj1)
            return True
        return parentfn(wait(space, w_obj1), wait(space, w_obj2))
    return is_w

def proxymaker(space, opname, parentfn):
    if opname == "is_w":
        return is_wproxy(space, parentfn)
    if opname == "eq" or opname == "is_":
        return isoreqproxy(space, parentfn)
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

def Space(*args, **kwds):
    # for now, always make up a wrapped StdObjSpace
    from pypy.objspace import std
    space = std.Space(*args, **kwds)
    patch_space_in_place(space, 'logic', proxymaker)
    space.setitem(space.builtin.w_dict, space.wrap('newvar'),
                  space.wrap(app_newvar))
    space.setitem(space.builtin.w_dict, space.wrap('is_unbound'),
                  space.wrap(app_is_unbound))
    space.setitem(space.builtin.w_dict, space.wrap('bind'),
                 space.wrap(app_bind))
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
