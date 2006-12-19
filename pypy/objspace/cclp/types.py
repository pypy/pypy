from pypy.interpreter import baseobjspace, gateway, typedef
from pypy.interpreter.error import OperationError

from pypy.objspace.cclp.misc import w, AppCoroutine, get_current_cspace
from pypy.objspace.cclp.global_state import sched

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
            return '<?@%s>' % prettyfy_id(id(w_self))
        return '<%s@%s>' % (w_self.w_bound_to,
                            prettyfy_id(id(w_self)))

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


class W_CVar(W_Var):
    def __init__(self, space, w_dom, w_name):
        assert isinstance(w_dom, W_AbstractDomain)
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

#-- Constraint ---------------------------------------------

class W_Constraint(baseobjspace.Wrappable):
    def __init__(self, object_space):
        self._space = object_space

W_Constraint.typedef = typedef.TypeDef("W_Constraint")

class W_AbstractDomain(baseobjspace.Wrappable):
    """Implements the functionnality related to the changed flag.
    Can be used as a starting point for concrete domains"""

    def __init__(self, space):
        self._space = space
        self._changed = W_Var(self._space)

    def give_synchronizer(self):
        pass

    def get_values(self):
        pass

    def remove_values(self, values):
        assert isinstance(values, list)
        
    def size(self):
        pass

W_AbstractDomain.typedef = typedef.TypeDef("W_AbstractDomain")

class W_AbstractDistributor(baseobjspace.Wrappable):

    def __init__(self, space, fanout):
        assert isinstance(fanout, int)
        self._space = space
        self._fanout = fanout
        self._cspace = get_current_cspace(space)

W_AbstractDistributor.typedef = typedef.TypeDef("W_AbstractDistributor")

#-- Pool --------------------------------------------------

class Pool:
    local_pool = None

    def __init__(self, cspace=None):
        self.cspace = cspace

    def hello_local_pool(self):
        if we_are_translated():
            w('hello_local_pool')
            self.saved_pool = gc_swap_pool(self.local_pool)

    def goodbye_local_pool(self):
        if we_are_translated():
            w('goodbye_local_pool')
            self.local_pool = gc_swap_pool(self.saved_pool)
            self.saved_pool = None

    def clone(self):
        copy = Pool()
        self.clone_into(copy)
        return copy

    def clone_into(self, copy, extradata=None):
        # blindly copied from interp_clonable
        # all we need is love, after all ...
        if not we_are_translated():
            raise NotImplementedError
        # cannot gc_clone() directly self, because it is not in its own
        # local_pool.  Moreover, it has a __del__, which cloning doesn't
        # support properly at the moment.
        # the hello/goodbye pair has two purposes: it forces
        # self.local_pool to be computed even if it was None up to now,
        # and it puts the 'data' tuple in the correct pool to be cloned.
        self.hello_local_pool()
        data = (self.cspace, extradata)
        self.goodbye_local_pool()
        # clone!
        data, copy.local_pool = gc_clone(data, self.local_pool)
        copy.cspace, extradata = data
        return extradata


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

def prettyfy_id(an_int):
    "gets the 3 lower digits of an int"
    assert isinstance(an_int, int)
    a_str = str(an_int)
    l = len(a_str) - 1
    return a_str[l-3:l]
