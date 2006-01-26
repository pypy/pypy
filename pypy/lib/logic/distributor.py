import math, random

def make_new_domains(variables):
    """updates variables with copied domains indexed by computation space"""
    new_doms = {}
    for var in variables:
        new_doms[var] = var.dom.copy()
    return new_doms

class AbstractDistributor(object):
    """_distribute is left unimplemented."""

    def __init__(self, c_space, nb_subspaces=2):
        self.nb_subspaces = nb_subspaces
        self.c_space = c_space
        self.verbose = 0
            
    def findSmallestDomain(self):
        """returns the variable having the smallest domain.
        (or one of such varibles if there is a tie)
        """
        vars_ = [var for var in self.c_space.store.get_variables_with_a_domain()
                 if var.dom.size() > 1]
        
        best = vars_[0]
        for var in vars_:
            if var.dom.size() < best.dom.size():
                best = var
        
        return best

    def findLargestDomain(self):
        """returns the variable having the largest domain.
        (or one of such variables if there is a tie)
        """
        vars_ = [var for var in self.c_space.store.get_variables_with_a_domain()
                 if var.dom.size() > 1]

        best = vars_[0]
        for var in vars_:
            if var.dom.size() > best.dom.size():
                best = var
        
        return best


    def nb_subdomains(self):
        """return number of sub domains to explore"""
        return self.nb_subspaces

    def distribute(self, verbose=0):
        """do the minimal job and let concrete class distribute variables
        """
        self.verbose = verbose
        variables = self.c_space.store.get_variables_with_a_domain()
        replicas = []
        for i in range(self.nb_subdomains()):
            replicas.append(make_new_domains(variables))
        modified_domains = self._distribute(*replicas)
        for domain in modified_domains:
            domain.reset_flags()
        return replicas

    def _distribute(self, *args):
        """ method to implement in concrete class

        take self.nb_subspaces copy of the original domains as argument
        distribute the domains and return each modified domain
        """
        raise NotImplementedError("Use a concrete implementation of "
                                  "the Distributor interface")
        
class NaiveDistributor(AbstractDistributor):
    """distributes domains by splitting the smallest domain in 2 new domains
    The first new domain has a size of one,
    and the second has all the other values"""

    def _distribute(self, dom1, dom2):
        """See AbstractDistributor"""
        variable = self.findSmallestDomain(dom1)
        values = dom1[variable].get_values()
        if self.verbose:
            print 'Distributing domain for variable', variable, \
                  'at value', values[0]
        dom1[variable].remove_values(values[1:])
        dom2[variable].remove_value(values[0])
        return (dom1[variable], dom2[variable])


class RandomizingDistributor(AbstractDistributor):
    """distributes domains as the NaiveDistrutor, except that the unique
    value of the first domain is picked at random."""
        
    def _distribute(self, dom1, dom2):
        """See AbstractDistributor"""
        variable = self.findSmallestDomain(dom1)
        values = dom1[variable].get_values()
        distval = random.choice(values)
        values.remove(distval)
        if self.verbose:
            print 'Distributing domain for variable', variable, \
                  'at value', distval
        dom1[variable].remove_values(values)
        dom2[variable].remove_value(distval)
        return (dom1[variable], dom2[variable])
    

class SplitDistributor(AbstractDistributor):
    """distributes domains by splitting the smallest domain in
    nb_subspaces equal parts or as equal as possible.
    If nb_subspaces is 0, then the smallest domain is split in
    domains of size 1"""
    
    def __init__(self, c_space, nb_subspaces=3):
        AbstractDistributor.__init__(self, c_space, nb_subspaces)
        self.__to_split = None

    def nb_subdomains(self):
        """See AbstractDistributor"""
        self.__to_split = self.findSmallestDomain()
        if self.nb_subspaces:
            return min(self.nb_subspaces, self.__to_split.dom.size()) #domains[self.__to_split].size())
        else:
            return self.__to_split.dom.size() # domains[self.__to_split].size()
    
    def _distribute(self, *args):
        """See AbstractDistributor"""
        variable = self.__to_split
        nb_subspaces = len(args)
        values = args[0][variable].get_values()
        nb_elts = max(1, len(values)*1./nb_subspaces)
        slices = [(int(math.floor(index * nb_elts)),
                   int(math.floor((index + 1) * nb_elts)))
                  for index in range(nb_subspaces)]
        if self.verbose:
            print 'Distributing domain for variable', variable
        modified = []
        for (dom, (end, start)) in zip(args, slices) :
            dom[variable].remove_values(values[:end])
            dom[variable].remove_values(values[start:])
            modified.append(dom[variable])
        return modified

class DichotomyDistributor(SplitDistributor):
    """distributes domains by splitting the smallest domain in
    two equal parts or as equal as possible"""
    def __init__(self, c_space):
        SplitDistributor.__init__(self, c_space, 2)


class EnumeratorDistributor(SplitDistributor):
    """distributes domains by splitting the smallest domain
    in domains of size 1."""
    def __init__(self, c_space):
        SplitDistributor.__init__(self, c_space, 0)

DefaultDistributor = DichotomyDistributor
