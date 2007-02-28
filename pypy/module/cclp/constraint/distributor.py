import math

from pypy.interpreter.error import OperationError
from pypy.interpreter import baseobjspace, typedef
from pypy.interpreter.gateway import interp2app

from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.module.cclp.types import W_AbstractDistributor, ConsistencyError
from pypy.module.cclp.misc import w, get_current_cspace

def distribute(space, w_strategy):
    assert isinstance(w_strategy, W_StringObject)
    strat = space.str_w(w_strategy)
    cspace = get_current_cspace(space)
    dist = None
    if strat == 'dichotomy':
         dist = make_split_distributor(space, space.newint(2))
    else:
        raise OperationError(space.w_RuntimeError,
                             space.wrap("please pick a strategy in (naive, dichotomy)"))

    cspace.distributor = dist
    # constraint distributor thread main loop
    cspace.wait_stable()
    if not dist.distributable():
        return
    while 1:
        choice = cspace.choose(dist.fanout())
        if dist.distributable():
            dist.w_distribute(choice)
            # propagators laucnhed
        else:
            if cspace._failed:
                raise ConsistencyError
            break
distribute.unwrap_spec = [baseobjspace.ObjSpace,
                          baseobjspace.W_Root]


class W_Distributor(W_AbstractDistributor):
    """_distribute is left unimplemented."""

    def w_fanout(self):
        return self._space.newint(self._fanout)

    def fanout(self):
        return self._fanout
 
    def _find_smallest_domain(self):
        """returns the variable having the smallest domain.
        (or one of such variables if there is a tie)
        """
        vars_ = [var for var in self._cspace._store.values()
                 if var.w_dom.size() > 1]
        best = vars_[0]
        for var in vars_:
            if var.w_dom.size() < best.w_dom.size():
                best = var
        return best

    def distributable(self):
        for var in self._cspace._store.values():
            if var.w_dom.size() > 1:
                return True
        return False

    def w_distribute(self, w_choice):
        assert isinstance(w_choice, W_IntObject)
        self.distribute(self._space.int_w(w_choice) -1)

    def distribute(self, choice):
        assert isinstance(choice, int)
        variable = self.find_distribution_variable()
        domain = variable.w_dom
        self._do_distribute(domain, choice)

    def find_distribution_variable(self):
        return self._find_smallest_domain()
    
    def _do_distribute(self, domain, choice):
        """remove values from domain depending on choice"""
        raise NotImplementedError

W_Distributor.typedef = typedef.TypeDef("W_Distributor",
    W_AbstractDistributor.typedef,
    fanout = interp2app(W_Distributor.w_fanout),
    distribute = interp2app(W_Distributor.w_distribute))
    
        
class W_NaiveDistributor(W_Distributor):
    """distributes domains by splitting the smallest domain in 2 new domains
    The first new domain has a size of one,
    and the second has all the other values"""

        
    def _do_distribute(self, domain, choice):
        values = domain.get_values()
        #assert len(values) > 0
        if choice == 0:
            domain.remove_values(values[1:])
        else:
            domain.w_remove_value(values[0]) #XXX w ? not w ?

W_NaiveDistributor.typedef = typedef.TypeDef(
    "W_NaiveDistributor",
    W_Distributor.typedef)

def make_naive_distributor(object_space, fanout=2):
    if not isinstance(fanout, int):
        raise OperationError(object_space.w_RuntimeError,
                             object_space.wrap("fanout must be a positive integer"))
    return W_NaiveDistributor(object_space, fanout)
app_make_naive_distributor = interp2app(make_naive_distributor,
                                        unwrap_spec = [baseobjspace.ObjSpace, int])


class W_SplitDistributor(W_Distributor):
    """distributes domains by splitting the smallest domain in
    nb_subspaces equal parts or as equal as possible.
    If nb_subspaces is 0, then the smallest domain is split in
    domains of size 1"""
    
    def _subdomains(self):
        """returns the min number of partitions
           for a domain to be distributed"""
        to_split = self._find_smallest_domain()
        if self._fanout > 0:
            return min(self._fanout, to_split.w_dom.size()) 
        else:
            return to_split.w_dom.size() 

    def _do_distribute(self, domain, choice):
        values = domain.get_values()
        subdoms = self._subdomains()
        nb_elts = max(subdoms, len(values))  / float(subdoms)
        start, end = (int(math.floor(choice * nb_elts)),
                      int(math.floor((choice + 1) * nb_elts)))
        lv = len(values)
        assert start >= 0
        assert start <= lv
        domain.remove_values(values[:start])
        assert end >= 0
        assert end <= lv
        domain.remove_values(values[end:])

def make_split_distributor(space, w_fanout):
    return W_SplitDistributor(space, space.int_w(w_fanout))
app_make_split_distributor = interp2app(make_split_distributor)

