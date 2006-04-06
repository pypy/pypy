from pypy.interpreter.error import OperationError

from pypy.interpreter import baseobjspace, typedef, gateway
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.listobject import W_ListObject, W_TupleObject

from pypy.objspace.std.model import StdObjSpaceMultiMethod


all_mms = {}

class ConsistencyFailure(Exception):
    """The repository is not in a consistent state"""
    pass


class W_AbstractDomain(Wrappable):
    """Implements the functionnality related to the changed flag.
    Can be used as a starting point for concrete domains"""

    def __init__(self, space):
        self._space = space
        self.__changed = self._space.newbool(False)

    def w_reset_flags(self):
        self.__changed = self._space.newbool(False)
    
    def w_has_changed(self):
        return self.__changed

    def w_size(self):
        pass
    
    def _value_removed(self):
        """The implementation of remove_value should call this method"""
        self.__changed = self._space.newbool(True)
        if self._space.eq_w(self.w_size(), self._space.newint(0)):
            raise  OperationError(self._space.w_RuntimeError,
                             self._space.wrap('ConsistencyFailure'))

W_AbstractDomain.typedef = typedef.TypeDef("W_AbstractDomain",
    reset_flags = interp2app(W_AbstractDomain.w_reset_flags),
    has_changed = interp2app(W_AbstractDomain.w_has_changed))

class W_FiniteDomain(W_AbstractDomain):
    """
    Variable Domain with a finite set of possible values
    """

    def __init__(self, space, w_values):
        """values is a list of values in the domain
        This class uses a dictionnary to make sure that there are
        no duplicate values"""
        W_AbstractDomain.__init__(self, space)
        self._values = {}
        self.set_values(w_values)

    def set_values(self, w_values):
        for w_v in w_values.wrappeditems:
            self._values[w_v] = True
        
    def w_remove_value(self, w_value):
        """Remove value of domain and check for consistency"""
        self._values.pop(w_value)
        self._value_removed()

    def w_remove_values(self, w_values):
        """Remove values of domain and check for consistency"""
        if self._space.is_true(self._space.gt(self._space.len(w_values),
                                              self._space.newint(0))) :
            for val in w_values.wrappeditems :
                self._values.pop(val)
            self._value_removed()
    __delitem__ = w_remove_value
    
    def w_size(self):
        """computes the size of a finite domain"""
        return self._space.newint(len(self._values))
    __len__ = w_size
    
    def w_get_values(self):
        """return all the values in the domain
           in an indexable sequence"""
        return self._space.newlist([x for x in self._values])

    def __iter__(self):
        return iter(self._values)
    
    def w_copy(self):
        """clone the domain"""
        return W_FiniteDomain(self._space, self.w_get_values())
    
    def __repr__(self):
        return '<FD %s>' % str(self.get_values())

    def __eq__(self, w_other):
        if w_other is NoDom: return False
        return self._values == w_other._values

    def __ne__(self, w_other):
        return not self == w_other

# function bolted into the space to serve as constructor
def make_fd(space, w_values):
    return W_FiniteDomain(space, w_values)
app_make_fd = gateway.interp2app(make_fd)


def intersection__FiniteDomain_FiniteDomain(space, w_fd1, w_fd2):
    return make_fd(w_fd1.w_get_values() + w_fd2.w_get_values())

intersection_mm = StdObjSpaceMultiMethod('intersection', 2)
intersection_mm.register(intersection__FiniteDomain_FiniteDomain,
                         W_FiniteDomain, W_FiniteDomain)
all_mms['intersection'] = intersection_mm

W_FiniteDomain.typedef = typedef.TypeDef("W_FiniteDomain",
    W_AbstractDomain.typedef,
    remove_value = interp2app(W_FiniteDomain.w_remove_value),
    remove_values = interp2app(W_FiniteDomain.w_remove_values),
    get_values = interp2app(W_FiniteDomain.w_get_values),
    copy = interp2app(W_FiniteDomain.w_copy),
    size = interp2app(W_FiniteDomain.w_size))

