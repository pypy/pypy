from pypy.objspace.proxy import patch_space_in_place
from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError
from pypy.objspace.thunk import nb_forcing_args

# __________________________________________________________________________

class W_Var(baseobjspace.W_Root, object):
    def __init__(w_self):
        w_self.w_bound_to = None


def force(space, w_self):
    if not isinstance(w_self, W_Var):
        return w_self
    w_bound_to = w_self.w_bound_to
    while isinstance(w_bound_to, W_Var):
        w_bound_to = w_bound_to.w_bound_to
    if w_bound_to is None:
        # XXX here we would have to suspend the current thread
        raise OperationError(space.w_ValueError,
                             space.wrap("trying to perform an operation on an unbound variable"))
    else:
        # actually attach the object directly to each variable
        # to remove indirections
        w_obj = w_bound_to
        w_curr = w_self
        while w_curr.w_bound_to is not w_obj:
            w_next = w_curr.w_bound_to
            w_curr.w_bound_to = w_obj
            w_curr = w_next
        return w_obj

def newvar(space):
    return W_Var()
app_newvar = gateway.interp2app(newvar)

def is_unbound(space, w_var):
    if not isinstance(w_var, W_Var):
        return space.newbool(False)
    w_curr = w_var
    while isinstance(w_curr, W_Var):
        w_curr = w_curr.w_bound_to
    return space.newbool(w_curr is None)
app_is_unbound = gateway.interp2app(is_unbound)

def bind(space, w_var, w_obj):
    if not space.is_true(is_unbound(space, w_var)):
        raise OperationError(space.w_TypeError,
                             space.wrap("can only bind unbound logic variable"))
    w_curr = w_var
    while w_curr is not None:
        w_next = w_curr.w_bound_to
        w_curr.w_bound_to = w_obj
        w_curr = w_next
    return space.w_None
app_bind = gateway.interp2app(bind)


# __________________________________________________________________________

def proxymaker(space, opname, parentfn):
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
    return space
