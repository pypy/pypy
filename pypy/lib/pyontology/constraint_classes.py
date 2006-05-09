from logilab.constraint.propagation import AbstractDomain, AbstractConstraint, ConsistencyFailure

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

class MaxCardinality(AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, variable, cardinality):
        AbstractConstraint.__init__(self, [variable])
        self.cost = 80
        self.variable = variable
        self.cardinality = cardinality

    def __repr__(self):
        return '<%s  %s %i>' % (self.__class__.__name__, str(self._variables[0]), self.cardinality)

    def estimateCost(self, domains):
        return self.cost
    
    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        prop = domains[self.variable].property
        props = Linkeddict(domains[prop].getValues())
        dom = domains[self.variable].getValues()
        if not dom:
            return 0
        cls = dom[0]
        card = get_cardinality(props, cls)
        if card > self.cardinality:
            raise ConsistencyFailure("Maxcardinality of %i exceeded by the value %i" %(self.cardinality,len(props[cls])))
        else:
            return 1

class MinCardinality(MaxCardinality):

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        prop = domains[self.variable].property
        props = Linkeddict(domains[prop].getValues())
        cls = domains[self.variable].getValues()[0]
        card = get_cardinality(props, cls)
        if card < self.cardinality:
            raise ConsistencyFailure("MinCardinality of %i not achieved by the value %i" %(self.cardinality,len(props[cls])))
        else:
            return 1
        
class Cardinality(MaxCardinality):
    
    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        prop = domains[self.variable].property
        props = Linkeddict(domains[prop].getValues())
        cls = domains[self.variable].getValues()[0]
        card = get_cardinality(props, cls)
        if card != self.cardinality:
            raise ConsistencyFailure("Cardinality of %i exceeded by the value %r for %r" %
                                     (self.cardinality, props[cls], prop))
        else:
            return 1

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
        vals += superdom.getValues()
        vals += subdom.getValues() +[self.variable]
        superdom.setValues(vals)
            
        return 0

class DisjointClassConstraint(SubClassConstraint):

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals1 = superdom.getValues()  
        vals2 = subdom.getValues()  
        for i in vals1:
            if i in vals2:
                raise ConsistencyFailure()

class ComplementClassConstraint(SubClassConstraint):

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]

class RangeConstraint(SubClassConstraint):

    cost = 30
    
    def narrow(self, domains):
        propdom = domains[self.variable]
        rangedom = domains[self.object]
        newrange = rangedom.getValues()
        res = []
        oldrange = propdom.range
        if oldrange:
            for v in oldrange:
                if v in newrange:
                    res.append(v)
        else:
            res = newrange
        propdom.range = res
        propdom.setValues([(None,i) for i in res])
        #prop = Linkeddict(propdom.getValues())
        #for pval in sum(prop.values(),[]):
        #    if pval not in range:
        #        raise ConsistencyFailure("Value %r not in range %r for Var %s"%(pval,range, self.variable))

class DomainConstraint(SubClassConstraint):

    cost = 200

    def narrow(self, domains):
        propdom = domains[self.variable]
        domaindom = domains[self.object]
        newdomain = domaindom.getValues() +[self.object]
        domain = []
        olddomain = propdom.domain
        if olddomain:
            for v in olddomain:
                if v in newdomain:
                    domain.append(v)
        else:
            domain = newdomain
        propdom.domain = domain
        prop = Linkeddict(propdom.getValues())
        for pval in prop.keys():
            if pval not in domain:
                raise ConsistencyFailure("Value %r not in range %r"%(pval, domain))

class SubPropertyConstraint(SubClassConstraint):

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals = superdom.getValues()
        for (key, val) in subdom.getValues():
            if not (key, val) in superdom:
                for v in val:
                    superdom.addValue(key, v)

class EquivalentPropertyConstraint(SubClassConstraint):

    cost = 100
    
    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals = superdom.getValues()  
        for val in subdom.getValues():
            if not val in vals:
                raise ConsistencyFailure("The Property %s is not equivalent to Property %s" %
                                         (self.variable, self.object))

class TypeConstraint(SubClassConstraint):
    cost = 1
    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals = []
        vals += superdom.getValues()  
        vals.append(self.variable)
        superdom.setValues(vals)
        return 1

class FunctionalCardinality(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        domain_dict = Linkeddict(domain)
        for cls, val in domain_dict.items():
            if len(val) != 1:
                raise ConsistencyFailure("FunctionalCardinality error")
        else:
            return 0

class InverseFunctionalCardinality(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        vals = {}
        for cls, val in domain:
            for v in val:
                if vals.has_key(v):
                    raise ConsistencyFailure("InverseFunctionalCardinality error")
                else:
                    vals[v] = 1
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
        obj_domain = domains[self.object].getValues()
        sub_domain = domains[self.variable].getValues()
        res = []
        for cls, val in obj_domain:
            for v in val:
                if not (v,cls) in sub_domain:
                    raise ConsistencyFailure("Inverseof failed for (%r, %r) in %r" % 
                                         (val, cls, sub_domain) )
        for cls, val in sub_domain:
            for v in val:
                if not (val,cls) in obj_domain:
                    raise ConsistencyFailure("Inverseof failed for (%r, %r) in %r" % 
                                         (val, cls, obj_domain)) 

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
                vals = dom.getValues()
                if hasattr(dom, '_dict'):
                    val = Linkeddict(vals)
                    if self.variable in val.keys() and not self.object in val.keys():
                        vals +=[dom.addValue(self.object,v) for v in val[self.variable]]
                        #dom.setValues(vals)
                    elif not self.variable in val.keys() and self.object in val.keys():
                        vals +=[dom.addValue(self.variable,v) for v in val[self.object]]
                        #dom.setValues(vals)
                    elif self.variable in val.keys() and self.object in val.keys():
                        if not val[self.object] == val[self.variable]:
                            raise ConsistencyFailure("Sameas failure: The two individuals (%s, %s) \
                                                has different values for property %r"%(self.variable, self.object, dom))
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
        vals += domains[self.variable].getValues()
        if vals == []:
            return 0
        while True:
            if vals[-1] in domains.keys() and isinstance(domains[vals[-1]], List):
                vals = vals[:-1] + domains[vals[-1]].getValues()
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
        vals = domains[self.variable].getValues()
        if vals:
            cls = vals[0]
            props = domains[prop].getValues()
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
        val = domains[self.List].getValues()
        if isinstance(domains[self.variable],Restriction):
            # This should actually never happen ??
            property = domains[self.variable].property
            cls = domains[self.variable].getValues()[0]
            prop = Linkeddict(domains[property].getValues())
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
        val = domains[self.List].getValues()
        union = []
        for v in val:
            for u in domains[v].getValues():
                if not u in union:
                    union.append(u)
        cls = domains[self.variable].setValues(union)
        
class IntersectionofConstraint(OneofPropertyConstraint):

    cost = 200

    def narrow(self, domains):
        val = domains[self.List].getValues()
        intersection = domains[val[0]].getValues()
        for v in val[1:]:
            vals= domains[v].getValues()
            remove = []
            for u in intersection:
                if not u in vals:
                    remove.append(u)
            for u in remove:
                intersection.remove(u)
        cls = domains[self.variable].setValues(intersection)
        term = {}
        for l in [domains[x] for x in val]:
            if hasattr(l,'TBox'):
                TBox = l.TBox
                prop = l.property
                for item in TBox.values():
                    term.setdefault(prop,[])
                    term[prop].append(item)
        for prop in term:
            axioms = term[prop]
            ranges = [ax[0] for ax in axioms]
            res = []
            while axioms:
                r, comp = axioms.pop(0)
                if res:
                    res = [x for x in res if eval('x %s r' % comp)]
                else:
                    res = [x for x in r if eval('x %s r' % comp)]
                if not res:
                    axioms.append((r,comp))
        if not res:
            raise ConsistencyFailure("Inconsistent use of intersectionOf")

class SomeValueConstraint(OneofPropertyConstraint):

    cost = 100
        
    def narrow(self, domains):
        val = domains[self.List].getValues()
        property = domains[self.variable].property
        cls = domains[self.variable].getValues()[0]
        prop = Linkeddict(domains[property].getValues())
        for v in prop[cls]:
            if v in val:
                break
        else:
            raise ConsistencyFailure(
                    "The value of the property %s in the class %s has no values from %r"
                        %(property, cls, val))

class AllValueConstraint(OneofPropertyConstraint):

    cost = 100
        
    def narrow(self, domains):
        val = domains[self.List].getValues()
        property = domains[self.variable].property
        cls = domains[self.variable].getValues()[0]
        prop = Linkeddict(domains[property].getValues())
        for v in prop[cls]:
            if not v in val:
                raise ConsistencyFailure(
                    "The value of the property %s in the class %s has a value not from %r"
                        %(property, cls, val))

class HasvalueConstraint(AbstractConstraint):

    def __init__(self, variable, List):
        AbstractConstraint.__init__(self, [variable])
        self.variable = variable
        self.List = List

    cost = 100

    def estimateCost(self, domains):
        return self.cost

    def narrow(self, domains):
        val = self.List
        property = domains[self.variable].property
        cls = domains[self.variable].getValues()[0]
        prop = Linkeddict(domains[property].getValues())
        for v in prop[cls]:
            if v == val:
                break
        else:
            raise ConsistencyFailure(
                    "The value of the property %s in the class %s has a value not from %r"
                        %(property, cls, val))

