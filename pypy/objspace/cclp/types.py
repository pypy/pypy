from pypy.interpreter import baseobjspace
from pypy.module._stackless.interp_clonable import Coroutine, ClonableCoroutine

W_Root = baseobjspace.W_Root

#-- Types --------------------------------------------------

class W_Var(W_Root, object):
    def __init__(w_self, space):
        # ring of aliases or bound value
        w_self.w_bound_to = w_self
        # byneed flag
        w_self.needed = False

    def __repr__(w_self):
        if isinstance(w_self.w_bound_to, W_Var):
            return '<?@%s>' % prettyfy_id(id(w_self))
        return '<%s@%s>' % (w_self.w_bound_to,
                            prettyfy_id(id(w_self)))
    __str__ = __repr__

class W_Future(W_Var):
    "a read-only-by-its-consummer variant of logic. var"
    def __init__(w_self, space):
        W_Var.__init__(w_self, space)
        w_self.client = ClonableCoroutine.w_getcurrent(space)

class W_FailedValue(W_Root, object):
    """wraps an exception raised in some coro, to be re-raised in
       some dependant coro sometime later
    """
    def __init__(w_self, exc):
        w_self.exc = exc

#-- Misc ----------------------------------------------------

def deref(space, w_var):
    #XXX kill me ?
    "gets the value/next alias of a variable"
    assert isinstance(w_var, W_Var)
    return w_var.w_bound_to

def aliases(space, w_var):
    """return the aliases of a var, including itself"""
    assert isinstance(w_var, W_Var)
    assert isinstance(w_var.w_bound_to, W_Var)
    al = []
    w_curr = w_var
    while 1:
        w_next = w_curr.w_bound_to
        al.append(w_curr)
        if space.is_true(space.is_nb_(w_next, w_var)):
            break
        w_curr = w_next
    return al

def prettyfy_id(an_int):
    "gets the 3 lower digits of an int"
    assert isinstance(an_int, int)
    a_str = str(an_int)
    l = len(a_str) - 1
    return a_str[l-3:l]
