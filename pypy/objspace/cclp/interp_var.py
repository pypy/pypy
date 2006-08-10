from pypy.objspace.cclp.variable import wait__Var, _assign_aliases, _entail
from pypy.objspace.cclp.types import W_Var



def interp_wait(space, obj):
    return wait__Var(space, obj)


class RebindingError(Exception): pass

def interp_bind(space, w_var, obj):
    if isinstance(w_var.w_bound_to, W_Var):
        return _assign_aliases(space, w_var, obj)
    if w_var.w_bound_to == obj:
        return
    raise RebindingError

class EntailmentFailure(Exception): pass

def interp_entail(space, w_v1, w_v2):
    w_v1val = w_v1.w_bound_to
    w_v2val = w_v2.w_bound_to
    if not isinstance(w_v1val, W_Var):
        if not isinstance(w_v2val, W_Var):
            # let's be simpler than unify
            if w_v1val != w_v2val:
                raise EntailmentFailure
        return _assign_aliases(space, w_v2, w_v1val)
    else:
        return _entail(space, w_v1, w_v2)

