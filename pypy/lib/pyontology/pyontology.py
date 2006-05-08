from rdflib import Graph, URIRef, BNode, Literal
from logilab.constraint import  Repository, Solver
from logilab.constraint.fd import  Expression, FiniteDomain as fd
from logilab.constraint.propagation import AbstractDomain, AbstractConstraint, ConsistencyFailure
from constraint_classes import *
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

    def addValue(self, value):
	    self.values[value] = True

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
        return items
    
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
        tmp.load(f, format)
        for triple in tmp.triples((None,)*3):
            self.add(triple)
            
    def load_file(self, f, format=None):
        if not format:
            format = check_format(f)
        self.graph.load(f, format=format)
    
    def attach_fd(self):
        for (s, p, o) in (self.graph.triples((None,)*3)):
            self.consider_triple((s, p, o))
        assert len(list(self.graph.triples((None,)*3))) == len(self.seen.keys())

    def consider_triple(self,(s, p, o)):
        if (s, p, o) in self.seen.keys():
            return
        self.seen[(s, p, o)] = True
        if p.find('#') != -1:
            ns, func = p.split('#')
        else:
            ns =''
            func = p
        if ns in namespaces.values():
            #predicate is one of builtin OWL or rdf predicates
            pred = getattr(self, func)
            res = pred(s, o)
            avar = self.make_var(ClassDomain, s)
        else:
            avar = self.make_var(Property, p)
            # Set the values of the property p to o
            sub = self.make_var(ClassDomain, s)
            obj = self.make_var(Thing, o)
            propdom = self.variables[avar]
            res = propdom.addValue(sub, obj)

    def resolve_item(self, item):
        item_as_subject = self.graph.triples((item, None, None))
        for triple in item_as_subject:
            self.consider_triple(triple)

    def get_individuals_of(self, item):
        item_as_subject = self.graph.triples(( None, rdf_type, item))
        for triple in item_as_subject:
            self.consider_triple(triple)

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

    def evaluate(self, terms):
        # terms is a dictionary of types of restriction and list of values for this restriction
        term = terms
        if len(term) < 1: return    
        mini = maxi = equal = None
        for tp,val in term:
            if tp == '<':
               if not maxi or val < maxi : maxi = val
            elif tp == '>':
               if not mini or val > mini : mini = val
            else:
                if equal:
                    raise ConsistencyFailure
                equal = val

        if mini and maxi and (mini > maxi or
                             equal < mini or
                             equal > maxi):
            raise ConsistencyFailure
        
    def check_TBoxes(self):
        for var, cls in self.variables.items():
            for prop, terms in cls.TBox.items():
                if len(terms['Cardinality']) > 1: 
                    self.evaluate(terms['Cardinality'])
    
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
    
#---------------- Implementation ----------------
    
    def comment(self, s, var):
        pass
    
    def type(self, s, var):
        avar = self.make_var(ClassDomain, var)
        if not var in builtin_voc :
            # var is not one of the builtin classes
            svar = self.make_var(self.variables[avar].__class__, s)
        else:
            # var is a builtin class
            cls = builtin_voc[var]
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
        self.resolve_item(s)
        self.resolve_item(var)
        avar = self.make_var(None, var)
        svar = self.make_var(ClassDomain, s)
        obj = self.variables[avar]
        sub = self.variables[svar]

        if obj.TBox:
            for key in obj.TBox.keys():
                sub.TBox.setdefault(key,{})
                prop = sub.TBox[key]
                for typ in obj.TBox[key].keys():
                    prop.setdefault(typ, [])
                    prop[typ].extend(obj.TBox[key][typ])

#            if isinstance(self.variables[avar], Restriction):
#                self.variables.pop(avar)
        else:
            cons = SubClassConstraint( svar, avar)
            self.constraints.append(cons)
        self.get_individuals_of(var)

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
        self.resolve_item(s)
        svar =self.make_var(Restriction, s)
        cls = list(self.graph.subjects(None,s))[0]
        cls_name = self.make_var(ClassDomain, cls)
        prop = self.variables[svar].property
        self.variables[svar].TBox[prop] = {'Cardinality': [( '<', int(var))]}
        formula = "not isinstance(%s[0], self.variables[%s]) or len(%s[1] < int(%s))" %(prop, cls_name, prop, var)
        constrain = Expression([prop], formula)
        self.constraints.append(constrain)

    def minCardinality(self, s, var):
        """ Len of finite domain of the property shall be greater than or equal to var"""
        self.resolve_item(s)
        svar =self.make_var(Restriction, s)
        cls = list(self.graph.subjects(None,s))[0]
        cls_name = self.make_var(ClassDomain, cls)
        prop = self.variables[svar].property
        self.variables[svar].TBox[prop] = {'Cardinality': [( '>', int(var))]}
        formula = "not isinstance(%s[0], self.variables[%s]) or len(%s[1] > int(%s))" %(prop, cls_name, prop, var)
        constrain = Expression([prop], formula)
        self.constraints.append(constrain)
    
    def cardinality(self, s, var):
        """ Len of finite domain of the property shall be equal to var"""
        self.resolve_item(s)
        svar =self.make_var(Restriction, s)
        cls = list(self.graph.subjects(None,s))[0]
        cls_name = self.make_var(ClassDomain, cls)
        prop = self.variables[svar].property
        self.variables[svar].TBox[prop] = {'Cardinality': [( '=', int(var))]}
        formula = "not isinstance(%s[0], self.variables[%s]) or len(%s[1] == int(%s))" %(prop, cls_name, prop, var)
        constrain = Expression([prop], formula)
        self.constraints.append(constrain)
    
    def hasValue(self, s, var):
        self.resolve_item(var)
        svar = self.make_var(Restriction, s)
        avar = self.make_var(None, var)
        restr = self.variables[svar]
        restr.TBox['hasValue'] = [('hasvalue', var)]
#        constrain = HasvalueConstraint(svar, avar)
#        self.constraints.append(constrain)
    
    def allValuesFrom(self, s, var):
        self.resolve_item(var)
        svar = self.make_var(Restriction, s)
        avar = self.make_var(None, var)
        restr = self.variables[svar]
        restr.TBox['allValues'] = [('allvalue', var)]
#        constrain = AllValueConstraint(svar, avar)
#        self.constraints.append(constrain)
    
    def someValuesFrom(self, s, var):
        self.resolve_item(var)
        svar = self.make_var(Restriction, s)
        avar = self.make_var(None, var)
        restr = self.variables[svar]
        restr.TBox['someValues'] = [('somevalues', var)]
#        constrain = SomeValueConstraint(svar, avar)
#        self.constraints.append(constrain)

# -----------------              ----------------
    
    def imports(self, s, var):
        # PP TODO: implement this
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

