from pypy.interpreter.error import OperationError

from pypy.interpreter import typedef, gateway, baseobjspace
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.listobject import W_ListObject, W_TupleObject
from pypy.objspace.std.intobject import W_IntObject

from pypy.rlib.cslib import rdomain as rd

class _FiniteDomain(rd.BaseFiniteDomain):
    """
    Variable Domain with a finite set of possible values
    """

    def __init__(self, vlist, values):
        """vlist is a list of values in the domain
        values is a dictionnary to make sure that there are
        no duplicate values"""
        
        #assert isinstance(w_values, W_ListObject)
        self.vlist = vlist
        self._values = {}

        if values is None:
            for k in range(len(vlist)):
                self._values[k] = True
        else:
            self._values = values.copy()
        
        self._changed = False

    def get_wvalues_in_rlist(self):
        w_vals = self.vlist
        return [w_vals[idx] for idx in self._values]

    def copy(self):
        return _FiniteDomain(self.vlist, self._values)

    def intersect(self, other):
        v1 = self.get_wvalues_in_rlist()
        v2 = other.get_wvalues_in_rlist()
        inter = [v for v in v1
                 if v in v2]
        return _FiniteDomain(inter, None)
        

class W_FiniteDomain(baseobjspace.Wrappable):
    def __init__(self, w_values, values):
        assert isinstance(w_values, W_ListObject)
        self.domain = _FiniteDomain(w_values.wrappeditems, values)


def make_fd(space, w_values):
    if not isinstance(w_values, W_ListObject):
        if not isinstance(w_values, W_TupleObject):
            raise OperationError(space.w_TypeError,
                                 space.wrap('first argument must be a list.'))
    return W_FiniteDomain(w_values, None)

W_FiniteDomain.typedef = typedef.TypeDef(
    "W_FiniteDomain")

