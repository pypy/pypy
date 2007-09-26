from pypy.interpreter import baseobjspace, gateway, typedef
from pypy.interpreter.error import OperationError
from pypy.module._stackless.interp_clonable import AppClonableCoroutine

from pypy.module.cclp.misc import w, AppCoroutine, get_current_cspace
from pypy.module.cclp.global_state import sched

from pypy.rlib.rgc import gc_swap_pool, gc_clone
from pypy.rlib.objectmodel import we_are_translated

W_Root = baseobjspace.W_Root

#-- Variables types ----------------------------------------

class W_Var(W_Root):
    def __init__(w_self, space):
        # ring of aliases or bound value
        w_self.w_bound_to = w_self
        w_self.entails = {}
        # byneed flag
        w_self.needed = False

    def __repr__(w_self):
        if isinstance(w_self.w_bound_to, W_Var):
            return '<?@%x>' % id(w_self)
        return '<%s@%x>' % (w_self.w_bound_to,
                            id(w_self))

    def _same_as(w_self, w_var):
        assert isinstance(w_var, W_Var)
        return w_self is w_var
    __str__ = __repr__


class W_Future(W_Var):
    "a read-only-by-its-consummer variant of logic. var"
    def __init__(w_self, space):
        W_Var.__init__(w_self, space)
        w_self._client = AppCoroutine.w_getcurrent(space)
        w("FUT", str(w_self))


from pypy.module._cslib import fd

class W_CVar(W_Var):
    def __init__(self, space, w_dom, w_name):
        assert isinstance(w_dom, fd.W_FiniteDomain)
        W_Var.__init__(self, space)
        self.w_dom = w_dom
        self.name = space.str_w(w_name)
        self.w_nam = w_name
        get_current_cspace(space).register_var(self)

    def copy(self, space):
        return W_CVar(space, self.w_dom.copy(), self.w_nam)

    def name_w(self):
        return self.name

    def w_name(self):
        return self.w_nam

    def assign(self, w_var):
        if not w_var.w_dom.contains(w_val):
            raise ValueError, "assignment out of domain"
        w_var.w_bound_to = w_val


def domain_of(space, w_v):
    if not isinstance(w_v, W_CVar):
        raise OperationError(space.w_TypeError,
                             space.wrap("domain_of takes a constraint variable"))
    return w_v.w_dom
app_domain_of = gateway.interp2app(domain_of)

def name_of(space, w_v):
    if not isinstance(w_v, W_CVar):
        raise OperationError(space.w_TypeError,
                             space.wrap("name_of takes a constraint variable"))
    return w_v.w_name()
app_name_of = gateway.interp2app(name_of)

#-- Exception types ----------------------------------------

class W_FailedValue(W_Root):
    """wraps an exception raised in some coro, to be re-raised in
       some dependant coro sometime later
    """
    def __init__(w_self, exc):
        w_self.exc = exc

class ConsistencyError(Exception): pass

class Solution(Exception): pass

class FailedSpace(Exception): pass

#-- Ring (used by scheduling entities)

class RingMixin(object):
    _mixin_ = True
    """
    useless till we can give a type parameter
    """
    
    def init_head(self, head):
        self._head = head
        head._next = head._prev = head
        self._count = 1

    def chain_insert(self, obj):
        r = self._head
        l = r._prev
        l._next = obj
        r._prev = obj
        obj._prev = l
        obj._next = r

    def remove(self, obj):
        l = obj._prev
        r = obj._next
        l._next = r
        r._prev = l
        if self._head == obj:
            self._head = r
        if r == obj:
            # that means obj was the last one
            # the group is about to die
            self._head = None
        obj._next = obj._prev = None
          

#-- Misc ---------------------------------------------------

def deref(space, w_var):
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
        assert isinstance(w_next, W_Var)
        al.append(w_curr)
        if space.is_true(space.is_nb_(w_next, w_var)):
            break
        w_curr = w_next
    return al

