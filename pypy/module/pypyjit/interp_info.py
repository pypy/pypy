
from pypy.interpreter.baseobjspace import Wrappable, ObjSpace, W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pycode import PyCode

class MergePointInfo(Wrappable):
    def __init__(self, jitcell):
        self.counter = jitcell.counter

MergePointInfo.typedef = TypeDef(
    'MergePointInfo',
    counter = interp_attrproperty('counter', cls=MergePointInfo),
)
MergePointInfo.typedef.acceptable_as_base_class = False

@unwrap_spec(ObjSpace, W_Root)
def getjitinfo(space, w_obj):
    pycode = space.interp_w(PyCode, w_obj)
    w_dict = space.newdict()
    for k, v in pycode.jit_cells.items():
        space.setitem(w_dict, space.wrap(k), MergePointInfo(v))
    return w_dict
