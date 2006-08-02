from logilab.constraint.propagation import AbstractDomain, AbstractConstraint,\
       ConsistencyFailure
from rdflib import URIRef

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

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("Constraint")
py.log.setconsumer("Constraint", ansi_log)

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

        if domains[self.prop].getValues() != []:
            log ("%r"% self._variables[0])
            for indi in domains[self._variables[0]].getValues():
                log("%s" % indi)
                if not eval(self.formula)(domains[self.prop],indi):
                    raise ConsistencyFailure

class NothingConstraint(AbstractConstraint):

    def __init__(self, variable):
        AbstractConstraint.__init__(self, [variable])
        self.variable = variable

    def narrow(self, domains):
        if domains[self.variable].getValues() != []:
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
        vals += superdom.getValues()
        vals += subdom.getValues() +[self.variable]
        superdom.setValues(vals)
            
        return 0

class DisjointClassConstraint(SubClassConstraint):

    def narrow(self, domains):
        if self.variable ==self.object:
            raise ConsistencyFailure
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals1 = superdom.getValues()  
        vals2 = subdom.getValues()  
        for i in vals1:
            if i in vals2:
                raise ConsistencyFailure()

Thing_uri = URIRef(u'http://www.w3.org/2002/07/owl#Thing')

class MemberConstraint(AbstractConstraint):

    def __init__(self, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [ cls_or_restriction])
        self.object = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        x_vals = domains[self.object].getValues()
        if self.variable not in x_vals:
            raise ConsistencyFailure("%s not in %s"% (self.variable, self.object))

class ComplementOfConstraint(SubClassConstraint):

    def narrow(self, domains):
        vals = domains[self.variable].getValues()
        x_vals = domains[self.object].getValues()
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
                for item in val:
                    for otheritem in val:
                        if (otheritem == item) == False: 
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

    def __init__(self, variable, property, value):
        AbstractConstraint.__init__(self, [variable])
        self.variable = variable
        self.property = property
        self.value = value

    cost = 100

    def estimateCost(self, domains):
        return self.cost

    def narrow(self, domains):
        """ This is to check the assertion that the class self.variable has a value of self.value
            for the property """
        val = self.value
        prop = domains[self.property].getValuesPrKey(self.variable)
        for v in prop:
            if v == val:
                break
        else:
            raise ConsistencyFailure(
                    "The value of the property %s in the class %s has a value not from %r"
                        %(self.property, self.variable, self.value))

