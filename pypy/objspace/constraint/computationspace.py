from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.stringobject import W_StringObject

from pypy.objspace.constraint.domain import W_AbstractDomain


all_mms = {}

#-- Variables ---------------------------

class W_Variable(Wrappable):
    def __init__(self, obj_space, w_name):
        self._space = obj_space
        self.w_name = w_name

    def name_w(self):
        return self._space.str_w(self.w_name)

W_Variable.typedef = typedef.TypeDef("W_Variable")

#-- Constraints -------------------------

class W_Constraint(Wrappable):
    def __init__(self, object_space):
        self._space = object_space

    def w_affected_variables(self):
        pass

    def w_is_variable_relevant(self, w_var):
        pass

    def w_estimate_cost(self, w_cs):
        pass

    def w_revise(self, w_cs):
        pass
    
W_Constraint.typedef = typedef.TypeDef(
    "W_Constraint",
    affected_variables = interp2app(W_Constraint.w_affected_variables),
    is_variable_relevant = interp2app(W_Constraint.w_is_variable_relevant),
    estimate_cost = interp2app(W_Constraint.w_estimate_cost),
    revise = interp2app(W_Constraint.w_revise))

#-- Computation space -------------------

class W_ComputationSpace(Wrappable):
    def __init__(self, obj_space):
        self._space = obj_space
        self.domains = self._space.newdict({})
        self.constraints = self._space.newdict({})

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
        return self.domains.content[w_variable.w_name]

    def w_tell(self, w_constraint):
        assert isinstance(w_constraint, W_Constraint)
        self.constraints.content[w_constraint] = self._space.w_True

W_ComputationSpace.typedef = typedef.TypeDef(
    "W_ComputationSpace",
    var = interp2app(W_ComputationSpace.w_var),
    dom = interp2app(W_ComputationSpace.w_dom),
    tell = interp2app(W_ComputationSpace.w_tell))


def newspace(space):
    return W_ComputationSpace(space)
app_newspace = gateway.interp2app(newspace)
