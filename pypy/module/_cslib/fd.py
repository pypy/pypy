from pypy.interpreter.error import OperationError

from pypy.interpreter import typedef, gateway, baseobjspace
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.listobject import W_ListObject, W_TupleObject
from pypy.objspace.std.intobject import W_IntObject

from pypy.rlib import rdomain as rd

class _FiniteDomain(rd.BaseFiniteDomain):
    """
    Variable Domain with a finite set of possible values
    """

    def __init__(self, w_values, values):
        """values is a list of values in the domain
        This class uses a dictionnary to make sure that there are
        no duplicate values"""
        
        assert isinstance(w_values, W_ListObject)
        self.w_values = w_values
        self._values = {}

        if values is None:
            for k in range(len(w_values.wrappeditems)):
                self._values[k] = True
        else:
            self._values = values.copy()
        
        self._changed = False

    def copy(self):
        return _FiniteDomain(self.w_values, self._values)

class W_FiniteDomain(baseobjspace.Wrappable):
    def __init__(self, w_values, values):
        assert isinstance(w_values, W_ListObject)
        self.domain = _FiniteDomain( w_values, values )

def make_fd(space, w_values):
    if not isinstance(w_values, W_ListObject):
        if not isinstance(w_values, W_TupleObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap('first argument must be a list.'))
    return W_FiniteDomain(w_values, None)

W_FiniteDomain.typedef = typedef.TypeDef(
    "W_FiniteDomain")

