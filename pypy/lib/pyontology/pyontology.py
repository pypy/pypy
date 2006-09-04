from rdflib import Graph, URIRef, BNode, Literal
from logilab.constraint import  Repository, Solver
from logilab.constraint.fd import  Expression, FiniteDomain as fd
from logilab.constraint.propagation import AbstractDomain, AbstractConstraint,\
       ConsistencyFailure
from constraint_classes import *
import sys, py
import datetime, time
from urllib2 import URLError
log = py.log.Producer("Pyontology")
from pypy.tool.ansi_print import ansi_log
py.log.setconsumer("Pyontology", None)
#py.log.setconsumer("Pyontology.exception", ansi_log)

namespaces = {
    'rdf' : 'http://www.w3.org/1999/02/22-rdf-syntax-ns',
    'rdfs' : 'http://www.w3.org/2000/01/rdf-schema',
    'xmlns' : 'http://www.w3.org/1999/xhtml',
    'xmlschema' : 'http://www.w3.org/2001/XMLSchema', 
    'owl' : 'http://www.w3.org/2002/07/owl',
}

uris = {}
for k,v in namespaces.items():
    uris[v] = k

Class = URIRef(u'http://www.w3.org/2002/07/owl#Class')
Thing_uri = URIRef(u'http://www.w3.org/2002/07/owl#Thing')
Nothing_uri = URIRef(u'http://www.w3.org/2002/07/owl#Nothing')
rdf_type = URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
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

class ClassDomain(AbstractDomain, object):
    
    # Class domain is intended as a (abstract/virtual) domain for implementing
    # Class axioms. Working on class descriptions the class domain should allow
    # creation of classes through axioms.
    # The instances of a class can be represented as a FiniteDomain in values (not always see Disjointwith)
    # Properties of a class is in the dictionary "properties"
    # The bases of a class is in the list "bases"

    fixed = False
 
    def __init__(self, name='', uri=None, values = [], bases = []):
        AbstractDomain.__init__(self)
        self.name = name
        self.uri = uri
        self.values = {}
        self.setValues(values)
        self.property = None
        self.constraint = []
        self.un_constraint = []
        self.in_constraint = []
        self.domains = {}
        self.bases = [] 
        self.finished = False
        self.value = None
        self.type = []

    def finish(self, variables, glob_constraints):
        # The finish method constructs the constraints
        if not self.finished:
            log.finish("%s" % self.name)
        # Try to initialise constraints for this class
            if len(self.type) > 1:
                #try to merge the domains of the types 
                expr = []
                for typ in self.type:
                    expr +=[ "%s == %s" % (self.name, typ)]
                expr = ' and '.join(expr)
                self.in_constraint.append(Expression([self.name]+self.type, expr))
            prop = getattr(self, 'property')
            val = getattr(self, 'value')
            if prop:
                prop = variables[prop]
            for constraint in self.un_constraint:
                dom, constraints = constraint(self.name, prop, val)
                if dom:
                    self.domains.update(dom)
                    self.in_constraint.extend(constraints)
        # Initialise constraints from the base classes
            self.finished = True
            for cls in self.bases:
                cls = variables[cls]
                dom,constraint = cls.finish(variables, glob_constraints)

                # if the base class is a Restriction we shouldnt add the constraints to the store
                if not isinstance(cls, Restriction):
                    self.domains.update(dom)
                    self.constraint.extend(constraint)
                # initialise the constraint with this class as the first argument
                for constraint in cls.un_constraint:
                    dom, constraints = constraint(self.name, variables[cls.property], cls.value)
                    self.domains.update(dom)
                    self.in_constraint.extend(constraints)
            # update the store
            if prop:
                variables[self.name].setValues([v[0] for v in prop.getValues()])
            elif ('owl_Thing' in variables.keys() and isinstance(self, ClassDomain)
                 and  self.size() == 0):
                variables[self.name].setValues(list(variables['owl_Thing'].getValues()))
#                log.finish("setting the domain %s to all individuals %r"%(self.name,variables[self.name]))
            variables.update(self.domains)
            glob_constraints.extend(self.in_constraint)
            assert len([x for x in glob_constraints if type(x)==list])==0
        return self.domains, self.un_constraint
            
    def __repr__(self):
        return "<%s %s>" % (self.__class__, str(self.name))

    def __contains__(self,  item): 
        return item in self.values

    def copy(self):
        return self
    
    def size(self):
        return len(self.values)
    
    def removeValues(self, values):
        for val in values:
            self.removeValue(val)

    def removeValue(self, value):
        log.removeValue("Removing %r of %r" % (value ,self.values))
        if value in self.values:
            self.values.pop(value)
        if not self.values:
            log.removeValue("Removed the lastvalue of the Domain")
            raise ConsistencyFailure("Removed the lastvalue of the Domain")
 
    def getBases(self):
        return self._bases

    def setBases(self, bases):
        log(">>>>>>>>>>>>>>>>>>>>>>>  %r" %self.name)
        assert self.name != 'owl_Class'
        self._bases = bases
    
    def addValue(self, value):
#        assert isinstance(value, URIRef)
        self.values[value] = True

    def getValues(self):
        for key in self.values:
            yield key
        
    def __iter__(self):
        return iter(self.values.keys())
        
    def setValues(self, values):
        for val in values:
            self.addValue(val) 

class FixedClassDomain(ClassDomain):

    finished = True 
    fixed = True
 
    def removeValues(self, values):
        raise ConsistencyFailure("Cannot remove values from a FixedClassDomain")

    def removeValue(self, value):
        raise ConsistencyFailure("Cannot remove values from a FixedClassDomain")

    def setValues(self, values):
        if not self.values:
            self.values = dict.fromkeys(values)
        #else:
            #raise ConsistencyFailure

class Thing(ClassDomain):
    pass

class Individual(Thing):
    def __init__(self, name, uri=None, values=[], bases=[]):
        Thing.__init__(self, name, uri, values, bases) 
        self.name = name
        self.uri = uri
        self.sameas = set() 
        self.differentfrom = set()
    
    def __repr__(self):
        return "<%s( %s, %s)>"%(self.__class__.__name__, self.name, self.uri)

    def __hash__(self):
        return hash(self.uri)
 
    def __eq__(self, other):
        log("CMP %r,%r %i"%(self.name,other, len(self.differentfrom)))
        if ((hasattr(other,'uri') and self.uri == other.uri) or
            (not hasattr(other,'uri') and self.uri == other) or
              other in self.sameas):
            return True
        if other in self.differentfrom:
            return False
        else:
            return None
           
    cmp = __eq__
 
class List(ClassDomain):
    
    def __init__(self, name='', values=[], bases = []):
        ClassDomain.__init__(self, name, values, bases)

class Property(Individual): #ClassDomain):
    # Property contains the relationship between a class instance and a value
    # - a pair. To accomodate global assertions like 'range' and 'domain' attributes
    # for range and domain must be filled in by rdfs:range and rdfs:domain
    
    def __init__(self, name='', uri='', values=[], bases = []):
        Individual.__init__(self, name, uri, values, bases)
        self.name = name
        self._dict = {}
        self.property = None
        self.constraint = []
        self.un_constraint = []
        self.in_constraint = []
        self.bases = []
        self.finished = True

    def finish(self, var, constraints):
        return var, constraints
    
    def size(self):
        return len(self._dict)
            
    def getValues(self):
        items = self._dict.items()
        res = []
        for k,vals in items:
            for v in vals:
                yield (k,v)

    def getValuesPrKey(self, key= None):
        if key:
            return self._dict.get(key,[])
        return self._dict.items()
    
    def addValue(self, key, val):
        if key == None:
            raise RuntimeError
        self._dict.setdefault(key, [])
        self._dict[key].append(val)
    
    def setValues(self, values):
        for key, val in values:
            self.addValue(key, val)
    
    def removeValues(self, values):
        for k,v in values:
            vals = self._dict[k]
            if vals == [None]:
                self._dict.pop(k)
            else:
                self._dict[k] = [ x for x in vals if x != v]

    def __contains__(self, (cls, val)):
        if not cls in self._dict:
            return False
        vals = self._dict[cls]
        if val in vals:
            return True
        return False

class ObjectProperty(Property):
    
    pass

class DatatypeProperty(Property):
    pass

class DataRange(ClassDomain):
    pass

class AllDifferent(ClassDomain):
    # A special class whose members are distinct
    # Syntactic sugar
    pass

class Nothing(ClassDomain):

    def __init__(self, name='', values=[], bases = []):
        ClassDomain.__init__(self, name, values, bases)
        self.constraint = [NothingConstraint(name)]
    
class FunctionalProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = [FunctionalCardinality(name)]

class InverseFunctionalProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = [InverseFunctionalCardinality(name)]

    def addValue(self, key, val):
        Property.addValue(self, key, val)
        valuelist = [set(x) for x in self._dict.values()]
        res = set()
        for vals in valuelist:
            if vals & res:
                raise ConsistencyFailure("Only unique values in InverseFunctionalProperties")
            res = res | vals

class TransitiveProperty(Property):
   
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        #self.constraint = TransitiveConstraint(name)

    def addValue(self, key, val):
        Property.addValue(self, key, val)
        if val in self._dict.keys():
            for v in self._dict[val]:
                Property.addValue(self, key, v)
        for k in self._dict.keys():
            if key in self._dict[k]:
                Property.addValue(self, k, val)
                
class SymmetricProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
#        self.constraint = SymmetricConstraint(name)

    def addValue(self, key, val):
        Property.addValue(self, key, val)
        Property.addValue(self, val, key)

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
        self.property = None

def Types(typ):
    class Type(ClassDomain):
 
        def __contains__(self, item):
            #assert isinstance(item, Literal)
            return item.datatype is None or item.datatype == self.Type

    datatype = Type
    datatype.Type = typ
    return datatype

builtin_voc = {
               getUriref('owl', 'Thing') : Thing,
               getUriref('owl', 'Class') : ClassDomain,
               getUriref('rdf', 'Property') : Property,               
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
               getUriref('rdf', 'List') : List,
              }

XMLTypes = ['string', 'float', 'integer', 'date']

for typ in XMLTypes:
    uri = getUriref('xmlschema', typ)
    builtin_voc[uri] = Types(uri)

class Ontology:
    
    def __init__(self, store = 'default'):
        self.graph = Graph(store)
        self.store = store
        if store != 'default':
            self.graph.open(py.path.local().join("db").strpath)
            self.store_path = py.path.local().join("db").strpath
        self.variables = {}
        self.constraints = []
        self.seen = {}
        self.var2ns ={}
        self.nr_of_triples = 0
        self.time = time.time()
    
    def add(self, triple):
        self.graph.add(triple)

    def add_file(self, f, format=None):
        tmp = Graph('default')
        if not format:
            format = check_format(f)
        tmp.load(f, format=format)
        for triple in tmp.triples((None,)*3):
            self.add(triple)
            
    def load_file(self, f, format=None):
        if not format:
            format = check_format(f)
        self.graph.load(f, format=format)
    
    def attach_fd(self):
        for (s, p, o) in (self.graph.triples((None,)*3)):
            self.consider_triple((s, p, o))
        log("=============================")

    def finish(self):
        for constraint in self.constraints:
            log.exception("Trying %r" %constraint)
            for key in constraint.affectedVariables():
                log.exception("FINISHING %s" % key)
                if isinstance( self.variables[key], fd):
                    continue
                self.variables[key].finish(self.variables, self.constraints)
            constraint.narrow(self.variables)
    
    def consider_triple(self,(s, p, o)):
        if (s, p, o) in self.seen:
            return
        self.nr_of_triples += 1
        log("Doing triple nr %i: %r" % (self.nr_of_triples,(s, p, o)))
        tim = time.time()
        log.considerTriple("Triples per second %f" %(1./(tim-self.time)))
        self.time = tim
        self.seen[(s, p, o)] = True
        if p.find('#') != -1:
            ns, func = p.split('#')
        else:
            ns =''
            func = p
        if ns in namespaces.values() and hasattr(self, func):
            #predicate is one of builtin OWL or rdf predicates
            pred = getattr(self, func)
            res = pred(s, o)
            avar = self.make_var(ClassDomain, s)
        else:
            avar = self.make_var(Property, p)
            # Set the values of the property p to o
            self.type(s, Thing_uri)
            sub = self.make_var(Thing, s)
            if type(o) == URIRef:
                obj = self.make_var(Thing, o)
                val = Individual(obj,o)
            else:
                val = o
            propdom = self.variables[avar]
            res = propdom.addValue(Individual(sub,s), val)

    def resolve_item(self, item):
        item_as_subject = self.graph.triples((item, None, None))
        for triple in item_as_subject:
            self.consider_triple(triple)

    def resolve_predicate(self, item):
        item_as_predicate = self.graph.triples(( None, item, None))
        for triple in item_as_predicate:
            self.consider_triple(triple)

    def get_individuals_of(self, item):
        item_as_object = self.graph.triples(( None, rdf_type, item))
        for triple in item_as_object:
            self.consider_triple(triple)

    def make_var(self, cls=fd, a=''):
        log("make_var %r,%r" %(cls,a))
        if a in builtin_voc:
            cls = builtin_voc[a]
        if type(a) == URIRef:
            if a.find('#') != -1:
                ns,name = a.split('#')
            else:
                ns,name = a,''
            if ns not in uris.keys():
                uris[ns] = ns.split('/')[-1]
            var = uris[ns] + '_' + name
            var = str(var.replace('.','_'))
            var = str(var.replace('-','_'))
        elif type(a) == BNode:
            var = str(a)
        else:
            return a
        if not cls:
            return var
        if not var in self.variables:
            cls = self.variables[var] = cls(var, a)
            if cls.constraint:
                log("make_var constraint 1 %r,%r" %(cls,a))
                self.constraints.extend(cls.constraint)
        # XXX needed because of old style classes
        elif not cls == self.variables[var].__class__ and issubclass(cls, self.variables[var].__class__):
            vals = self.variables[var].getValues()
            tmp = cls(var, a)
            tmp.setValues(list(vals))
            tmp.property = self.variables[var].property
            if tmp.constraint:
                log("make_var constraint 2 %r,%r" %(cls,a))
                self.constraints.extend(tmp.constraint)
            self.variables[var] = tmp
        return var

    def solve(self,verbose=0):
        rep = Repository(self.variables.keys(), self.variables, self.constraints)
        return Solver().solve(rep, verbose)
    
    def consistency(self, verbose=0):
        log("BEFORE FINISH %r" % self.variables)
        self.finish()
        self.rep = Repository(self.variables.keys(), self.variables, self.constraints)
        self.rep.consistency(verbose)
    
    def flatten_rdf_list(self, rdf_list):
        res = []
        if not type(rdf_list) == list:
            avar = self.make_var(List, rdf_list)
            lis = list(self.graph.objects(rdf_list, rdf_first))
            if not lis:
                return avar
            res.append(lis[0])
            lis = list(self.graph.objects(rdf_list, rdf_rest))[0]
            while lis != rdf_nil:
                res.append(list(self.graph.objects(lis, rdf_first))[0])
                lis = list(self.graph.objects(lis, rdf_rest))[0]
            self.variables[avar].setValues(res)
        else:
            # For testing
            avar = self.make_var(List, BNode('anon_%r'%rdf_list))
            if type(rdf_list[0]) ==  list:
                res = [tuple(x) for x in rdf_list]
            else:
                res = rdf_list
        self.variables[avar].setValues(res)
        return avar
    
#---------------- Implementation ----------------
    
    def comment(self, s, var):
        pass
    
    def label(self, s, var):
        pass

    def type(self, s, var):
        log("type %r %r"%(s, var))
        avar = self.make_var(ClassDomain, var)
        if not var in builtin_voc :
            # var is not one of the builtin classes -> it is a Thing
            self.type(s, Thing_uri)
            svar = self.make_var(Individual, s)
            self.variables[svar].type.append(avar) 
            self.constraints.append(MemberConstraint(svar, avar))
        else:
            # var is a builtin class
            cls = builtin_voc[var]
            if cls == List:
                return
            svar = self.make_var(cls, s)
            cls = self.variables[svar]
            if cls.constraint:
                self.constraints.extend(cls.constraint)
            if not isinstance(self.variables[avar], Property):
                if isinstance(self.variables[avar], Thing):
                    self.variables[avar].addValue(Individual(svar, s))
                else:
                    self.variables[avar].addValue(svar)
    
    def first(self, s, var):
        pass
    
    def rest(self, s, var):
        pass
    
    def onProperty(self, s, var):
        log("%r onProperty %r "%(s, var))
        svar =self.make_var(Restriction, s)
        avar =self.make_var(Property, var)
        restr = self.variables[svar]
        restr.property = avar

#---Class Axioms---#000000#FFFFFF-----------------------------------------------
    
    def subClassOf(self, s, var):
        # s is a subclass of var means that the
        # class extension of s is a subset of the
        # class extension of var, ie if a indiviual is in
        # the extension of s it must be in the extension of
        # var
        
        # what I really  want is to just say s.bases.append(var)
        
        log("%r subClassOf %r "%(s, var))
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(ClassDomain, s)
        self.variables[svar].bases.append(avar)
        self.variables[svar].bases.extend(self.variables[avar].bases)

    def equivalentClass(self, s, var):
        self.subClassOf(s, var)
        self.subClassOf(var, s)
    
    def disjointWith(self, s, var):
        self.resolve_item(s)
        self.resolve_item(var)
        avar = self.make_var(None, var)
        svar = self.make_var(None, s)
        constrain = DisjointClassConstraint(svar, avar)
        self.constraints.append(constrain)
    
    def complementOf(self, s, var):
        # add constraint of not var
        # i.e. the extension of s shall contain all individuals not in var
        # We need to know all elements and subtract the elements of var
        self.resolve_item(s)
        self.resolve_item(var)
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(ClassDomain, s)
        self.constraints.append(ComplementOfConstraint(svar, avar))       
    
    def oneOf(self, s, var):
        # Oneof is used to generate a fixed class. The elements of the class
        # are exactly the ones in the list.
        # Can be used to define an enumerated datatype as well.
        # The memebers of the list can be Urirefs (Individuals) or Literals
        var = self.flatten_rdf_list(var)
        svar = self.make_var(FixedClassDomain, s)
        res = list(self.variables[var].getValues())
        if type(res[0]) == URIRef:
            self.variables[svar].setValues([
                Individual(self.make_var(Thing, x), x) for x in res])
            for i in res:
                self.type(i, Thing_uri)
        else: 
            self.variables[svar].setValues(res)

    def unionOf(self,s, var):
        var = self.flatten_rdf_list(var)
        
        res = []
        for val in self.variables[var].getValues():
            self.get_individuals_of(val)
            var_name = self.make_var(ClassDomain, val)
            val = self.variables[var_name].getValues()
            res.extend([x for x in val])
        svar = self.make_var(ClassDomain, s)
        vals = list(self.variables[svar].getValues())
        res.extend(vals)
        self.variables[svar].setValues(res)
    
    def intersectionOf(self, s, var):
        var_list = self.flatten_rdf_list(var)
        vals = [self.make_var(ClassDomain, x) for x in self.variables[var_list].getValues()]
        
        res = vals[0]
        for l in vals[1:]:
            result = []
            for v in res:
                if v in self.variables[l].getValues() :
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
        self.resolve_predicate(var)
        self.resolve_predicate(s)
        avar = self.make_var(Property, var)
        svar = self.make_var(Property, s)
        avals = self.variables[avar]
        for pair in self.variables[svar].getValues():
            if not pair in avals:
                self.variables[avar].addValue(pair[0], pair[1])

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
        
    def cardinality_helper(self, s, var, card):
        
        log("%r %sCardinality %r "%(s, card, var))
        svar =self.make_var(Restriction, s)
        scls = self.variables[svar]
        scls.un_constraint.append(card)
        scls.value = var

    def maxCardinality(self, s, var):
        """ Len of finite domain of the property shall be less than or equal to var"""
        def maxCard(cls , prop, val):
            dom = {"%s_%s_card" %(cls, prop.name) : fd(range(val+1))}
            return dom,[CardinalityConstraint( prop.name, cls, val, '<')]
        self.cardinality_helper(s, int(var), maxCard)
        
    def minCardinality(self, s, var):
        """ Len of finite domain of the property shall be greater than or equal to var"""
        def minCard(cls , prop, val):
            var = "%s_%s_card" %(cls, prop.name)
            con = Expression([var], "%s >= %i" % (var, val))
            return {},[con, CardinalityConstraint(prop.name, cls, val , '>')]
        self.cardinality_helper(s, int(var), minCard)
    
    def cardinality(self, s, var):
        """ Len of finite domain of the property shall be equal to var"""
        def Card(cls , prop, val):
            dom = {"%s_%s_card" %(cls, prop.name) : fd([val])}
            return dom,[CardinalityConstraint( prop.name, cls, val, '=')]
        self.cardinality_helper(s, int(var), Card)

    def value_helper(self, s, var, constraint):
        svar = self.make_var(Restriction, s)
        avar = self.make_var(None, var)
        scls = self.variables[svar]
        scls.un_constraint.append(constraint)
        scls.value = avar

    def hasValue(self, s, var):
        """ The hasValue restriction defines a class having as an extension all
            Individuals that have a property with the value of var.
            To make an assertion we need to know for which class the restriction applies"""
        sub = self.make_var(Restriction, s)
        cons = HasvalueConstraint(sub, var)
        self.constraints.append(cons)

    def allValuesFrom(self, s, var):
        sub = self.make_var(Restriction, s)
        obj = self.make_var(ClassDomain, var)
        cons = AllValueConstraint(sub, obj)
        self.constraints.append(cons)

    def someValuesFrom(self, s, var):
        sub = self.make_var(Restriction, s)
        obj = self.make_var(ClassDomain, var)
        cons = SomeValueConstraint(sub, obj)
        self.constraints.append(cons)
        
# -----------------              ----------------
    
    def imports(self, s, var):
        # Get the url
        url = var
        # add the triples to the graph
        tmp = Graph()
        try:
           tmp.load(url)
           for trip in tmp.triples((None,)*3):
               self.add(trip)
        except URLError:
           pass

    def sameAs(self, s, var):
        s_var = self.make_var(Thing, s)
        var_var = self.make_var(Thing, var)
        constrain = SameasConstraint(s_var, var_var)
        self.constraints.append(constrain)

    def differentFrom(self, s, var):
        s_var = self.make_var(Thing, s)
        var_var = self.make_var(Thing, var)
        constrain = DifferentfromConstraint(s_var, var_var)
        self.constraints.append(constrain)

    def distinctMembers(self, s, var):
        s_var = self.make_var(AllDifferent, s)
        var_var = self.flatten_rdf_list(var)
        diff_list = self.variables[var_var].getValues()
        for v in diff_list:
           indx = diff_list.index(v)
           for other in diff_list[indx+1:]:
               self.differentFrom(v, other)
