from pypy.interpreter.error import OperationError

from pypy.interpreter import baseobjspace, gateway
from pypy.interpreter.baseobjspace import Wrappable

from pypy.objspace.std.objspace import W_Object

# ?
from pypy.objspace.std.listobject import W_ListObject, W_TupleObject


class ConsistencyFailure(Exception):
    """The repository is not in a consistent state"""
    pass


class W_AbstractDomain(Wrappable):
    """Implements the functionnality related to the changed flag.
    Can be used as a starting point for concrete domains"""

    def __init__(self, space):
        self._space = space
        self.__changed = 0

    def w_reset_flags(self):
        self.__changed = 0
    
    def w_has_changed(self):
        return self.__changed

    def _value_removed(self):
        """The implementation of remove_value should call this method"""
        self.__changed = 1
        if self.size() == 0:
            raise ConsistencyFailure()

W_AbstractDomain.typedef = TypeDef("W_AbstractDomain",
    reset_flags = interp2app(W_AbstractDomain.w_reset_flags)
    has_changed = interp2app(W_AbstractDomain.w_has_changed))

class W_FiniteDomain(AbstractDomain):
    """
    Variable Domain with a finite set of possible values
    """

    def __init__(self, values):
        """values is a list of values in the domain
        This class uses a dictionnary to make sure that there are
        no duplicate values"""
        AbstractDomain.__init__(self)
        self.set_values(values)

    def set_values(self, values):
        self._values = set(values)
        
    def w_remove_value(self, value):
        """Remove value of domain and check for consistency"""
        self._values.remove(value)
        self._value_removed()

    def w_remove_values(self, values):
        """Remove values of domain and check for consistency"""
        if values:
            for val in values :
                self._values.remove(val)
            self._value_removed()
    __delitem__ = remove_value
    
    def w_size(self):
        """computes the size of a finite domain"""
        return len(self._values)
    __len__ = size
    
    def w_get_values(self):
        """return all the values in the domain
           in an indexable sequence"""
        return list(self._values)

    def __iter__(self):
        return iter(self._values)
    
    def w_copy(self):
        """clone the domain"""
        return FiniteDomain(self)
    
    def __repr__(self):
        return '<FD %s>' % str(self.get_values())

    def __eq__(self, other):
        if other is NoDom: return False
        return self._values == other._values

    def __ne__(self, other):
        return not self == other

    def intersection(self, other):
        if other is None: return self.get_values()
        return self._values & other._values

W_FiniteDomain.typedef = TypeDef("W_FiniteDomain",
    
