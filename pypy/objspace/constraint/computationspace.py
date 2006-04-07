from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.stringobject import W_StringObject

from pypy.objspace.constraint.domain import W_AbstractDomain

all_mms = {}

class W_Variable(Wrappable):
    def __init__(self, obj_space, w_name):
        self._space = obj_space
        self.name = w_name

W_Variable.typedef = typedef.TypeDef("W_Variable")

class W_ComputationSpace(Wrappable):
    def __init__(self, obj_space):
        self._space = obj_space
        self.domains = self._space.newdict({})

    def w_var(self, w_name, w_domain):
        assert isinstance(w_name, W_StringObject)
        assert isinstance(w_domain, W_AbstractDomain)
        if w_name in self.domains.content:
            raise OperationError(self._space.w_RuntimeError,
                                 self._space.wrap("Name already used"))
        self.domains.content[w_name] = w_domain
        return W_Variable(self._space, w_name)

    def w_dom(self, w_variable):
        assert isinstance(w_variable, W_Variable)
        return self.domains.content[w_variable.name]

W_ComputationSpace.typedef = typedef.TypeDef(
    "W_ComputationSpace",
    var = interp2app(W_ComputationSpace.w_var),
    dom = interp2app(W_ComputationSpace.w_dom))


def newspace(space):
    return W_ComputationSpace(space)
app_newspace = gateway.interp2app(newspace)
