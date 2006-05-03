from rdflib import Graph, URIRef, BNode, Literal
from logilab.constraint import  Repository, Solver
from logilab.constraint.fd import  FiniteDomain as fd
from logilab.constraint.propagation import AbstractDomain, AbstractConstraint, ConsistencyFailure
import sys, py
import time

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
rdf_nil = URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#nil')

def getUriref(ns, obj):
    return URIRef(namespaces[ns]+'#'+obj)

def check_format(f):
    if type(f) == str:
        tmp = file(f, "r")
    else:
        tmp = f.open()
    start = tmp.read(10)
    tmp.close()
    if "<" in start:
        format = "xml"
    else:
        format = "n3"
    return format

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
        self.values = {}
        self.setValues(values)
        self.name = name
        self.properties = {}
        # The TBox is a dictionary containing terminology constraints
        # on predicates for this class. Keys are predicates, constraint 
        # tupples ie. (p,'Carddinality') and values are list, comparison
        # tupples
        self.TBox = {}
        # The ABox contains the constraints the individuals of the class 
        # shall comply to 
        self.ABox = {}

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
        return self.values.keys()

    def setValues(self, values):
        self.values = dict.fromkeys(values)

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
    
    def addValue(self, key, val):
        self._dict.setdefault(key, [])
        self._dict[key].append(val)

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
    """ A owl:restriction is an anonymous class that links a class to a restriction on a property
        The restriction is only applied to the property in the conntext of the specific task. In order
        to construct a constraint to check the restriction three things are thus needed :
            1. The property to which the restriction applies - this comes from the onProperty tripple. 
                the property is saved in the Restriction class' property attribute
            2. The restriction itself. This comes from one of the property restrictions triples (oneOf, 
                maxCardinality ....). It adds a constraint class
            3. The class in which context the restriction should be applied. This comes from subClassOf, type...
                The class is saved in the restrictions cls attribute
        """
    def __init__(self, name='', values=[], bases = []):
        ClassDomain.__init__(self, name, values, bases)
        self.constraint = RestrictionConstraint(name)
        self.property = None
        
builtin_voc = {
               getUriref('owl', 'Thing') : Thing,
               getUriref('owl', 'Class') : ClassDomain,
               getUriref('owl', 'ObjectProperty') : ObjectProperty,
               getUriref('owl', 'AllDifferent') : AllDifferent ,
               getUriref('owl', 'AnnotationProperty') : Property, #XXX AnnotationProperty,
               getUriref('owl', 'DataRange') : DataRange,
               getUriref('owl', 'DatatypeProperty') : DatatypeProperty,
##               getUriref('owl', 'DeprecatedClass') : DeprecatedClass,
##               getUriref('owl', 'DeprecatedProperty') : DeprecatedProperty,
               getUriref('owl', 'FunctionalProperty') : FunctionalProperty,
               getUriref('owl', 'InverseFunctionalProperty') : InverseFunctionalProperty,
               getUriref('owl', 'Nothing') : Nothing,
##               getUriref('owl', 'Ontology') : Ontology,
##               getUriref('owl', 'OntologyProperty') : OntologyProperty,
               getUriref('owl', 'Restriction') : Restriction,
               getUriref('owl', 'SymmetricProperty') : SymmetricProperty,
               getUriref('owl', 'TransitiveProperty') : TransitiveProperty,
               getUriref('rdf', 'List') : List
              }
  
class Ontology:

    def __init__(self, store = 'default'):
        self.graph = Graph(store)
        if store != 'default':
            self.graph.open(py.path.local().join("db").strpath)
        self.variables = {}
        self.constraints = []
        self.seen = {}
        self.var2ns ={}

    def add(self, triple):
        self.graph.add(triple)
        
    def add_file(self, f, format=None):
        if not format:
            format = check_format(f)
        self.graph.load(f, format=format)

    def attach_fd(self):
        for (s, p, o) in (self.graph.triples((None,)*3)):
            if p.find('#') != -1:
                ns, func = p.split('#')
            else:
                ns =''
                func = p
            if ns in namespaces.values():
                #predicate is one of builtin OWL or rdf predicates
                pred = getattr(self, func)
                res = pred(s, o) 
                if not res :
                    continue
                if type(res) != list :
                    res = [res]
                avar = self.make_var(ClassDomain, s) 
            else:
                avar = self.make_var(Property, p)
                # Set the values of the property p to o
                sub = self.make_var(ClassDomain, s) 
                obj = self.make_var(Thing, o) 
                propdom = self.variables[avar]
                res = propdom.addValue(sub, obj) 

    def solve(self,verbose=0):
        rep = Repository(self.variables.keys(), self.variables, self.constraints)
        return Solver().solve(rep, verbose)

    def consistency(self, verbose=0):
        self.rep = Repository(self.variables.keys(), self.variables, self.constraints)
        self.rep.consistency(verbose)

    def flatten_rdf_list(self, rdf_list):
        res = []
        if not type(rdf_list) == list:
            avar = self.make_var(List, rdf_list)
            lis = list(self.graph.objects(rdf_list, rdf_first))
            if not lis:
                return res
            res.append(lis[0])
            lis = list(self.graph.objects(rdf_list, rdf_rest))[0]
            while lis != rdf_nil:
                res.append(list(self.graph.objects(lis, rdf_first))[0])
                lis = list(self.graph.objects(lis, rdf_rest))[0]
        else:
            # For testing 
            avar = self.make_var(List, BNode('anon_%r'%rdf_list))
            if type(rdf_list[0]) ==  list:
                res = [tuple(x) for x in rdf_list]
            else:
                res = rdf_list
        self.variables[avar].setValues(res)
        return avar
            
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
        if not var in self.variables:
            self.variables[var] = cls(var)
        elif type(self.variables[var]) in cls.__bases__:
            vals = self.variables[var].getValues()
            self.variables[var] = cls(var)
            self.variables[var].setValues(vals)
        return var 

#---------------- Implementation ----------------

    def comment(self, s, var):
        pass
        
    def type(self, s, var):
        if not var in builtin_voc :
            # var is not one of the builtin classes
            avar = self.make_var(ClassDomain, var)
            svar = self.make_var(self.variables[avar].__class__, s)
            constrain = TypeConstraint(svar,  avar)
            self.constraints.append(constrain)
        else:
            # var is a builtin class
            cls =builtin_voc[var]
            if cls == List:
                return
            else:
                svar = self.make_var(None, s)
            if not (self.variables.has_key(svar) and 
                   isinstance(self.variables[svar], cls)):
                svar = self.make_var(cls, s)
            cls = self.variables[svar]
            if hasattr(cls, 'constraint'):
                self.constraints.append(cls.constraint)

    def first(self, s, var):
        pass

    def rest(self, s, var):
        pass
    
    def onProperty(self, s, var):
        svar =self.make_var(Restriction, s)
        avar =self.make_var(Property, var)
        self.variables[svar].property = avar
        

#---Class Axioms---#000000#FFFFFF-----------------------------------------------

    def subClassOf(self, s, var):
        # s is a subclass of var means that the 
        # class extension of s is a subset of the
        # class extension of var, ie if a indiviual is in 
        # the extension of s it must be in the extension of
        # var
        avar = self.make_var(None, var)
        svar = self.make_var(ClassDomain, s)
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
        var = self.flatten_rdf_list(var)
        #avar = self.make_var(List, var)
        svar = self.make_var(ClassDomain, s)
        res = self.variables[var].getValues()
        self.variables[svar].setValues(res)

    def unionOf(self,s, var):
        var = self.flatten_rdf_list(var)
        vals = self.variables[var].getValues()

        res = []
        for val in vals:
             res.extend([x for x in val])
        svar = self.make_var(ClassDomain, s)
        vals = self.variables[svar].getValues()
        res.extend(vals)
        self.variables[svar].setValues(res)

    def intersectionOf(self, s, var):
        var = self.flatten_rdf_list(var)
        vals = self.variables[var].getValues()
        res = vals[0]
        for l in vals[1:]:
            result = []
            for v in res:
                if v in l :
                    result.append(v)
            res = result
        svar = self.make_var(ClassDomain, s)
        self.variables[svar].setValues(res)

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
        svar =self.make_var(Restriction, s)
        constrain = MaxCardinality(svar, int(var))
        self.constraints.append(constrain) 
        # Make a new variable that can hold the domain of possible cardinality
        # values
        self.variables[svar].TBox['Cardinality'] = (range( int(var)+1), 'in')
#        var_name = '%s_Cardinality' % svar
#        self.variables[var_name] = fd(range(int(var)+1))
	          
    def minCardinality(self, s, var):
        """ Len of finite domain of the property shall be greater than or equal to var"""
        svar =self.make_var(Restriction, s)
        constrain = MinCardinality(svar, int(var))
        self.constraints.append(constrain) 
        self.variables[svar].TBox['Cardinality'] = ( range(int(var)), 'not in')
#        var_name = '%s_Cardinality' % svar
#        self.variables[var_name] = fd(range(int(var)))
#        constraint = Expression(var_name,' not in')
#        self.constraints.append(constraint)

    def cardinality(self, s, var):
        """ Len of finite domain of the property shall be equal to var"""
        svar =self.make_var(Restriction, s)
        # Check if var is an int, else find the int buried in the structure
        constrain = Cardinality(svar, int(var))
        self.constraints.append(constrain) 
        self.variables[svar].TBox['Cardinality'] = ( [int(var)], 'in')
#        var_name = '%s_Cardinality' % svar
#        self.variables['var_name'] = fd(int(var))        

    def differentFrom(self, s, var):
        s_var = self.make_var(Thing, s)
        var_var = self.make_var(Thing, var)
        constrain = DifferentfromConstraint(s_var, var_var)
        self.constraints.append(constrain)

#XXX need to change this
    def distinctMembers(self, s, var):
        s_var = self.make_var(AllDifferent, s)
        var_var = self.flatten_rdf_list(var)
        #var_var = self.make_var(List, var)
        for v in var_var:
           indx = var_var.index(v) 
           for other in var_var[indx+1:]:
               self.differentFrom(v, other)
        constrain = AllDifferentConstraint(s_var, var_var)
        self.constraints.append(constrain)

    def sameAs(self, s, var):
        s_var = self.make_var(None, s)
        var_var = self.make_var(None, var)
        constrain = SameasConstraint(s_var, var_var)
        self.constraints.append(constrain)

    def hasValue(self, s, var):
        svar = self.make_var(Restriction, s)
        avar = self.make_var(None, var)
        constrain = HasvalueConstraint(svar, avar)
        self.constraints.append(constrain)
        
    def allValuesFrom(self, s, var):
        svar = self.make_var(Restriction, s)
        avar = self.make_var(None, var)
        constrain = AllValueConstraint(svar, avar)
        self.constraints.append(constrain)

    def someValuesFrom(self, s, var):
        svar = self.make_var(Restriction, s)
        avar = self.make_var(None, var)
        constrain = SomeValueConstraint(svar, avar)
        self.constraints.append(constrain)

    def imports(self, s, var):
        # PP TODO: implement this 
        pass

# ----------------- Helper classes ----------------

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
        for val in subdom.getValues():
            if not val in vals:
                vals.append(val)
        superdom.setValues(vals)

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
    cost = 200
    
    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        obj_domain = domains[self.object].getValues()
        sub_domain = domains[self.variable].getValues()
        res = []
        for cls, val in obj_domain:
            if not (val,cls) in sub_domain:
                raise ConsistencyFailure("Inverseof failed for (%r, %r) in %r" % 
                                         (val, cls, sub_domain) )
        for cls, val in sub_domain:
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
                if isinstance(dom, Property):
                    val = Linkeddict(vals)
                    if self.variable in val.keys() and not self.object in val.keys():
                        vals +=[(self.object,v) for v in val[self.variable]]
                        dom.setValues(vals)
                    elif not self.variable in val.keys() and self.object in val.keys():
                        vals +=[(self.variable,v) for v in val[self.object]]
                        dom.setValues(vals)
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

