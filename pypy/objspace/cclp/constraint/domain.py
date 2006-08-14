from pypy.interpreter.error import OperationError

from pypy.interpreter import typedef, gateway, baseobjspace
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.listobject import W_ListObject, W_TupleObject

from pypy.objspace.std.model import StdObjSpaceMultiMethod

from pypy.objspace.cclp.types import W_AbstractDomain, W_Var
from pypy.objspace.cclp.interp_var import interp_bind

all_mms = {}

class ConsistencyFailure(Exception):
    """The repository is not in a consistent state"""
    pass


class W_FiniteDomain(W_AbstractDomain):
    """
    Variable Domain with a finite set of possible values
    """

    def __init__(self, space, w_values):
        """values is a list of values in the domain
        This class uses a dictionnary to make sure that there are
        no duplicate values"""
        W_AbstractDomain.__init__(self, space)
        #XXX a pure dict used to work there (esp. in revise)
        assert isinstance(w_values, W_ListObject)
        self._values = space.newdict()
        self.set_values(w_values)


    def clear_change(self):
        assert not isinstance(self._changed.w_bound_to, W_Var)
        self._changed = W_Var(self._space)

    def give_synchronizer(self):
        return self._changed

    def _value_removed(self):
        """The implementation of remove_value should call this method"""
        interp_bind(self._space, self._changed, True)
        self.clear_change()
        
        if self.size() == 0:
            raise OperationError(self._space.w_RuntimeError,
                                 self._space.wrap('ConsistencyFailure'))

##     def w__del__(self):
##         self._space.bind(self._changed, self._space.newbool(False))


    def set_values(self, w_values):
        """Objects in the value set can't be unwrapped unless we
        specialize on specific types - this might need speccialization
        of revise & friends
        """
        for w_v in w_values.wrappeditems:
            self._space.setitem(self._values, w_v, self._space.w_True)
        
    def remove_value(self, w_value):
        """Remove value of domain and check for consistency"""
        assert isinstance(w_value, baseobjspace.W_Root)
        del self._values.content[w_value]
        self._value_removed()

    def w_remove_values(self, w_values):
        """Remove values of domain and check for consistency"""
        assert isinstance(w_values, W_ListObject)
        try:
            self.remove_values(w_values.wrappeditems)
        except KeyError:
            raise OperationError(self._space.w_RuntimeError,
                                 self._space.wrap("attempt to remove unkown value from domain"))

    def remove_values(self, values):
        assert isinstance(values, list)
        if len(values) > 0:
            for w_val in values:
                del self._values.content[w_val]
            self._value_removed()

    def w_size(self):
        return self._space.newint(self.size())

    def size(self):
        """computes the size of a finite domain"""
        return self._space.len(self._values).intval
    __len__ = size
    
    def w_get_values(self):
        """return all the values in the domain
           in an indexable sequence"""
        return self._space.newlist(self.get_values())

    def get_values(self):
        return [x for x in self._values.content.keys()]
        
    def __repr__(self):
        return '<FD %s>' % str(self.w_get_values())

    def __eq__(self, w_other):
        if not isinstance(w_other, W_FiniteDomain):
            return self._space.newbool(False)
        return self._space.newbool(self._space.eq_w(self._values, w_other._values))
            
    def __ne__(self, w_other):
        return not self == w_other




# function bolted into the space to serve as constructor
def make_fd(space, w_values):
    assert isinstance(w_values, W_ListObject)
    return space.wrap(W_FiniteDomain(space, w_values))
app_make_fd = gateway.interp2app(make_fd)


def intersection(space, w_fd1, w_fd2):
    assert isinstance(w_fd1, W_FiniteDomain)
    assert isinstance(w_fd2, W_FiniteDomain)
    return space.intersection(w_fd1, w_fd2)
app_intersection = gateway.interp2app(intersection)


def intersection__FiniteDomain_FiniteDomain(space, w_fd1, w_fd2):
    w_v1 = w_fd1._values.content
    res = [w_v for w_v in w_fd2._values.content
             if w_v in w_v1]
    return make_fd(space, space.newlist(res))

intersection_mm = StdObjSpaceMultiMethod('intersection', 2)
intersection_mm.register(intersection__FiniteDomain_FiniteDomain,
                         W_FiniteDomain, W_FiniteDomain)
all_mms['intersection'] = intersection_mm

W_FiniteDomain.typedef = typedef.TypeDef(
    "W_FiniteDomain",
    W_AbstractDomain.typedef,
    remove_value = interp2app(W_FiniteDomain.remove_value),
    remove_values = interp2app(W_FiniteDomain.w_remove_values),
    get_values = interp2app(W_FiniteDomain.w_get_values),
    __eq__ = interp2app(W_FiniteDomain.__eq__),
    __ne__ = interp2app(W_FiniteDomain.__ne__),
    size = interp2app(W_FiniteDomain.w_size))

