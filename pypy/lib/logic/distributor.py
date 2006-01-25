# (c) 2000-2001 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307
# USA.

"""
distributors - part of Logilab's constraint satisfaction solver.
"""

__revision__ = '$Id: distributors.py,v 1.25 2005/01/14 15:16:21 alf Exp $'

import math, random

def make_new_domains(domains):
    """return a shallow copy of dict of domains passed in argument"""
    domain = {}
    for key, value in domains.items():
        domain[key] = value.copy()
    return domain

class AbstractDistributor(object):
    """_distribute is left unimplemented."""

    def __init__(self, nb_subspaces=2):
        self.nb_subspaces = nb_subspaces
        self.verbose = 0
        
    def findSmallestDomain(self, domains):
        """returns the variable having the smallest domain.
        (or one of such varibles if there is a tie)
        """
        domlist = [(dom.size(), variable ) for variable, dom in domains.items()
                                           if dom.size() > 1]
        domlist.sort()
        return domlist[0][1]

    def findLargestDomain(self, domains):
        """returns the variable having the largest domain.
        (or one of such variables if there is a tie)
        """
        domlist = [(dom.size(), variable) for variable, dom in domains.items()
                                          if dom.size() > 1]
        domlist.sort()
        return domlist[-1][1]

    def nb_subdomains(self, domains):
        """return number of sub domains to explore"""
        return self.nb_subspaces

    def distribute(self, domains, verbose=0):
        """do the minimal job and let concrete class distribute variables
        """
        self.verbose = verbose
        replicas = []
        for i in range(self.nb_subdomains(domains)):
            replicas.append(make_new_domains(domains))
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

    def __init__(self):
        AbstractDistributor.__init__(self)
        
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

    def __init__(self):
        AbstractDistributor.__init__(self)
        
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
    
    def __init__(self, nb_subspaces=3):
        AbstractDistributor.__init__(self, nb_subspaces)
        self.__to_split = None
    def nb_subdomains(self, domains):
        """See AbstractDistributor"""
        self.__to_split = self.findSmallestDomain(domains)
        if self.nb_subspaces:
            return min(self.nb_subspaces, domains[self.__to_split].size())
        else:
            return domains[self.__to_split].size()
    
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
    def __init__(self):
        SplitDistributor.__init__(self, 2)


class EnumeratorDistributor(SplitDistributor):
    """distributes domains by splitting the smallest domain
    in domains of size 1."""
    def __init__(self):
        SplitDistributor.__init__(self, 0)

DefaultDistributor = DichotomyDistributor
