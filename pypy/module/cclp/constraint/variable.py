from pypy.interpreter import gateway, baseobjspace
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.module.cclp.types import deref, W_Var, W_CVar
from pypy.module.cclp.variable import bind_mm, raise_unification_failure, _alias, \
     _assign_aliases, bind__Var_Root, bind__Var_Var
from pypy.module.cclp.misc import w

from pypy.module._cslib import fd


W_Root = baseobjspace.W_Root

def domain(space, w_values, w_name):
    assert isinstance(w_values, W_ListObject)
    assert isinstance(w_name, W_StringObject)
    w_dom = fd.W_FiniteDomain(w_values, None)
    w_var = W_CVar(space, w_dom, w_name)
    w("CVAR", str(w_var))
    return w_var
app_domain = gateway.interp2app(domain)


def bind__CVar_Root(space, w_cvar, w_obj):
    #XXX we should (want to) be able to test membership
    #    in a wrapped against wrappeds into a non-wrapped dict
    if [True for elt in w_cvar.w_dom.domain.get_wvalues_in_rlist()
        if space.is_true(space.eq(w_obj, elt))]:
        return bind__Var_Root(space, w_cvar, w_obj)
    raise_unification_failure(space, "value not in variable domain")

def bind__CVar_CVar(space, w_cvar1, w_cvar2):
    d1 = w_cvar1.w_dom.domain
    d2 = w_cvar2.w_dom.domain
    dinter = d1.intersect(d2)
    if dinter.size() > 0:
        if dinter.size() == 1:
            w_value = dinter.get_wvalues_in_rlist()[0]
            _assign_aliases(space, w_cvar1, w_value)
            _assign_aliases(space, w_cvar2, w_value)
        else:
            w_interdom = fd.W_FiniteDomain(space.newlist([]), None)
            w_interdom.domain = dinter
            w_cvar1.w_dom = w_cvar2.w_dom = w_interdom
            _alias(space, w_cvar1, w_cvar2)
    else:
        raise_unification_failure(space, "incompatible domains")

def bind__CVar_Var(space, w_cvar, w_var):
    if space.is_true(space.is_bound(w_var)):
        return bind__CVar_Root(space, w_cvar, w_var)
    return bind__Var_Var(space, w_cvar, w_var)


bind_mm.register(bind__CVar_CVar, W_CVar, W_CVar)
bind_mm.register(bind__CVar_Root, W_CVar, W_Root)
bind_mm.register(bind__CVar_Var, W_CVar, W_Var)
