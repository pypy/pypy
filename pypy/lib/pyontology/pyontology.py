#import autopath
try:
    from cslib import Repository
    from cslib.fd import  FiniteDomain as fd
    print 'using pypy.lib.cslib'
except ImportError: 
    print 'using logilab.constraint'
    from logilab.constraint import  Repository
    from logilab.constraint.fd import  FiniteDomain as fd
from logilab.constraint.propagation import AbstractDomain, AbstractConstraint,\
     ConsistencyFailure
from sparql_grammar import SPARQLGrammar as SP # name clash ?
from constraint_classes import *
Solver = MySolver
Expression = MyExpression
import sys, py
import datetime, time
from urllib2 import URLError
log = py.log.Producer("Pyontology")
from pypy.tool.ansi_print import ansi_log
py.log.setconsumer("Pyontology", None)
#py.log.setconsumer("Pyontology", ansi_log)

from rdflib import Graph, URIRef, BNode, Literal as rdflib_literal


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
    elif hasattr(f, 'open'):
        tmp = f.open()
    else:
        tmp = f
    start = tmp.read(10)
    tmp.seek(0)
    if "<" in start:
        format = "xml"
    else:
        format = "n3"
    return format

""" In OWL there are Classes, Properties, Individuals and Literals.
    Properties creates relations between Classes, Classes and Individuals,
    Individuals and Individuals and Literals. There is an inheritance
    tree of Properties.
    We record instances of Properies in the class variable "prop_instance".

    Classes are defined as the set of Individuals belonging to the Class.
    We record these as the Values of the Classdomain.
    We record the instances of a Classtype in the Class variable "cls_inst".
    The class instances shall "bubble" up the inheritance tree.
"""

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
        self.setValues(values)
        
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
            variables.update(self.domains)
            glob_constraints.extend(self.in_constraint)
#            assert self.size() != 0
            assert len([x for x in glob_constraints if type(x)==list])==0
        return self.domains, self.un_constraint
            
    def __repr__(self):
        return "<%s %s>" % (self.__class__, str(self.name))

    def __contains__(self,  item): 
        return item in self.values

    def copy(self):
        return self.__class__(self.name, self.uri, self.getValues())
    
    def size(self):
        return len(self.values)
    
    def removeValues(self, values):
        for val in values:
            self.removeValue(val)

    def removeValue(self, value):
        if value in self.values:
            self.values.pop(value)
        if not self.values:
            raise ConsistencyFailure("Removed the lastvalue of the Domain %r" % self)
 
    def getBases(self):
        return self._bases

    def setBases(self, bases):
        assert self.name != 'owl_Class'
        self._bases = bases
    
    def addValue(self, value):
        self.values[value] = True

    def getValues(self):
        for key in self.values:
            yield key
        #return self.values.keys()
        
    def __iter__(self):
        return iter(self.values.keys())
        
    def setValues(self, values):
        for val in values:
            self.addValue(val) 

class FixedClassDomain(ClassDomain):

    finished = True 

    def __init__(self, name='', uri=None, values = [], bases = []):
        ClassDomain.__init__(self, name, uri, values, bases)
        self.fixed = True

    def addValue(self, value):
        if self.fixed :
            raise ValueError("Fixed classes can only add vulues during initialisation")
        else:
            ClassDomain.addValue(self, value)

#    def removeValues(self, values):
#        raise ConsistencyFailure("Cannot remove values from a FixedClassDomain")

#    def removeValue(self, value):
#        raise ConsistencyFailure("Cannot remove values from a FixedClassDomain")

#    def setValues(self, values):
#        if not self.values:
#            self.values = dict.fromkeys(values)
        #else:
            #raise ConsistencyFailure

class Thing(ClassDomain):
    uri = URIRef(namespaces['owl'] + "#Thing")
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
        #log("CMP %r,%r %i"%(self.name,other, len(self.differentfrom)))
        #assert isinstance(other, ClassDomain)
        if hasattr(other,'uri'):
            if self.uri == other.uri:
                return True
        elif other in self.sameas:
            return True
        else:
            if self.uri == other:
                return True
        if not other or other in self.differentfrom:
            return False
        else:
            return None
           
    cmp = __eq__
 
class List(ClassDomain):
    uri = URIRef(namespaces['rdf'] + "#List")
    
    def __init__(self, name='', values=[], bases = []):
        ClassDomain.__init__(self, name, values, bases)

class Property(AbstractDomain, object): 
    # Property contains the relationship between a class instance and a value
    # - a pair. To accomodate global assertions like 'range' and 'domain' attributes
    # for range and domain must be filled in by rdfs:range and rdfs:domain
    uri = URIRef(namespaces['rdf'] + "#Property")

    def __init__(self, name='', uri='', values=[], bases = []):
        super(Property, self).__init__()
        self.name = name
        self._dict = {}
        self.property = None
        self.constraint = []
        self.un_constraint = []
        self.in_constraint = []
        self.bases = []
        self.name_uri = uri
        self.finished = True
        self.setValues(values)

    def copy(self):
        return Property(self.name, self.uri, list(self.getValues()))

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
        self._dict.setdefault(key, [])
        self._dict[key].append(val)
    
    def setValues(self, values):
        self._dict= {}
        for key, val in values:
            self.addValue(key, val)
    
    def removeValues(self, values):
        for k,v in values:
            vals = self._dict[k]
            if vals == [None]:
                self._dict.pop(k)
            else:
                self._dict[k] = [ x for x in vals if x != v]
                if not self._dict[k]:
                    self._dict.pop(k)
        if not self._dict:
            raise ConsistencyFailure("Removed the last value of %s" % self.name)

    def __iter__(self):
        return iter(self.getValues())
        
    def __contains__(self, (cls, val)):
        if not cls in self._dict:
            return False
        vals = self._dict[cls]
        if val in vals:
            return True
        return False

class ObjectProperty(Property):
    uri = URIRef(namespaces['owl'] + "#ObjectProperty")
    
    pass

class DatatypeProperty(Property):
    uri = URIRef(namespaces['owl'] + "#DatatypeProperty")
    pass

class DataRange(ClassDomain):
    pass

class AllDifferent(ClassDomain):
    uri = URIRef(namespaces['owl'] + "#AllDifferent")
    # A special class whose members are distinct
    # Syntactic sugar
    pass

class Nothing(ClassDomain):
    uri = URIRef(namespaces['owl'] + "#Nothing")
    def __init__(self, name='', values=[], bases = []):
        ClassDomain.__init__(self, name, values, bases)
        self.constraint = [NothingConstraint(name)]
        self.finished = True
    
class FunctionalProperty(Property):
    uri = URIRef(namespaces['owl'] + "#FunctionalProperty")
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = [FunctionalCardinality(name)]

class InverseFunctionalProperty(ObjectProperty):
    uri = URIRef(namespaces['owl'] + "#InverseFunctionalProperty")
    
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

class TransitiveProperty(ObjectProperty):
    uri = URIRef(namespaces['owl'] + "#TransitiveProperty")
   
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
                
class SymmetricProperty(ObjectProperty):
    uri = URIRef(namespaces['owl'] + "#SymmetricProperty")
    
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
    uri = URIRef(namespaces['owl'] + "#Restriction")
    def __init__(self, name='', uri='', values=[], bases = []):
        ClassDomain.__init__(self, name, uri, values, bases)
        self.property = None

    def copy(self):
        cc = ClassDomain.copy(self)
        cc.property = self.property
        return cc

class Literal(ClassDomain):
    pass

def Types(typ):
    class Type(Literal):
        def __contains__(self, item):
            if isinstance(item, rdflib_literal):
                return item.datatype is None or item.datatype == self.Type
            else:
                return XMLTypes[self.Type.split("#")[-1]] == type(item)

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
               getUriref('rdf', 'Literal') : Literal,
#               getUriref('rdf', 'type') : Property,
              }
#XMLTypes = ['string', 'float', 'integer', 'date']
XMLTypes = {'string': str, 'float': float, 'integer': int, 
            'date': lambda x: datetime.date(*[int(v) for v in x.split('-')])}

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
        self.variables['owl_Thing'] = Thing('owl_Thing')
        self.variables['owl_Literal'] = Literal('owl_Literal')
        self.seen = {}
        self.var2ns ={}
        self.nr_of_triples = 0
#        self.time = time.time()
#        for pr in builtin_voc:
#            name = self.mangle_name(pr)
            # Instantiate ClassDomains to record instances of the types
#            name = name + "_type"
#            self.variables[name] = ClassDomain(name, pr)

    def add(self, triple):
        self.graph.add(triple)

    def add_file(self, f, format=None):
        tmp = Graph('default')
        if not format:
            format = check_format(f)
        tmp.load(f, format=format)
        for triple in tmp.triples((None,)*3):
            self.add(triple)
#            self.consider_triple(triple)
            
    def load_file(self, f, format=None):
        if not format:
            format = check_format(f)
        self.graph.load(f, format=format)
    
    def attach_fd(self):
        for (s, p, o) in (self.graph.triples((None,)*3)):
            self.consider_triple((s, p, o))

    def finish(self):
        cons = [(c.cost,c) for c in self.constraints if hasattr(c, 'cost')]
        cons.sort()
        for i,constraint in cons: 
            log.ontfinish("Trying %r of %d/%d " %(constraint,cons.index((i, constraint)),len(cons)))
            for key in constraint.affectedVariables():
                if not ( self.variables.get(key)):
                    break
                if isinstance( self.variables[key], fd):
                    continue
                self.variables[key].finish(self.variables, self.constraints)
            else:
#                try:
                constraint.narrow(self.variables)
#                except ConsistencyFailure, e:
#                    print "FAilure", e
        things = list(self.variables['owl_Thing'].getValues())
        things += list(self.variables['owl_Literal'].getValues())
        self.variables['owl_Thing'].setValues(things)

    def _sparql(self, query):
        qe = SP.Query.parseString(query)
        prefixes = qe.Prefix[0]

        resvars = []
        for v in qe.SelectQuery[0].VARNAME:
            resvars.append(v[0])
                                                                            
        where = qe.SelectQuery[0].WhereClause[0]

        triples = where.GroupGraphPattern[0].Triples
        new = []
        vars = []
        for trip in triples:
            case = 0
            inc = 1
            newtrip = []
            trip_ = [trip.Subject[0], trip.Verb[0], trip.Object[0]]
            for item in trip_:
                if isinstance(item[0], rdflib_literal):
                    o = item[0]
                    if o.datatype in builtin_voc:
                        o = XMLTypes[o.datatype.split('#')[-1]](o)
                    self.variables['owl_Literal'].addValue(o)
                    newtrip.append(o)
                elif item[0].NCNAME_PREFIX:
                    uri = prefixes[item[0].NCNAME_PREFIX[0]] + item[0].NCNAME[0]
                    newtrip.append(URIRef(uri))
                elif item.VAR1:
                    var_uri = URIRef('query_'+item.VAR1[0][0])
                    newtrip.append(var_uri)
                    vars.append(var_uri)
                    case += trip_.index(item) + inc
                    if inc == 2:
                        inc = 1
                    else:
                        inc = 2
                else:
                    newtrip.append(item[0][0])
            newtrip.append(case)
            new.append(newtrip)
        constrain = where.GroupGraphPattern[0].Constraint
        return new, prefixes, resvars, constrain, vars

# There are 8 ways of having the triples in the query, if predicate is not a builtin owl predicate
#
# case  s               p               o
#
# 0     bound           bound           bound  ; Check if this triple entails
# 1     var             bound           bound  ; add a hasvalue constraint
# 2     bound           var             bound  ; for all p's return p if p[0]==s and p[1]==o 
# 3     bound           bound           var    ; search for s in p
# 4     var             var             bound  ; for all p's return p[0] if p[1]==o 
# 5     var             bound           var    ; return the values of p
# 6     bound           var             var    ; for all p's return p[1] if p[0]==s
# 7     var             var             var    ; for all p's return p.getvalues
#

    def sparql(self, query):
        new, prefixes, resvars, constrain, vars = self._sparql(query)
        query_dom = {}
        query_constr = []
        for trip in new:
            case = trip.pop(-1)
            if case == 0:
                # Check if this triple entails
                sub = self.mangle_name(trip[0])
                prop = self.mangle_name(trip[1])
                obj = self.mangle_name(trip[2])
                if not obj in self.variables[prop].getValuesPrKey(sub):
                    raise ConsistencyFailure
            elif case == 1:
                # Add a HasValue constraint
                ns,pred = trip[1].split("#")
                if ns in namespaces.values():
                    self.consider_triple(trip)
                else:
                    var = self.make_var(Restriction, URIRef(trip[0]))
                    self.onProperty(var, URIRef(trip[1]))
                    self.hasValue(var, trip[2])
            elif case == 2:
                #  for all p's return p if p[0]==s and p[1]==o

                prop_name = self.make_var(ClassDomain, URIRef(trip[1]))
                indi_name = self.mangle_name(trip[0])
                indi = Individual(indi_name, trip[0])
                obj_name = self.mangle_name(trip[2])
                if  obj_name in self.variables:
                    obj = self.variables[self.mangle_name(trip[2])]
                else:
                    obj = trip[2]
                prop = self.variables[prop_name]
                # Get all properties by looking at 'rdf_Property'
                props = list(self.variables['rdf_Property'].getValues())
                prop.setValues(props)
                for p in props:
                    query_dom[p] = self.variables[p]
                # add a constraint trip[0] in domains[prop] and trip[2] in domains[prop].getValuesPrKey(trip[0])
                query_constr.append(PropertyConstrain(prop_name, indi, obj))

            elif case == 3:
                #  search for s in p
                prop = self.make_var(None, trip[1])
                #indi = self.variables[self.make_var(
                indi = Individual( self.mangle_name(trip[0]), trip[0])
                p_vals = self.variables[prop].getValuesPrKey(indi)
                var = self.make_var(Thing, trip[2])
                self.variables[var].setValues((p_vals))
            elif case == 4:
                #  for all p's return p[0] if p[1]==o 
                 
                sub_name = self.make_var(ClassDomain, URIRef(trip[0]))
                prop_name = self.make_var(ClassDomain, URIRef(trip[1]))
                sub = self.variables[sub_name]
                sub.setValues(list(self.variables['owl_Thing'].getValues()))
                prop = self.variables[prop_name]
                props = list(self.variables['rdf_Property'].getValues())
                prop.setValues(props)
                for p in props:
                    query_dom[p] = self.variables[p]
                obj_name = self.mangle_name(trip[2])
                if  obj_name in self.variables:
                    obj = self.variables[self.mangle_name(trip[2])]
                else:
                    obj = trip[2]
                query_constr.append(PropertyConstrain2(prop_name, sub_name, obj))
            elif case == 5:
                #  return the values of p
                prop = self.make_var(Property, URIRef(trip[1]))
                query_dom[prop] = self.variables[prop]
                p_vals = list(self.variables[prop].getValues())
                sub = self.make_var(Thing, trip[0])
                vals = set([v[0] for v in p_vals])
                if self.variables[sub].size():
                    vals &= set(self.variables[sub].getValues())
                self.variables[sub].setValues(vals)
                obj = self.make_var(Thing, trip[2])
                vals = set([v[1] for v in p_vals])
                if self.variables[obj].size():
                    vals &= set(self.variables[obj].getValues())
                self.variables[obj].setValues(vals)
                con = PropertyConstrain3(prop, sub, obj)
#                con = Expression([sub,prop,obj], "%s == (%s, %s)" %(prop, sub, obj))
                query_constr.append(con)

            elif case == 6:
# 6     bound           var             var    ; for all p's return p[1] if p[0]==s
                #  for all p's return p[1] if p[0]==s 
                prop = self.make_var(Property, URIRef(trip[1]))

                pass
            elif case == 7:
                #  for all p's return p.getvalues
                p_vals = []
                for p in self.variables['rdf_Property'].getValues():
                    p_vals += self.variables[p].getValues()
                    
                prop = self.make_var(Property, URIRef(trip[1]))
                self.variables[prop].setValues(p_vals)
                sub = self.make_var(Thing, trip[0])
                obj = self.make_var(Thing, trip[2])
                con = Expression([sub,prop,obj], "%s[0] == %s and %s[1] == %s" %(prop, sub, prop, obj))
                query_constr.append(con)
        # call finish on the variables in the query
        for v in vars:
            _dom, _ = self.variables[self.mangle_name(v)].finish(self.variables, query_constr) #query_dom, query_constr)
            query_dom.update(_dom)
        # Build a repository with the variables in the query
        dom = dict([(self.mangle_name(v),self.variables[self.mangle_name(v)])
                     for v in vars])

        dom.update(query_dom)
        # solve the repository and return the solution
        rep = Repository(dom.keys(), dom, query_constr)
        res_s = Solver(MyDistributor()).solve(rep, verbose=0)
        res = []
        query_vars = dict([('query_%s_'%name,name) for name in resvars])
        for d in res_s:
           res_dict = {}
           for k,v in d.items():
               if hasattr(v,'uri'):
                   val = v.uri
               else:
                   val = v 
               d[k] = (val)
               if k in query_vars:
                   res_dict[query_vars[k]] = (val)
           res.append(res_dict)
        return res
    
    def consider_triple(self,(s, p, o)):
        if (s, p, o) in self.seen:
            return
        self.nr_of_triples += 1
        log("Doing triple nr %i: %r" % (self.nr_of_triples,(s, p, o)))
#        tim = time.time()
#        log.considerTriple("Triples per second %f" %(1./(tim-self.time)))
#        self.time = tim
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
        #avar = self.make_var(ClassDomain, s)
        #else:
        pvar = self.make_var(Property, p)
        # Set the values of the property p to o
        self.type(s, Thing_uri)
        sub = self.mangle_name(s)
        if type(o) == URIRef:
            obj = self.mangle_name(o)
            if obj in self.variables:
                val = self.variables[obj]
            else:
                val = Individual(obj, o)
        elif type(o) == rdflib_literal:
#            self.variables.setdefault('owl_Literal', ClassDomain('owl_Literal',u''))
            if o.datatype in builtin_voc:
               o = XMLTypes[o.datatype.split('#')[-1]](o)
            self.variables['owl_Literal'].addValue(o)
            val = o
        else:
            val = o
        propdom = self.variables[pvar]
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

    def mangle_name(self, a):

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
            var = a
        return var
 
    def make_var(self, cls=fd, a=''):
        var = self.mangle_name(a)
        if not cls:
            return var
        if not var in self.variables:
            if a in builtin_voc and issubclass(builtin_voc[a], ClassDomain):
                cls = builtin_voc[a]
            cls = self.variables[var] = cls(var, a)
            if cls.constraint:
                self.constraints.extend(cls.constraint)
        elif not cls == self.variables[var].__class__ and issubclass(cls, self.variables[var].__class__):
            vals = self.variables[var].getValues()
            tmp = cls(var, a)
            tmp.setValues(list(vals))
            tmp.property = self.variables[var].property
            if tmp.constraint:
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
        if not var in builtin_voc :
            # var is not one of the builtin classes -> it is a Class 
            avar = self.make_var(ClassDomain, var)
            #self.type(s, Thing_uri)
            svar = self.mangle_name(s)
            s_type = Individual(svar, s)
            self.variables[svar] = s_type
            if type(self.variables[avar]) != FixedClassDomain:
                self.variables[avar].addValue(s_type)
            self.constraints.append(MemberConstraint(svar, avar))
        else:
            # var is a builtin class
            cls = builtin_voc[var]
            avar = self.make_var(ClassDomain, var)
            if cls in [Thing]:
                svar = self.mangle_name(s)
                self.variables[avar].addValue(Individual(svar, s))
                return
            svar = self.make_var(cls, s)
            for parent in cls.__mro__[1:]:
                if not hasattr(parent, 'uri'):
                    break
                typ_name = self.make_var(ClassDomain, parent.uri)
                self.variables[typ_name].addValue(svar)
            if cls == List:
                return
            cls = self.variables[svar]
            if cls.constraint:
                self.constraints.extend(cls.constraint)
#            if not isinstance(self.variables[avar], Property):
            if isinstance(self.variables[avar], Thing):
                self.variables[avar].addValue(Individual(svar, s))
            else:
                self.variables[avar].addValue(svar)
    
    def first(self, s, var):
        pass
    
    def rest(self, s, var):
        pass
    
    def onProperty(self, s, var):
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
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(ClassDomain, s)
        self.variables[svar].bases.append(avar)
        self.variables[svar].bases.extend(self.variables[avar].bases)
        self.constraints.append(SubClassConstraint(svar, avar))

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
        svar = self.mangle_name(s)
        res = list(self.variables[var].getValues())
        # For Individuals (datatypes handled differently ?) XXX
        s_cls = FixedClassDomain(svar, s, [Individual(self.mangle_name(x), x) for x in res])
        self.variables[svar] = s_cls

    def unionOf(self,s, var):
        avar = self.flatten_rdf_list(var)
        res = [self.mangle_name(x) for x in self.variables[avar]]
        self.variables[avar] = ClassDomain(avar, var, res)
        svar = self.make_var(ClassDomain, s)
        cons = UnionofConstraint(svar, avar)
        self.constraints.append(cons)
    
    def intersectionOf(self, s, var):
        avar = self.flatten_rdf_list(var)
        res = [self.mangle_name(x) for x in self.variables[avar]]
        self.variables[avar] = ClassDomain(avar, var, res)
        svar = self.make_var(ClassDomain, s)
        cons = IntersectionofConstraint(svar, avar)
        self.constraints.append(cons)

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

if __name__ == "__main__":
    import SimpleXMLRPCServer

    import sys

    def ok():
        return "ok"

    rdffile = sys.argv[-1]
    O = Ontology()
    O.add_file(rdffile)
    O.attach_fd()
    O.consistency()
    server = SimpleXMLRPCServer.SimpleXMLRPCServer(("localhost", 9000))
    server.register_instance(O)
    server.register_function(ok)
    server.serve_forever()

