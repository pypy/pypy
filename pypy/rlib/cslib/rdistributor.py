"""
distributors - part of constraint satisfaction solver.
"""

def make_new_domains(domains):
    """return a shallow copy of dict of domains passed in argument"""
    new_domains = {}
    for key, domain in domains.items():
        new_domains[key] = domain.copy()
    return new_domains

class AbstractDistributor:
    """Implements DistributorInterface but abstract because
    _distribute is left unimplemented."""
        
    def find_smallest_domain(self, domains):
        """returns the variable having the smallest domain.
        (or one of such varibles if there is a tie)
        """
        k = 0
        doms = domains.items()
        while k<len(doms):
            var, dom = doms[k]
            sz = dom.size()
            if sz>1:
                min_size = sz
                min_var = var
                break
            k += 1
        else:
            raise RuntimeError, "should not be here"
        while k<len(doms):
            var, dom = doms[k]
            if 1 < dom.size() < min_size:
                min_var = var
                min_size = dom.size()
            k += 1
        return min_var

    def distribute(self, domains):
        """
        domains -> two variants of the same modified domain
        do the minimal job and let concrete class distribute variables
        """
        doms1 = make_new_domains(domains)
        doms2 = make_new_domains(domains)
        for modified_domain in self._distribute(doms1,doms2):
            modified_domain._changed = False 
        return [doms1,doms2]
        
class AllOrNothingDistributor(AbstractDistributor):
    """distributes domains by splitting the smallest domain in 2 new domains
    The first new domain has a size of one,
    and the second has all the other values"""

    def _distribute_on_choice(self, dom, choice):
        if choice == 1:
            dom.remove_values(dom.get_values()[1:])
        else:
            dom.remove_value(dom.get_values()[0])
            
    def _distribute(self, doms1, doms2):
        """See AbstractDistributor"""
        variable = self.find_smallest_domain(doms1)
        values = doms1[variable].get_values()
        self._distribute_on_choice(doms1[variable], 1)
        self._distribute_on_choice(doms2[variable], 2)
        return [doms1[variable], doms2[variable]]

class DichotomyDistributor(AbstractDistributor):
    """distributes domains by splitting the smallest domain in
    two equal parts or as equal as possible."""

    def _distribute_on_choice(self, dom, choice):
        values = dom.get_values()
        middle = len(values)/2
        if choice == 1:
            dom.remove_values(values[:middle])
        else:
            dom.remove_values(values[middle:])

    def _distribute(self, doms1, doms2):
        """See AbstractDistributor"""
        variable = self.find_smallest_domain(doms1)
        values = doms1[variable].get_values()
        middle = len(values)/2
        self._distribute_on_choice(doms1[variable], 1)
        self._distribute_on_choice(doms2[variable], 2)
        return [doms1[variable], doms2[variable]]

DefaultDistributor = DichotomyDistributor
