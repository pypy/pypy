import math

def arrange_domains(cs, variables):
    """build a data structure from var to dom
       that satisfies distribute & friends"""
    new_doms = {}
    for var in variables:
        new_doms[var] = cs.dom(var).copy()
    return new_doms

class AbstractDistributor(object):
    """_distribute is left unimplemented."""

    def __init__(self, c_space, nb_subspaces=2):
        self.nb_subspaces = nb_subspaces
        self.cs = c_space
        self.verbose = 0

    def set_space(self, space):
        self.cs = space
            
    def find_smallest_domain(self):
        """returns the variable having the smallest domain.
        (or one of such varibles if there is a tie)
        """
        vars_ = [var for var in self.cs.get_variables_with_a_domain()
                 if self.cs.dom(var).size() > 1]
        
        best = vars_[0]
        for var in vars_:
            if self.cs.dom(var).size() < self.cs.dom(best).size():
                best = var
        
        return best

    def nb_subdomains(self):
        """return number of possible splits"""
        return self.nb_subspaces



    def distribute(self, choice):
        variable = self._find_distribution_variable()
        self._do_distribute(self.cs.dom(variable), choice)
        for const in self.cs.dependant_constraints(variable):
            self.cs.event_set.add(const)

    def _find_distribution_variable(self):
        return self.find_smallest_domain()
    
    def _do_distribute(self, domain, choice):
        """remove values from domain depending on choice"""
        raise NotImplementedError

    
       

        
class NaiveDistributor(AbstractDistributor):
    """distributes domains by splitting the smallest domain in 2 new domains
    The first new domain has a size of one,
    and the second has all the other values"""

    def __init__(self, c_space):
        AbstractDistributor.__init__(self, c_space, 2)
        
    def _do_distribute(self, domain, choice):
        values = domain.get_values()
        if choice == 0:
            domain.remove_values(values[1:])
        else:
            domain.remove_value(values[0])
    

class SplitDistributor(AbstractDistributor):
    """distributes domains by splitting the smallest domain in
    nb_subspaces equal parts or as equal as possible.
    If nb_subspaces is 0, then the smallest domain is split in
    domains of size 1"""
    
    def __init__(self, c_space, nb_subspaces=3):
        AbstractDistributor.__init__(self, c_space, nb_subspaces)


    def nb_subdomains(self):
        to_split = self.find_smallest_domain()
        if self.nb_subspaces:
            return min(self.nb_subspaces,
                       self.cs.dom(to_split).size()) 
        else:
            return self.cs.dom(to_split).size() 


    def _do_distribute(self, domain, choice):
        nb_subspaces = self.nb_subdomains()
        values = domain.get_values()
        nb_elts = max(1, len(values)*1./nb_subspaces)
        start, end = (int(math.floor(choice * nb_elts)),
                      int(math.floor((choice + 1) * nb_elts)))
        domain.remove_values(values[:start])
        domain.remove_values(values[end:])


class DichotomyDistributor(SplitDistributor):
    """distributes domains by splitting the smallest domain in
    two equal parts or as equal as possible"""
    def __init__(self, c_space):
        SplitDistributor.__init__(self, c_space, 2)

DefaultDistributor = NaiveDistributor
