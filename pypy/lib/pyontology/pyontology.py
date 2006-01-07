from rdflib import Graph, URIRef, BNode, Literal
from logilab.constraint import  Repository, Solver
from logilab.constraint.fd import Equals, AllDistinct, BinaryExpression, Expression 
from logilab.constraint.fd import  FiniteDomain as fd
from logilab.constraint.propagation import AbstractDomain, AbstractConstraint, ConsistencyFailure
import sys

namespaces = {
    'rdf' : 'http://www.w3.org/1999/02/22-rdf-syntax-ns',
    'rdfs' : 'http://www.w3.org/2000/01/rdf-schema',
    'xmlns' : 'http://www.w3.org/1999/xhtml',
    'owl' : 'http://www.w3.org/2002/07/owl',
}

uris = {}
for k,v in namespaces.items(): 
    uris[v] = k

Class = URIRef(u'http://www.w3.org/2002/07/owl#Class')
rdf_rest = URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#rest')
rdf_first = URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#first')

class ClassDomain(AbstractDomain):

    # Class domain is intended as a (abstract/virtual) domain for implementing
    # Class axioms. Working on class descriptions the class domain should allow
    # creation of classes through axioms.
    # The instances of a class can be represented as a FiniteDomain in values (not always see Disjointwith)
    # Properties of a class is in the dictionary "properties"
    # The bases of a class is in the list "bases"

    def __init__(self, name='', values=[], bases = []):
        AbstractDomain.__init__(self)
        self.bases = bases+[self]
        self.values = values
        self.name = name
        self.properties = {}

    def __repr__(self):
        return "<%s %s %r>" % (self.__class__, str(self.name),self.getValues())

    def __getitem__(self, index):
        return None

    def __iter__(self):
        return iter(self.bases) 

    def size(self):
        return len(self.bases)

    __len__ = size

    def copy(self):
        return self

    def removeValues(self, values):
        for val in values:
            self.values.pop(self.values.index(val))

    def getBases(self):
        return self.bases

    def getValues(self):
        return self.values

    def setValues(self, values):
        self.values = values

class List(ClassDomain):
    def __init__(self, name='', values=[], bases = []):
        ClassDomain.__init__(self, name, values, bases)
        self.constraint = ListConstraint(name)
        
class Property(ClassDomain):
    # Property contains the relationship between a class instance and a value
    # - a pair. To accomodate global assertions like 'range' and 'domain' attributes
    # for range and domain must be filled in by rdfs:range and rdfs:domain 

    def __init__(self, name='', values=[], bases = []):
        ClassDomain.__init__(self, name, values, bases)
        self._dict = Linkeddict()
        self.range = []
        self.domain = []

    def getValues(self):
        items = self._dict.items()
        res = []
        for k,v in items:
            for i in v:
                res.append((k,i))
        return res

    def setValues(self, values):
        self._dict = Linkeddict(values)

    def removeValues(self, values):
        for k,v in values:
            vals = self._dict[k]
            if vals == [None]:
                self._dict.pop(k)
            else:
                self._dict[k] = [ x for x in vals if x != v] 
            
class ObjectProperty(Property):

    pass

class DatatypeProperty(Property):
    pass

class Thing(ClassDomain):
    pass

class DataRange(ClassDomain):
    pass

class AllDifferent(ClassDomain):
    # A special class whose members are distinct
    # Syntactic sugar
    pass

class Nothing(ClassDomain):

    pass


class FunctionalProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = FunctionalCardinality(name)
        
class InverseFunctionalProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = InverseFunctionalCardinality(name)

class TransitiveProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = TransitiveConstraint(name)

class SymmetricProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = SymmetricConstraint(name)

class Restriction(ClassDomain):
    pass

builtin_voc = {
               'Thing' : Thing,
               'Class' : ClassDomain,
               'ObjectProperty' : ObjectProperty,
               'AllDifferent' : AllDifferent ,
##               'AnnotationProperty' : AnnotationProperty,
               'DataRange' : DataRange,
               'DatatypeProperty' : DatatypeProperty,
##               'DeprecatedClass' : DeprecatedClass,
##               'DeprecatedProperty' : DeprecatedProperty,
               'FunctionalProperty' : FunctionalProperty,
               'InverseFunctionalProperty' : InverseFunctionalProperty,
##               'Nothing' : Nothing,
##               'ObjectProperty' : ObjectProperty,
##               'Ontology' : Ontology,
##               'OntologyProperty' : OntologyProperty,
               'Restriction' : Restriction,
               'SymmetricProperty' : SymmetricProperty,
               'TransitiveProperty' : TransitiveProperty,
               'List' : List
              }
  
class Ontology(Graph):

    def __init__(self):
        Graph.__init__(self)
        self.variables = {}
        self.constraints = []
        self.seen = {}
        self.var2ns ={}

    def add_file(self, f):
        tmp = Graph()
        tmp.load(f)
        for i in tmp.triples((None,)*3):
            self.add(i)

    def attach_fd(self):
        for (s, p, o) in (self.triples((None, None, None))):
            if p.find('#') != -1:
                ns, func = p.split('#')
            else:
                ns =''
                func = p
            if ns in namespaces.values():
                #predicate is one of builtin OWL predicates
                pred = getattr(self, func)
                res = pred(s, o) 
                if not res :
                    continue
                if type(res) != list :
                    res = [res]
                avar = self.make_var(ClassDomain, s) 
            else:
                res = [o]
                avar = self.make_var(Property, p)
                # Set the values of the property p to o
                sub = self.make_var(ClassDomain, s) 
                obj = self.make_var(Thing, o) 
                res = self.variables[avar].getValues() 
                self.variables[avar].setValues(res + [(sub, obj)])

    def solve(self,verbose=0):
        #self.merge_constraints()
        rep = Repository(self.variables.keys(), self.variables, self.constraints)
        return Solver().solve(rep, verbose)

    def consistency(self, verbose=0):
        self.rep = Repository(self.variables.keys(), self.variables, self.constraints[:])
        self.rep.consistency(verbose)
 
    def get_list(self, subject):
        res = []
        first = list(self.objects(subject, rdf_first)) 
        assert len(first) == 1
        if type(first[0]) == URIRef:
            var = self.make_var(ClassDomain, first[0])
        res += first
        
        rest = list(self.objects(subject, rdf_rest)) 
        if "#nil" in rest[0] :
           return res
        else:
           res += self.get_list(rest[0])
        return res

    def make_var(self, cls=fd, a=''):
        if type(a) == URIRef:
            if a.find('#') != -1:
                ns,name = a.split('#')
            else:
                ns,name = a,''
            if ns not in uris.keys():
                uris[ns] = ns.split('/')[-1]
            a = uris[ns] + '_' + name    
            var = str(a.replace('-','_'))
        else:
            var = a
        if not cls:
            return var
        if not var in self.variables.keys():
            self.variables[var] = cls(var)
        elif type(self.variables[var]) != cls:
            olddom = self.variables[var]
            newdom = cls(var)
            newdom.setValues(olddom.getValues())
            self.variables[var] = newdom
        return var 

    def find_prop(self, s):
        p = URIRef(u'http://www.w3.org/2002/07/owl#onProperty')
        pr = list(self.objects(s,p))
        assert len(pr) == 1
        return pr[0]

    def find_cls(self, s):
        p = URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
        r = URIRef(u'http://www.w3.org/2000/01/rdf-schema#subClassOf')
        if type(s) == BNode:
            pr = list( self.subjects(p,s) )
            if len(pr) == 0:
                pr = list( self.subjects(r,s) )
            return pr[0]
        else:
            return s
               
    def find_uriref(self, s):
        while type(s) == BNode:
            s = list(self.subjects(None,s))[0]
        return s

    def find_property(self, s):
        prop = self.find_prop(s)
        avar = self.make_var(Property, prop)
        return avar
    
#---------------- Implementation ----------------

    def type(self, s, var):
        if not (var in [URIRef(namespaces[ns]+'#'+x) for x in builtin_voc for ns in namespaces]):
            # var is not one of the builtin classes
            avar = self.make_var(ClassDomain, var)
            svar = self.make_var(self.variables[avar].__class__, s)
            constrain = BinaryExpression([svar, avar],"%s in %s" %(svar,  avar))
            self.constraints.append(constrain)
        else:
            # var is a builtin class
            cls =builtin_voc[var.split('#')[-1]]
            svar = self.make_var(cls, s)
            cls = self.variables[svar]
            if hasattr(cls, 'constraint'):
                self.constraints.append(cls.constraint)

    def first(self, s, var):
        avar = self.make_var(None, var)
        svar = self.make_var(List, s)
        vals = []
        vals += self.variables[svar].getValues()
        vals.insert(0, avar)
        self.variables[svar].setValues(vals)

    def rest(self, s, var):
        if var == URIRef(namespaces['rdf']+'#nil'):
            return 
        else:
            avar = self.make_var(List, var)
        svar = self.make_var(List, s)
        vals = []
        vals += self.variables[svar].getValues()
        vals.append( avar)
        self.variables[svar].setValues(vals)

    def onProperty(self, s, var):
        pass

#---Class Axioms---#000000#FFFFFF-----------------------------------------------

    def subClassOf(self, s, var):
        # s is a subclass of var means that the 
        # class extension of s is a subset of the
        # class extension of var. 
        avar = self.make_var(None, var)
        svar = self.make_var(None, s)
        cons = SubClassConstraint( svar, avar)
        self.constraints.append(cons)

    def equivalentClass(self, s, var):
        self.subClassOf(s, var)
        self.subClassOf(var, s)

    def disjointWith(self, s, var):
        avar = self.make_var(None, var)
        svar = self.make_var(None, s)
        constrain = DisjointClassConstraint(svar, avar) 
        self.constraints.append(constrain)

    def complementOf(self, s, var):
        # add constraint of not var
        # TODO: implementthis for OWL DL
##        avar = self.make_var(ClassDomain, var)
##        svar = self.make_var(ClassDomain, s)
            pass

    def oneOf(self, s, var):
        res = self.get_list(var)
        #prop = self.find_uriref(s)
        avar = self.make_var(None, s)
        if self.variables.get(avar) and type(self.variables[avar]) == fd:
            self.variables[avar] = fd(list(self.variables[avar].getValues()) + res)
        else:
            self.variables[avar] = fd(res)

    def unionOf(self,s, var):
        res = self.get_list(var)
        return res #There might be doubles (but fd takes care of that)

    def intersectionOf(self, s, var):
        res = self.get_list(var)
        result = {}.fromkeys(res[0])
        for el in res:
            for cls in result.keys():
                if cls not in el:
                   result.pop(cls)
        return result.keys()

#---Property Axioms---#000000#FFFFFF--------------------------------------------

    def range(self, s, var):
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(Property, s)
        cons = RangeConstraint(svar, avar)
        self.constraints.append(cons)

    def domain(self, s, var):
        # The classes that has this property (s) must belong to the class extension of var
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(Property, s)
        cons = DomainConstraint(svar, avar)
        self.constraints.append(cons)

    def subPropertyOf(self, s, var):
        # s is a subproperty of var
        avar = self.make_var(Property, var)
        svar = self.make_var(Property, s)
        cons = SubPropertyConstraint( svar, avar)
        self.constraints.append(cons)

    def equivalentProperty(self, s, var):
        avar = self.make_var(Property, var)
        svar = self.make_var(Property, s)
        cons = EquivalentPropertyConstraint( svar, avar)
        self.constraints.append(cons)

    def inverseOf(self, s, var):
        avar = self.make_var(Property, var)
        svar = self.make_var(Property, s)
        con = InverseofConstraint(svar, avar)
        self.constraints.append(con)

#---Property restrictions------------------------------------------------------

    def maxCardinality(self, s, var):
        """ Len of finite domain of the property shall be less than or equal to var"""
        avar = self.find_property(s)
        cls =self.make_var(None, self.find_cls(s))
        constrain = MaxCardinality(avar, cls, int(var))
        self.constraints.append(constrain) 

    def minCardinality(self, s, var):
        """ Len of finite domain of the property shall be greater than or equal to var"""
        avar = self.find_property(s)
        cls =self.make_var(None, self.find_cls(s))
        constrain = MinCardinality(avar, cls, int(var))
        self.constraints.append(constrain) 

    def cardinality(self, s, var):
        """ Len of finite domain of the property shall be equal to var"""
        avar = self.find_property(s)
        cls =self.make_var(None, self.find_cls(s))
        # Check if var is an int, else find the int buried in the structure
        constrain = Cardinality(avar, cls, int(var))
        self.constraints.append(constrain) 

    def differentFrom(self, s, var):
        s_var = self.make_var(ClassDomain, s)
        var_var = self.make_var(Thing, var)
        constrain = BinaryExpression([s_var, var_var],"%s != %s" %(s_var,  var_var))
        self.constraints.append(constrain)

    def distinctMembers(self, s, var):
        res = self.get_list(var)
        self.constraints.append(AllDistinct([self.make_var(ClassDomain, y) for y in res]))
        return res

    def sameAs(self, s, var):
        s_var = self.make_var(None, s)
        var_var = self.make_var(None, var)
        constrain = BinaryExpression([s_var, var_var],
               "%s == %s" %(s_var, var_var))
        self.constraints.append(constrain)

    def hasValue(self, s, var):
        if type(var) != URIRef:
            value = var
        else:
            value = self.make_var(None, var)
        prop = self.find_prop(s)
        cls = self.make_var(None, self.find_cls(s))
        con = HasvalueConstraint(prop, cls, value)
        self.constraints.append(con)
        
    def allValuesFrom(self, s, var):
        # TODO: implement this 
        pass

    def someValuesFrom(self, s, var):
        # TODO: implement this 
        pass

    def imports(self, s, var):
        # PP TODO: implement this 
        pass

# ----------------- Helper classes ----------------

class OwlConstraint(AbstractConstraint):

    def __init__(self, variable):
        AbstractConstraint.__init__(self, [variable])
        self.variable = variable
        self.__cost = 1 

    def __repr__(self):
        return '<%s  %s>' % (self.__class__.__name__, str(self._variables[0]))

    def estimateCost(self, domains):
        return self.__cost


class MaxCardinality(AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, variable, cls, cardinality):
        AbstractConstraint.__init__(self, [variable, cls])
        self.__cost = 2
        self.cardinality = cardinality
        self.cls = cls

    def __repr__(self):
        return '<%s  %s %i>' % (self.__class__.__name__, str(self._variables[0]), self.cardinality)

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        prop = Linkeddict(domains[self.variable].getValues())
        if len(prop[self.cls]) > self.cardinality:
            raise ConsistencyFailure("Maxcardinality exceeded")
        else:
            return 1

class MinCardinality(MaxCardinality):

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        prop = Linkeddict(domains[self.variable].getValues())
        if len(prop[self.cls]) < self.cardinality:
            raise ConsistencyFailure("MinCardinality not accomplished")
        else:
            return 1
        
class Cardinality(MaxCardinality):
    
    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        prop = Linkeddict(domains[self.variable].getValues())
        if len(prop[self.cls]) != self.cardinality:
            raise ConsistencyFailure("Cardinality constraint not met")
        else:
            return 1


def get_values(dom, domains, attr = 'getValues'):
    res = []
    if type(dom) == Literal:
        return [dom]
    for val in getattr(dom, attr)():
        res.append(val)
        if type(val) == tuple:
            val = val[0]
        if val in domains.keys():
            res.extend(get_values(domains[val], domains, attr))
    return res

class SubClassConstraint(AbstractConstraint):

    def __init__(self, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [variable, cls_or_restriction])
        self.object = cls_or_restriction
        self.variable = variable

    def __repr__(self):
        return '<%s  %s %s>' % (self.__class__.__name__, str(self._variables[0]), self.object)

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        bases = get_values(superdom, domains, 'getBases')  
        subdom.bases += [bas for bas in bases if bas not in subdom.bases]
        vals = get_values(subdom, domains, 'getValues')
        superdom.values += [val for val in vals if val not in superdom.values]

class DisjointClassConstraint(SubClassConstraint):

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        bases = get_values(superdom, domains, 'getBases')  
        subdom.bases += [bas for bas in bases if bas not in subdom.bases]
        vals1 = get_values(superdom, domains, 'getValues')  
        vals2 = get_values(subdom, domains, 'getValues')  
        for i in vals1:
            if i in vals2:
                raise ConsistencyFailure()

class ComplementClassConstraint(SubClassConstraint):

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]

class RangeConstraint(SubClassConstraint):

    def narrow(self, domains):
        propdom = domains[self.variable]
        rangedom = domains[self.object]
        newrange = get_values(rangedom, domains, 'getValues')  
        range = []
        oldrange = propdom.range
        if oldrange:
            for v in oldrange:
                if v in newrange:
                    range.append(v)
        else:
            range = newrange
        propdom.range = range
        prop = Linkeddict(propdom.getValues())
        for pval in sum(prop.values(),[]):
            if pval not in range:
                raise ConsistencyFailure("Value %r not in range %r"%(pval,range))

class DomainConstraint(SubClassConstraint):

    def narrow(self, domains):
        propdom = domains[self.variable]
        domaindom = domains[self.object]
        newdomain = get_values(domaindom, domains, 'getValues') +[self.object]
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
        vals = get_values(superdom, domains, 'getValues')  
        for val in subdom.getValues():
            if not val in vals:
                vals.append(val)
        superdom.setValues(vals)

class EquivalentPropertyConstraint(SubClassConstraint):

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.object]
        vals = get_values(superdom, domains, 'getValues')  
        for val in subdom.getValues():
            if not val in vals:
                raise ConsistencyFailure("Value not in prescribed range")

class FunctionalCardinality(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        domain_dict = Linkeddict(domain)
        for cls, val in domain_dict.items():
            if len(val) != 1:
                raise ConsistencyFailure("Maxcardinality exceeded")
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
                raise ConsistencyFailure("Maxcardinality exceeded")
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
##            dict.__getitem__(self,k).append(v)
            
class TransitiveConstraint(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        domain_dict = Linkeddict(domain)
        for cls, val in domain:
            if  val in domain_dict:
                for v in domain_dict[val]:
                    domain.append((cls,v))
        domains[self.variable].setValues(domain)

class SymmetricConstraint(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        for cls, val in domain:
            if not (val, cls) in domain:
                domain.append((val,cls))
        domains[self.variable].setValues(domain)

class InverseofConstraint(SubClassConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        obj_domain = domains[self.object].getValues()
        sub_domain = domains[self.variable].getValues()
        res = []
        for cls, val in obj_domain:
            if not (val,cls) in sub_domain:
                raise ConsistencyFailure("Inverseof failed") 
        for cls, val in sub_domain:
            if not (val,cls) in obj_domain:
                raise ConsistencyFailure("Inverseof failed") 

class ListConstraint(AbstractConstraint):
    """Contraint: all values must be distinct"""
    def __init__(self, variable):
        AbstractConstraint.__init__(self, [variable])
        self.variable = variable
        self.__cost = 10

    def estimateCost(self, domains):
        return self.__cost

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        vals =[]
        vals += domains[self.variable].getValues()
        while True:
            if vals[-1] in domains.keys() and isinstance(domains[vals[-1]], List):
                vals = vals[:-1] + domains[vals[-1]].getValues()
            else:
                break
        domains[self.variable].setValues(vals)
        return 1

class HasvalueConstraint:
    pass
