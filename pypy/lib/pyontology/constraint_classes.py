from logilab.constraint.propagation import AbstractDomain, AbstractConstraint,\
       ConsistencyFailure, Solver
from logilab.constraint.distributors import DichotomyDistributor, SplitDistributor
from logilab.constraint.fd import Expression
from rdflib import URIRef
try:
    # not sure if we have this when running on PyPy
    # this is needed for verbose, only (see solve method)
    from time import strftime
except ImportError:
    pass

import autopath
import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("Constraint")
py.log.setconsumer("Constraint", None)
import math

class MySolver(Solver):

    def _solve(self, repository, recursion_level=0):
        """main generator"""
        solve = self._solve
        verbose = self.verbose
        if recursion_level > self.max_depth:
            self.max_depth = recursion_level
        if verbose:
            print strftime('%H:%M:%S'),
            print '*** [%d] Solve called with repository' % recursion_level,
            print repository
        try:
            foundSolution = repository.consistency(verbose)
        except ConsistencyFailure, exc:
            if verbose:
                print strftime('%H:%M:%S'), exc
            pass
        else:
            if foundSolution: 
                solution = {}
                for variable, domain in repository.getDomains().items():
                    solution[variable] = list(domain.getValues())[0]
                if verbose:
                    print strftime('%H:%M:%S'), '### Found Solution', solution
                    print '-'*80
                yield solution
            else:
                for repo in repository.distribute(self._distributor,
                                                  verbose):
                    for solution in solve(repo, recursion_level+1):
                        if solution is not None:
                            yield solution
                            
        if recursion_level == 0 and self.verbose:
            print strftime('%H:%M:%S'),'Finished search'
            print strftime('%H:%M:%S'),
            print 'Maximum recursion depth = ', self.max_depth

class MyExpression(Expression):

    def _assign_values(self, domains):
        variables = []
        kwargs = {}
        for variable in self._variables:
            domain = domains[variable]
            values = list(domain.getValues())
            variables.append((domain.size(), [variable, values, 0, len(values)]))
            kwargs[variable] = values[0]
        # sort variables to instanciate those with fewer possible values first
        variables.sort()

        go_on = 1
        while go_on:
            yield kwargs
            # try to instanciate the next variable
            for size, curr in variables:
                if (curr[2] + 1) < curr[-1]:
                    curr[2] += 1
                    kwargs[curr[0]] = curr[1][curr[2]]
                    break
                else:
                    curr[2] = 0
                    kwargs[curr[0]] = curr[1][0]
            else:
                # it's over
                go_on = 0
 

class MyDistributor(SplitDistributor):

    def __init__(self):
        SplitDistributor.__init__(self,2)
        self.to_split = None

    def nb_subdomains(self, domains):
        """See AbstractDistributor"""
        self.to_split = self.findSmallestDomain(domains)
        if self.nb_subspaces:
            return min(self.nb_subspaces, domains[self.to_split].size())
        else:
            return domains[self.to_split].size()
 
    def _distribute(self, *args):
        """See AbstractDistributor"""
        variable = self.to_split
        nb_subspaces = len(args)
        values = list(args[0][variable].getValues())
        nb_elts = max(1, len(values)*1./nb_subspaces)
        slices = [(int(math.floor(index * nb_elts)),
                   int(math.floor((index + 1) * nb_elts)))
                  for index in range(nb_subspaces)]
        if self.verbose:
            print 'Distributing domain for variable', variable
        modified = []
        for (dom, (end, start)) in zip(args, slices) :
            dom[variable].removeValues(values[:end])
            dom[variable].removeValues(values[start:])
            modified.append(dom[variable])
        return modified

class OwlConstraint(AbstractConstraint):

    cost = 1
    
    def __init__(self, variable):
        AbstractConstraint.__init__(self, [variable])
        self.variable = variable

    def __repr__(self):
        return '<%s  %s>' % (self.__class__.__name__, str(self._variables[0]))

    def estimateCost(self, domains):
        return self.cost

def get_cardinality(props, cls):
        if props.get(cls):
           card = len(props[cls]) 
        elif props.get(None):
           card = len(props[None]) 
        else:
           card = 0
        return card 

class CardinalityConstraint(AbstractConstraint):

    cost = 10

    def __init__(self, prop, restr, var, comp):
        AbstractConstraint.__init__(self, [restr])
        self.prop = prop 
        self.formula = "lambda x,y:len(x.getValuesPrKey(y)) %s int(%s)"% (comp, var)

    def estimateCost(self, domains):
        return self.cost

    def narrow(self, domains):
        log(self.formula)

        if domains[self.prop].size() != 0:
            log ("%r"% self._variables[0])
            for indi in domains[self._variables[0]].getValues():
                log("%s" % indi)
                if not eval(self.formula)(domains[self.prop],indi):
                    raise ConsistencyFailure

class NothingConstraint(AbstractConstraint):
    cost = 1

    def __init__(self, variable):
        AbstractConstraint.__init__(self, [variable])
        self.variable = variable

    def narrow(self, domains):
        if domains[self.variable].size() != 0:
            raise ConsistencyFailure

class SubClassConstraint(AbstractConstraint):

    cost=1
    
    def __init__(self, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [variable, cls_or_restriction])
        self.object = cls_or_restriction
        self.variable = variable
        
    def estimateCost(self, domains):
        return self.cost

    def __repr__(self):
        return '<%s  %s %s>' % (self.__class__.__name__, str(self._variables[0]), self.object)

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals = []
        vals += list(superdom.getValues())
        vals += list(subdom.getValues()) #+[self.variable]
        superdom.setValues(vals)
            
        return 0

class DisjointClassConstraint(SubClassConstraint):

    def narrow(self, domains):
        if self.variable ==self.object:
            raise ConsistencyFailure
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals1 = superdom.getValues()  
        for i in vals1:
            if i in subdom:
                raise ConsistencyFailure()

Thing_uri = URIRef(u'http://www.w3.org/2002/07/owl#Thing')

class PropertyConstrain(AbstractConstraint):
    cost = 1

    def __init__(self, prop, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [ prop])
        self.object = cls_or_restriction
        self.variable = variable
        self.prop = prop

    def narrow(self, domains):
        # Narrow the list of properties (instances of some property type)
        # to those who has a pair (self.variable, self.object)
        dom = domains[self.prop]
        vals = dom.getValues()
        for p in vals:
            if not ((self.variable, self.object) in domains[p]):
                dom.removeValue(p)

class PropertyConstrain2(AbstractConstraint):
    cost = 1
    def __init__(self, prop, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [ prop])
        self.object = cls_or_restriction
        self.variable = variable
        self.prop = prop

    def narrow(self, domains):
        # Narrow the list of properties (instances of some property type)
        # to those who has a pair (self.variable, self.object)
        dom = domains[self.prop]
        sub = domains[self.variable]
        vals = dom.getValues()
        keep = []
        for p in vals:
            items = domains[p].getValuesPrKey()
            for key, obj_list in items:
                if not self.object in obj_list:
                    dom.removeValue(p)
                else:
                    keep.append(key)
        sub.removeValues([v for v in sub.getValues() if not v in keep])

class PropertyConstrain3(AbstractConstraint):
    cost = 1
    def __init__(self, prop, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [ prop])
        self.object = cls_or_restriction
        self.variable = variable
        self.prop = prop
    
    def narrow(self, domains):
        # Narrow the domains of object and variable to those values 
        # that are connected by self.prop
        dom = domains[self.prop]
        sub = domains[self.variable]
        obj = domains[self.object]
        vals_dict = dom._dict 

        keep = set()
        sub_rem = []
        for v in sub.getValues():
            if not v in vals_dict:
                sub_rem.append(v)
                #sub.removeValue(v)
            else:
                for o in dom.getValuesPrKey(v):
                    keep.add(o)
        remove = [x for x in obj.getValues() if not x in keep]
        sub.removeValues(sub_rem)
        obj.removeValues(remove)

class MemberConstraint(AbstractConstraint):
    cost = 1

    def __init__(self, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [ cls_or_restriction])
        self.object = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        dom = domains[self.variable]
        if domains[self.object].fixed:
            x_vals = set(domains[self.object].getValues())
            for indi in dom.getValues():
                if not indi in x_vals:
                    dom.removeValue(indi) 
        else:
            x_vals = set(domains[self.object].getValues())
            if dom not in x_vals:
                raise ConsistencyFailure("%s not in %s"% (self.variable, self.object))

class ComplementOfConstraint(SubClassConstraint):

    def narrow(self, domains):
        vals = domains[self.variable].getValues()
        x_vals = domains[self.object]
        remove = []
        for v in vals:
            if v in x_vals:
                remove.append(v)
        log("Complementof %r %r"%([x.name for x in remove], [x.name for x in x_vals]))
        domains[self.variable].removeValues(remove)
        

class RangeConstraint(SubClassConstraint):

    cost = 30
    
    def narrow(self, domains):
        propdom = domains[self.variable]
        rangedom = domains[self.object]
        for cls,pval in propdom.getValues():
            if pval not in rangedom:
                raise ConsistencyFailure("Value %r of property %r not in range %r : %r"%(pval, self.variable, self.object, rangedom.size()))

class DomainConstraint(SubClassConstraint):

    cost = 200

    def narrow(self, domains):
        propdom = domains[self.variable]
        domaindom = domains[self.object]
        for cls,val in propdom.getValues():
            if cls not in domaindom:
                raise ConsistencyFailure("Value %r of property %r not in domain %r : %r"%(cls, self.variable, self.object, domaindom.size()))

class SubPropertyConstraint(SubClassConstraint):

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        for (key, val) in subdom.getValues():
            if not (key, val) in superdom:
                for v in val:
                    superdom.addValue(key, v)

class EquivalentPropertyConstraint(SubClassConstraint):

    cost = 10
    
    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        superset = set(superdom.getValues())
        superset = superset.union(set(subdom.getValues()))
        superdom.setValues(superset)
        subdom.setValues(superset)

class TypeConstraint(SubClassConstraint):
    cost = 1
    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals = []
        vals += list(superdom.getValues())  
        vals.append(self.variable)
        superdom.setValues(vals)
        return 1

class FunctionalCardinality(OwlConstraint):
    """Contraint: all values must be distinct"""
    cost = 100

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        domain_dict = Linkeddict(list(domain))
        for cls, val in domain_dict.items():
            if len(val) != 1:
                for item in val:
                    for otheritem in val:
                        if (otheritem == item) == False: 
                            raise ConsistencyFailure("FunctionalCardinality error: %s for property %s with %r" % (cls, self.variable, val))
        else:
            return 0

class InverseFunctionalCardinality(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        vals = {}
        for cls, val in domain:
            if vals.has_key(val):
                raise ConsistencyFailure("InverseFunctionalCardinality error")
            else:
                vals[val] = 1
        else:
            return 0

class Linkeddict(dict):
    def __init__(self, values=()):
        for k,v in values:
            dict.setdefault(self,k,[])
            if type(v) == list:
                dict.__setitem__(self, k, v)
            else:
                if not v in dict.__getitem__(self,k):
                    dict.__getitem__(self,k).append(v)
            
class TransitiveConstraint(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        for cls, val in domain:
            for v in val:
                if v in domains[self.variable]._dict.keys():
                    [domains[self.variable].addValue(cls,x)
                        for x in domains[self.variable]._dict[v]]

class SymmetricConstraint(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        prop = domains[self.variable]
        domain = prop.getValues()
        for cls, val in domain:
            for v in val:
                if not v in prop._dict.keys() or not cls in prop._dict[v]:
                    prop.addValue(v,cls)


class InverseofConstraint(SubClassConstraint):
    """Contraint: all values must be distinct"""
    cost = 200
    
    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        obj_domain = domains[self.object].getValuesPrKey()
        sub_domain = set(domains[self.variable].getValues())
        res = []
        for cls, val in obj_domain:
            for v in val:
                if not (v,cls) in sub_domain:
                    domains[self.variable].addValue(v, cls)
        obj_domain = set(domains[self.object].getValues())
        sub_domain = domains[self.variable].getValuesPrKey()
        for cls, val in sub_domain:
            for v in val:
                if not (v,cls) in obj_domain:
                    domains[self.object].addValue(v, cls)

class DifferentfromConstraint(SubClassConstraint):

    def narrow(self, domains):
        if self.variable == self.object:
            raise ConsistencyFailure("%s can't be differentFrom itself" % self.variable)
        else:
            return 0

class SameasConstraint(SubClassConstraint):

    def narrow(self, domains):
        if self.variable == self.object:
            return 1
        else:
            for dom in domains.values():
                vals = list(dom.getValues())
                if hasattr(dom, '_dict'):
                    val = Linkeddict(vals)
                    if self.variable in val.keys() and not self.object in val.keys():
                        vals +=[dom.addValue(self.object,v) for v in val[self.variable]]
                    elif not self.variable in val.keys() and self.object in val.keys():
                        vals +=[dom.addValue(self.variable,v) for v in val[self.object]]
                    elif self.variable in val.keys() and self.object in val.keys():
                        if not val[self.object] == val[self.variable]:
                            raise ConsistencyFailure("Sameas failure: The two individuals (%s, %s) \
                                                has different values for property %r" % \
                                                (self.variable, self.object, dom))
                else:
                    if self.variable in vals and not self.object in vals:
                        vals.append(self.object)
                    elif not self.variable in vals and self.object in vals:
                        vals.append(self.variable)
                    else:
                        continue
                    dom.setValues(vals)
            return 0

class ListConstraint(OwlConstraint):
    """Contraint: all values must be distinct"""

    cost = 10

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        
        vals =[]
        vals += list(domains[self.variable].getValues())
        if vals == []:
            return 0
        while True:
            if vals[-1] in domains.keys() and isinstance(domains[vals[-1]], List):
                vals = vals[:-1] + list(domains[vals[-1]].getValues())
                if domains[vals[-1]].remove : 
                    domains.pop(vals[-1])
            else:
                break
        domains[self.variable].setValues(vals)
        return 1

class RestrictionConstraint(OwlConstraint):

    cost = 70

    def narrow(self, domains):
        prop = domains[self.variable].property
        vals = list(domains[self.variable].getValues())
        if vals:
            cls = vals[0]
            props = list(domains[prop].getValues())
            props.append((cls, None))
            domains[prop].setValues(props)
            return 1
        else:
            return 0
        
class OneofPropertyConstraint(AbstractConstraint):

    def __init__(self, variable, list_of_vals):
        AbstractConstraint.__init__(self, [variable ])
        self.variable = variable
        self.List = list_of_vals
    cost = 100

    def estimateCost(self, domains):
        return self.cost

    def narrow(self, domains):
        val = domains[self.List]
        if isinstance(domains[self.variable],Restriction):
            # This should actually never happen ??
            property = domains[self.variable].property
            cls = list(domains[self.variable].getValues())[0]
            prop = Linkeddict(list(domains[property].getValues()))
            for v in prop[cls]:
                if not v in val:
                    raise ConsistencyFailure(
                        "The value of the property %s in the class %s is not oneof %r"
                            %(property, cls, val))
        else:
            domains[self.variable].setValues(val)
            return 1

class UnionofConstraint(OneofPropertyConstraint):

    cost = 200

    def narrow(self, domains):
        # val is a list of mangled  URIRefs
        val = domains[self.List].getValues()
        union = set() 
        for v in val:
            union = union.union(domains[v].getValues())
        domains[self.variable].setValues(union)
        
class IntersectionofConstraint(OneofPropertyConstraint):

    cost = 200

    def narrow(self, domains):
        val = list(domains[self.List].getValues())
        inter = set(domains[val[0]].getValues())
        for v in val[1:]:
            inter = inter.intersection(set(domains[v].getValues()))
        assert len(inter) > 0
        cls = domains[self.variable].setValues(inter)

class SomeValueConstraint(OneofPropertyConstraint):

    cost = 100
        
    def narrow(self, domains):
        val = set(domains[self.List].getValues())
        dom = domains[self.variable]
        property = dom.property
        indi = dom.getValues()
        prop = Linkeddict(list(domains[property].getValues()))
        for v in indi:
            if not v in prop.keys():
                dom.removeValue(v)
            else:
                prop_val = prop[v]
                for p in prop_val:
                    if p in val:
                       break
                else:
                    dom.removeValue(v)
            
class AllValueConstraint(OneofPropertyConstraint):
    """ AllValuesfrom property restriction is used to define the class
        of individuals for which the values for the property (defined 
        by the onProperty triple) all comes from the class description
        which is the object of this triple.
        The constraint shall narrow the domain of the subject class to
        only contain individuals satisfying the above condition
     """
    cost = 100
        
    def narrow(self, domains):
        val = set(domains[self.List].getValues())
        if not val:
            return 
        dom = domains[self.variable]
        property = dom.property
        indi = dom.getValues()
        prop = domains[property]._dict
        remove = []
        for v in indi:
            if not v in prop:
                remove.append(v)
            else:
                prop_val = prop[v]
                for p in prop_val:
                    if not p in val:
                       remove.append(v)
        dom.removeValues(remove)

class HasvalueConstraint(OneofPropertyConstraint):

    cost = 100

    def narrow(self, domains):
        val = self.List
        dom = domains[self.variable]
        property = dom.property
        indi = dom.getValues()
        prop = Linkeddict(domains[property].getValues())
        remove = []
        for v in indi:
            if not v in prop:
                remove.append(v)
            else:
                prop_val = prop[v] 
                if not val in prop_val:
                    remove.append(v)
        dom.removeValues(remove)


