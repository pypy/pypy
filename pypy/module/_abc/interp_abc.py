from pypy.objspace.std.typeobject import W_TypeObject, PATMA_SEQUENCE, PATMA_MAPPING
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import oefmt

@unwrap_spec(flag=int)
def set_collection_flag(space, w_self, flag):
    w_self = space.interp_w(W_TypeObject, w_self)
    if flag == PATMA_SEQUENCE:
        w_self.flag_patma_collection = "S"
    elif flag == PATMA_MAPPING:
        w_self.flag_patma_collection = "M"
    else:
        raise oefmt(space.w_ValueError, "invalid value for __abc_tpflags__: %R", space.newint(flag))
    
@unwrap_spec(flag=int)
def set_collection_flag_recursive(space, w_self, flag):
    w_self = space.interp_w(W_TypeObject, w_self)
    set_collection_flag(space, w_self, flag)
    for child in w_self.get_subclasses():
        set_collection_flag_recursive(space, child, flag)

    
