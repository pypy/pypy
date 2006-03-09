from pypy.objspace.proxy import patch_space_in_place
from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError

USE_GREENLETS = False
try:
    from py.magic import greenlet
except ImportError:
    USE_GREENLETS = False

if USE_GREENLETS:
    runnable_uthreads = {}
    uthreads_blocked_on = {}
    main_greenlet = greenlet.getcurrent()

    def uthread(space, w_callable, __args__):
        w_Result = W_Var()
        def run():
            space.eq(w_Result, space.call_args(w_callable, __args__))
        gr = greenlet(run)
        current = greenlet.getcurrent()
        runnable_uthreads[current] = True
        gr.switch()
        while runnable_uthreads:
            next_greenlet, _ = runnable_uthreads.popitem()
            if next_greenlet and next_greenlet is not current:
                runnable_uthreads[current] = True
                next_greenlet.switch()
        return w_Result
    app_uthread = gateway.interp2app(uthread, unwrap_spec=[baseobjspace.ObjSpace,
                                                           baseobjspace.W_Root,
                                                           argument.Arguments])

class W_Var(baseobjspace.W_Root, object):
    def __init__(w_self):
        w_self.w_bound_to = None

def find_last_var_in_chain(w_var):
    w_curr = w_var
    while 1:
        w_next = w_curr.w_bound_to
        if isinstance(w_next, W_Var):
            w_curr = w_next
        else:
            break
    return w_curr

def force(space, w_self):
    while 1:
        if not isinstance(w_self, W_Var):
            return w_self
        w_last = find_last_var_in_chain(w_self)
        w_obj = w_last.w_bound_to
        if w_obj is None:
            # XXX here we would have to suspend the current thread
            if not USE_GREENLETS:
                raise OperationError(space.w_RuntimeError,
                                     space.wrap("trying to perform an operation on an unbound variable"))
            else:
                current = greenlet.getcurrent()
                uthreads_blocked_on.setdefault(w_last, []).append(current)
                while runnable_uthreads:
                    next_greenlet, _ = runnable_uthreads.popitem()
                    if next_greenlet:
                        next_greenlet.switch()
                        # there is a value here now
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
    if USE_GREENLETS:
        now_unblocked_uthreads = uthreads_blocked_on.pop(w_last, [])
        for uthread in now_unblocked_uthreads:
            runnable_uthreads[uthread] = True
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
        return parentfn(force(space, w_obj1), force(space, w_obj2))
    return isoreq

def cmpproxy(space, parentfn):
    def cmp(w_obj1, w_obj2):
        if space.is_true(is_unbound(space, w_obj1)):
            bind(space, w_obj1, w_obj2)
            return space.wrap(0)
        if space.is_true(is_unbound(space, w_obj2)):
            bind(space, w_obj2, w_obj1)
            return space.wrap(0)
        return parentfn(force(space, w_obj1), force(space, w_obj2))
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
        return parentfn(force(space, w_obj1), force(space, w_obj2))
    return ne

def is_wproxy(space, parentfn):
    def is_w(w_obj1, w_obj2):
        if space.is_true(is_unbound(space, w_obj1)):
            bind(space, w_obj1, w_obj2)
            return True
        if space.is_true(is_unbound(space, w_obj2)):
            bind(space, w_obj2, w_obj1)
            return True
        return parentfn(force(space, w_obj1), force(space, w_obj2))
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
            w1 = force(space, w1)
            return parentfn(w1, *extra)
    elif nb_args == 2:
        def proxy(w1, w2, *extra):
            w1 = force(space, w1)
            w2 = force(space, w2)
            return parentfn(w1, w2, *extra)
    elif nb_args == 3:
        def proxy(w1, w2, w3, *extra):
            w1 = force(space, w1)
            w2 = force(space, w2)
            w3 = force(space, w3)
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
    if USE_GREENLETS:
        def exitfunc():
            current = greenlet.getcurrent()
            while runnable_uthreads:
                next_greenlet, _ = runnable_uthreads.popitem()
                if next_greenlet and next_greenlet is not current:
                    runnable_uthreads[current] = True
                    next_greenlet.switch()
                    del runnable_uthreads[current]
            if uthreads_blocked_on:
                print "there are still blocked uthreads!"
                for var, blocked in uthreads_blocked_on.iteritems():
                    print var, blocked
                assert 0
        app_exitfunc = gateway.interp2app(exitfunc, unwrap_spec=[])
        space.setitem(space.sys.w_dict, space.wrap("exitfunc"), space.wrap(app_exitfunc))
        space.setitem(space.builtin.w_dict, space.wrap('uthread'),
                     space.wrap(app_uthread))
    return space
