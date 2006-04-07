from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app

from pypy.objspace.constraint.domain import W_AbstractDomain

all_mms = {}

class W_ComputationSpace(Wrappable):
    def __init__(self, obj_space):
        self._space = obj_space
        self.domains = self._space.newdict({})

    def w_var(self, w_name, w_domain):
        name = self._space.str_w(w_name)
        assert isinstance(w_domain, W_AbstractDomain)
        assert name not in self.domains
        self.domains[name] = w_domain


W_ComputationSpace.typedef = typedef.TypeDef("W_ComputationSpace",
    var = interp2app(W_ComputationSpace.w_var),
                                             )

def newspace(space):
    return W_ComputationSpace(space)
app_newspace = gateway.interp2app(newspace)
