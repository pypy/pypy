from pypy.interpreter import gateway, baseobjspace
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.module.cclp.constraint.domain import W_FiniteDomain

from pypy.module.cclp.types import deref, W_Var, W_CVar
from pypy.module.cclp.variable import bind_mm, raise_unification_failure, _alias, \
     _assign_aliases, bind__Var_Root, bind__Var_Var
from pypy.module.cclp.misc import w

W_Root = baseobjspace.W_Root

def domain(space, w_values, w_name):
    assert isinstance(w_values, W_ListObject)
    assert isinstance(w_name, W_StringObject)
    w_dom = W_FiniteDomain(space, w_values)
    w_var = W_CVar(space, w_dom, w_name)
    #w("CVAR", str(w_var))
    return w_var
app_domain = gateway.interp2app(domain)


def bind__CVar_Root(space, w_cvar, w_obj):
    #XXX we should (want to) be able to test membership
    #    in a wrapped against wrappeds into a non-wrapped dict
    if [True for elt in space.unpackiterable(w_cvar.w_dom._values)
        if space.is_true(space.eq(w_obj, elt))]:
        return bind__Var_Root(space, w_cvar, w_obj)
    raise_unification_failure(space, "value not in variable domain")

def bind__CVar_CVar(space, w_cvar1, w_cvar2):
    w_inter_dom = space.intersection(w_cvar1.w_dom, w_cvar2.w_dom)
    if w_inter_dom.__len__() > 0:
        if w_inter_dom.__len__() == 1:
            w_value = w_inter_dom.get_values()[0]
            _assign_aliases(space, w_cvar1, w_value)
            _assign_aliases(space, w_cvar2, w_value)
        else:
            w_cvar1.w_dom = w_cvar2.w_dom = w_inter_dom
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
