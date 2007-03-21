from pypy.interpreter import gateway, baseobjspace
from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import StdObjSpaceMultiMethod
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject
from pypy.objspace.std.dictobject import W_DictObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.module.cclp.misc import w, v, AppCoroutine
from pypy.module.cclp.global_state import sched
from pypy.module.cclp.types import deref, W_Var, W_CVar, W_Future, W_FailedValue

from pypy.rlib.objectmodel import we_are_translated

W_Root = baseobjspace.W_Root
all_mms = {}

def newvar(space):
    w_v = W_Var(space)
    w("VAR", w_v.__repr__())
    return w_v
app_newvar = gateway.interp2app(newvar)

    
#-- Wait -------------------------------------------------

def wait__Root(space, w_obj):
    return w_obj

def wait__Var(space, w_var):
    #w("###:wait", str(id(AppCoroutine.w_getcurrent(space))))
    if space.is_true(space.is_free(w_var)):
        sched.uler.unblock_byneed_on(w_var)
        sched.uler.add_to_blocked_on(w_var)
        sched.uler.schedule()
        assert space.is_true(space.is_bound(w_var))
    w_ret = w_var.w_bound_to
    if isinstance(w_ret, W_FailedValue):
        w(".. reraising Failed Value")
        raise w_ret.exc
    return w_ret

def wait(space, w_obj):
    if not we_are_translated():
        assert isinstance(w_obj, W_Root)
    return space.wait(w_obj)
app_wait = gateway.interp2app(wait)

wait_mm = StdObjSpaceMultiMethod('wait', 1)
wait_mm.register(wait__Var, W_Var)
wait_mm.register(wait__Root, W_Root)
all_mms['wait'] = wait_mm

#-- Wait_needed --------------------------------------------

def wait_needed__Var(space, w_var):
    #w(":wait_needed", str(id(AppCoroutine.w_getcurrent(space))))
    if space.is_true(space.is_free(w_var)):
        if w_var.needed:
            return
        sched.uler.add_to_blocked_byneed(w_var)
        sched.uler.schedule()
    else:
        raise OperationError(space.w_TypeError,
                             space.wrap("wait_needed only supported on unbound variables"))

def wait_needed(space, w_var):
    assert isinstance(w_var, W_Var)
    return space.wait_needed(w_var)
app_wait_needed = gateway.interp2app(wait_needed)            


wait_needed_mm = StdObjSpaceMultiMethod('wait_needed', 1)
wait_needed_mm.register(wait_needed__Var, W_Var)
all_mms['wait_needed'] = wait_needed_mm


#-- PREDICATES (is_bound, is_free, is_aliased, alias_of) ---------

def is_aliased(space, w_var): # XXX: this appear(ed) to block (long ago)
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


def alias_of(space, w_var1, w_var2):
    assert isinstance(w_var1, W_Var)
    assert isinstance(w_var2, W_Var)
    if not (space.is_true(space.is_free(w_var1)) and \
            space.is_true(space.is_free(w_var2))):
        raise OperationError(space.w_LogicError,
                             space.wrap("don't call alias_of on bound variables"))
    w_curr = w_var1
    while 1:
        w_next = w_curr.w_bound_to
        assert isinstance(w_next, W_Var)
        if w_next is w_var2:
            return space.newbool(True)
        if w_next is w_var1:
            break
        w_curr = w_next
    return space.newbool(False)
app_alias_of = gateway.interp2app(alias_of)

#-- HELPERS ----------------------

def get_ring_tail(space, w_start):
    "returns the last var of a ring of aliases"
    assert isinstance(w_start, W_Var)
    w_curr = w_start
    while 1:
        w_next = w_curr.w_bound_to
        assert isinstance(w_next, W_Var)
        if space.is_true(space.is_nb_(w_next, w_start)):
            return w_curr
        w_curr = w_next


def raise_unification_failure(space, comment="Unification failure"):
    """raises a specific exception for bind/unify
       should fail the current comp. space at some point"""
    raise OperationError(space.w_UnificationError,
                         space.wrap(comment))

# to signal a future binding exception
def raise_future_binding(space):
    raise OperationError(space.w_FutureBindingError,
                         space.wrap("This future is read-only for you, pal"))


#-- BIND, ENTAIL----------------------------

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

def entail(space, w_v1, w_v2):
    "X -> Y"
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    space.entail(w_v1, w_v2)
app_entail = gateway.interp2app(entail)
    

def bind__Var_Root(space, w_var, w_obj):
    #w("var val", str(id(w_var)))
    # 3. var and value
    if space.is_true(space.is_free(w_var)):
        return _assign_aliases(space, w_var, w_obj)
    if space.is_true(space.eq(w_var.w_bound_to, w_obj)):
        return
    raise OperationError(space.w_RebindingError,
                         space.wrap("Cannot bind twice but two identical values"))

def bind__Future_Root(space, w_fut, w_obj):
    #v("future val", str(id(w_fut)))
    if w_fut._client == AppCoroutine.w_getcurrent(space):
        raise_future_binding(space)
    return bind__Var_Root(space, w_fut, w_obj) # call-next-method ?

def bind__Var_Var(space, w_v1, w_v2):
    #w("var var")
    if space.is_true(space.is_bound(w_v1)):
        if space.is_true(space.is_bound(w_v2)):
            # we allow re-binding to same value, see 3.
            return unify(space,
                         deref(space, w_v1),
                         deref(space, w_v2))
        # 2. a (obj unbound, var bound)
        return _assign_aliases(space, w_v2, deref(space, w_v1))
    elif space.is_true(space.is_bound(w_v2)):
        # 2. b (var unbound, obj bound)
        return _assign_aliases(space, w_v1, deref(space, w_v2))
    else: # 1. both are unbound
        return _alias(space, w_v1, w_v2)

def bind__Future_Var(space, w_fut, w_var):
    #v("future var")
    if w_fut._client == AppCoroutine.w_getcurrent(space):
        raise_future_binding(space)
    return bind__Var_Var(space, w_fut, w_var)


def bind__Var_Future(space, w_var, w_fut): 
    if space.is_true(space.is_bound(w_fut)): #XXX write a test for me !
        return bind__Var_Root(space, w_var, deref(space, w_fut))
    if w_fut._client == AppCoroutine.w_getcurrent(space):
        raise_future_binding(space)
    return bind__Var_Var(space, w_var, w_fut) #and for me ...


bind_mm = StdObjSpaceMultiMethod('bind', 2)
bind_mm.register(bind__Var_Root, W_Var, W_Root)
bind_mm.register(bind__Var_Var, W_Var, W_Var)
bind_mm.register(bind__Future_Root, W_Future, W_Root)
bind_mm.register(bind__Future_Var, W_Future, W_Var)
bind_mm.register(bind__Var_Future, W_Var, W_Future)
all_mms['bind'] = bind_mm


def entail__Var_Var(space, w_v1, w_v2):
    #w("  :entail Var Var")
    if space.is_true(space.is_bound(w_v1)):
        if space.is_true(space.is_bound(w_v2)):
            return unify(space,
                         deref(space, w_v1),
                         deref(space, w_v2))
        return _assign_aliases(space, w_v2, deref(space, w_v1))
    else:
        return _entail(space, w_v1, w_v2)

entail_mm = StdObjSpaceMultiMethod('entail', 2)
entail_mm.register(entail__Var_Var, W_Var, W_Var)
all_mms['entail'] = entail_mm

def _entail(space, w_v1, w_v2):
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    w_v1.entails[w_v2] = True
    return space.w_None
        
def _assign_aliases(space, w_var, w_val):
    #w("  :assign")
    assert isinstance(w_var, W_Var)
    #assert isinstance(w_val, W_Root)
    w_curr = w_var
    while 1:
        w_next = w_curr.w_bound_to
        assert isinstance(w_next, W_Var)
        _assign(space, w_curr, w_val)
        # notify the blocked threads
        sched.uler.unblock_on(w_curr)
        if space.is_true(space.is_nb_(w_next, w_var)):
            break
        # switch to next
        w_curr = w_next
    _assign_entailed(space, w_var, w_val)
    #w("  :assigned")
    return space.w_None

def _assign_entailed(space, w_var, w_val):
    #w("   :assign entailed")
    for var in w_var.entails:
        if space.is_true(space.is_free(var)):
            _assign_aliases(space, var, w_val)
        else:
            unify(space, deref(space, var), w_val)

def _assign(space, w_var, w_val):
    assert isinstance(w_var, W_Var)
    if isinstance(w_var, W_CVar):
        if not w_val in w_var.w_dom.domain.get_wvalues_in_rlist():
            raise_unification_failure(space, "assignment out of domain")
    w_var.w_bound_to = w_val

    
def _alias(space, w_v1, w_v2):
    """appends one var to the alias chain of another
       user must ensure freeness of both vars"""
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    #w("  :alias", str(id(w_v1)), str(id(w_v2)))
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
    #w("   :add to aliases")
    w_tail = w_v1.w_bound_to
    w_v1.w_bound_to = w_v2
    w_v2.w_bound_to = w_tail
    return space.w_None
    
def _merge_aliases(space, w_v1, w_v2):
    assert isinstance(w_v1, W_Var)
    assert isinstance(w_v2, W_Var)
    #w("   :merge aliases")
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
            raise_unification_failure(space, str(w_x) + " != " + str(w_y))
        else:
            return unify__Dict_Dict(space, w_d1, w_d2)
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
        raise_unification_failure(space, "tuples of different lengths.")
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
        raise_unification_failure(space, "lists of different lengths.")
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
    for w_xk in space.unpackiterable(w_m1):
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
