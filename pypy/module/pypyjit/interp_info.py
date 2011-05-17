
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pycode import PyCode

class JitInfo(W_Root):
    pass

JitInfo.typedef = TypeDef(
    'JitInfo',
)
JitInfo.typedef.acceptable_as_base_class = False

@unwrap_spec(ObjSpace, W_Root)
def getjitinfo(space, w_obj):
    pycode = space.interp_w(PyCode, w_obj)
    w_dict = space.newdict()
    for k in pycode.jit_cells:
        space.setitem(w_dict, space.wrap(k), JitInfo())
    return w_dict
