from rdflib import Graph, URIRef, BNode, Literal
from logilab.constraint import  Repository, Solver
from logilab.constraint.fd import  Expression, FiniteDomain as fd
from logilab.constraint.propagation import AbstractDomain, AbstractConstraint, ConsistencyFailure
from constraint_classes import *
import sys, py
import time
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("Pyontology")
py.log.setconsumer("Pyontology", ansi_log)


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

class ClassDomain(fd, object):
    
    # Class domain is intended as a (abstract/virtual) domain for implementing
    # Class axioms. Working on class descriptions the class domain should allow
    # creation of classes through axioms.
    # The instances of a class can be represented as a FiniteDomain in values (not always see Disjointwith)
    # Properties of a class is in the dictionary "properties"
    # The bases of a class is in the list "bases"
    
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

    def finish(self, variables, glob_constraints):
        # The finish method constructs the constraints
        if not self.finished:
            log("FINISH %s" % self.name)
        # Try to initialise constraints for this class
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
            for cls in self.bases:
                cls = variables[cls]
                dom,constraint = cls.finish(variables, glob_constraints)

                log("DOM %r "%dom)
                # if the base class is a Restriction we shouldnt add the constraints to the store
                if not isinstance(cls, Restriction):
                    self.domains.update(dom)
                    self.constraint.extend(constraint)
                # initialise the constraint with this class as the first argument
                for constraint in cls.un_constraint:
                    dom, constraints = constraint(self.name, variables[cls.property], cls.value)
                    self.domains.update(dom)
                    log("Updating constraints %r" % constraints)
                    self.in_constraint.extend(constraints)
            self.finished = True
            log("RESULT of finish %r, %r" %(self.domains,self.in_constraint))
            # update the store
            if ('owl_Thing' in variables.keys() and isinstance(self, ClassDomain)
                 and  self.getValues() == []):
                variables[self.name].setValues(variables['owl_Thing'].getValues())
            variables.update(self.domains)
            glob_constraints.extend(self.in_constraint)
            assert len([x for x in glob_constraints if type(x)==list])==0
        return self.domains, self.un_constraint
            
    def __repr__(self):
        return "<%s %s %r>" % (self.__class__, str(self.name), self.getValues())
    
    def copy(self):
        return self
    
    def size(self):
        return len(self.getValues())
    
    def removeValues(self, values):
        for val in values:
            self.values.pop(val) 
    
    def getBases(self):
        return self._bases

    def setBases(self, bases):
        log(">>>>>>>>>>>>>>>>>>>>>>>  %r" %self.name)
        assert self.name != 'owl_Class'
        self._bases = bases
    
    def addValue(self, value):
        self.values[value] = True

    def getValues(self):
        return self.values.keys()
        
    def __iter__(self):
        return iter(self.values.keys())
        
    def setValues(self, values):
        self.values = dict.fromkeys(values)

class Thing(ClassDomain):
    pass

class Individual:
    def __init__(self, name, uri=None, values=[], bases=[]):
        self.name = name
        self.uri = uri
        self.sameas = [] 
        self.differentfrom = []
       
    def __hash__(self):
        return hash(self.uri) 
    def __eq__(self, other):
        log("CMP %r,%r"%(self,other))
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

class Property(fd):
    # Property contains the relationship between a class instance and a value
    # - a pair. To accomodate global assertions like 'range' and 'domain' attributes
    # for range and domain must be filled in by rdfs:range and rdfs:domain
    
    def __init__(self, name='', values=[], bases = []):
        AbstractDomain.__init__(self)
        self.name = name
        self._dict = {}
        self.range = []
        self.domain = []
        self.property = None
        self.constraint = []
        self.un_constraint = []
        self.in_constraint = []
        self.bases = []
    
    def finish(self, var, constraints):
        return var, constraints
    
    def size(self):
        return len(self.getValues())
            
    def getValues(self):
        items = self._dict.items()
        res = []
        for k,vals in items:
            for v in vals:
                res.append((k,v))
        return res

    def getValuesPrKey(self, key= None):
        if key:
            return self._dict.get(key,[])
        return self._dict.items()
    
    def addValue(self, key, val):
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
        if not cls in self._dict.keys():
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

    def addValue(self, key, val):
        Property.addValue(self, key, val)
#        if len(self._dict[key]) > 1:
#            raise ConsistencyFailure("FunctionalProperties can only have one value")
        
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
               getUriref('rdf', 'List') : List
              }

class Ontology:
    
    def __init__(self, store = 'default'):
        self.graph = Graph(store)
        self.store = store
        if store != 'default':
            self.graph.open(py.path.local().join("db").strpath)
        self.variables = {}
        self.constraints = []
        self.seen = {}
        self.var2ns ={}
    
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
        #while len(list(self.graph.triples((None,)*3))) != len(self.seen.keys()):
        for (s, p, o) in (self.graph.triples((None,)*3)):
            self.consider_triple((s, p, o))
            log("%s %s" %(s,p))
        log("=============================")
        assert len(list(self.graph.triples((None,)*3))) == len(self.seen.keys())

    def finish(self):
        for key in list(self.variables.keys()):
            log("FINISHING %s,%r" % (key,self.variables[key].bases))
            self.variables[key].finish(self.variables, self.constraints)
    
    def consider_triple(self,(s, p, o)):
        log("Trying %r" % ((s, p, o),))
        if (s, p, o) in self.seen.keys():
            return
        log("Doing %r" % ((s, p, o),))
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
            obj = self.make_var(Thing, o)
            propdom = self.variables[avar]
            res = propdom.addValue(Individual(sub,s),Individual(obj,o))

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
            a = uris[ns] + '_' + name
            var = str(a.replace('.','_'))
            var = str(a.replace('-','_'))
        else:
            var = str(a)
        if not cls:
            return var
        if not var in self.variables:
            cls = self.variables[var] = cls(var)
            if cls.constraint:
                log("make_var constraint 1 %r,%r" %(cls,a))
                self.constraints.extend(cls.constraint)
        # XXX needed because of old style classes
        elif not cls == self.variables[var].__class__ and issubclass(cls, self.variables[var].__class__):
            vals = self.variables[var].getValues()
            tmp = cls(var)
            tmp.setValues(vals)
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
        log("DOMAINS %r"% self.variables)
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
            svar = self.make_var(None,s) 
            self.constraints.append(MemberConstraint(Individual(svar,s), avar))
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
                    self.variables[avar].addValue(s)
    
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
        var = self.flatten_rdf_list(var)
        svar = self.make_var(ClassDomain, s)
        res = self.variables[var].getValues()
        self.variables[svar].setValues([Individual(self.make_var(None,x),x) for x in res])
    
    def unionOf(self,s, var):
        var = self.flatten_rdf_list(var)
        vals = self.variables[var].getValues()
        
        res = []
        for val in vals:
            self.get_individuals_of(val)
            var_name = self.make_var(ClassDomain, val)
            val = self.variables[var_name].getValues()
            res.extend([x for x in val])
        svar = self.make_var(ClassDomain, s)
        vals = self.variables[svar].getValues()
        res.extend(vals)
        self.variables[svar].setValues(res)
    
    def intersectionOf(self, s, var):
        var = self.flatten_rdf_list(var)
        vals = [self.make_var(ClassDomain, x) for x in self.variables[var].getValues()]
        
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
        avals = self.variables[avar].getValues()
        for pair in self.variables[svar].getValues():
            if not pair in avals:
                self.variables[avar].addValue(pair[0], pair[1])

    def equivalentProperty(self, s, var):
        avar = self.make_var(Property, var)
        svar = self.make_var(Property, s)
        cons = EquivalentPropertyConstraint( svar, avar)
        self.constraints.append(cons)
    
    def inverseOf(self, s, var):
        self.resolve_predicate(s)
        self.resolve_predicate(var)
        avar = self.make_var(Property, var)
        svar = self.make_var(Property, s)
#        con = InverseofConstraint(svar, avar)
#        self.constraints.append(con)
        avals = self.variables[avar].getValues()
        svals = self.variables[svar].getValues()
        for pair in avals:
            if not (pair[1], pair[0]) in svals:
	            self.variables[svar].addValue(pair[1], pair[0])
        for pair in svals:
            if not (pair[1], pair[0]) in avals:
	            self.variables[avar].addValue(pair[1], pair[0])

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
        scls.value = var

    def hasValue(self, s, var):
        """ The hasValue restriction defines a class having as an extension all
            Individuals that have a property with the value of var.
            To make an assertion we need to know for which class the restriction applies"""
        def Hasvalue(cls ,prop, val):
            var = "%s_%s_hasvalue" %(cls, prop.name)
            dom = {var : fd(prop.getValues( ))}
            cons = Expression([cls, var], " %s[1].cmp(%s) and %s.cmp( %s[0])" %( var, val, cls, var))
            log("HASVALUE %r %r"%(prop.getValues(),dom))
            return dom, [cons] 
        
        self.value_helper(s, var, Hasvalue)

    def allValuesFrom(self, s, var):
        def allvalue(cls ,prop, val):
            # This creates a temporary domain to be able to help find the classes that only has values 
            # from val
            var = "%s_%s_allvalue" %(cls, prop.name)
            dom = {var : fd([(x,tuple(y)) for (x,y) in prop.getValuesPrKey( )])}
            # The condition should  return true if 
            cons = Expression([cls, var], "%s == %s[1] and %s == %s[0]" %(val, var, cls, var))
            return dom, [cons] 
        self.value_helper(s, var, allvalue)

    def someValuesFrom(self, s, var):
        #Maybe just add hasvalue 
        def somevalue(cls ,prop, val):
            # This creates a temporary domain to be able to help find the classes that only has values 
            # from val
            var = "%s_%s_allvalue" %(cls, prop.name)
            dom = {var : fd(prop.getValues( ))}
            # The condition should  return true if 
            cons = Expression([cls, var], " %s[1] in %s and %s == %s[0]" %(var, val, cls, var))
            return dom, [cons] 
        self.value_helper(s, var, somevalue)

# -----------------              ----------------
    
    def imports(self, s, var):
        # Get the url
        url = var
        # add the triples to the graph
        tmp = Graph()
        tmp.load(url)
        for trip in tmp.triples((None,)*3):
            self.add(trip)

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
