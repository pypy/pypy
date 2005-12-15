from rdflib import Graph, URIRef, BNode
from logilab.constraint import  Repository, Solver
from logilab.constraint.fd import Equals, AllDistinct, BinaryExpression, Expression 
from logilab.constraint.fd import  FiniteDomain as fd
from logilab.constraint.propagation import AbstractDomain, AbstractConstraint, ConsistencyFailure
import sys

namespaces = {'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns',
      'rdfs':'http://www.w3.org/2000/01/rdf-schema',
      'dc':'http://purl.org/dc/elements/1.0/',
      'xmlns':'http://www.w3.org/1999/xhtml',
      'owl':'http://www.w3.org/2002/07/owl',
}
uris = {}
for k,v in namespaces.items(): 
    uris[v] = k

Thing = URIRef(u'http://www.w3.org/2002/07/owl#Thing')
Class = URIRef(u'http://www.w3.org/2002/07/owl#Class')
builtin_voc = [
               'Thing',
               'Class',
               'ObjectProperty',
               'AllDifferent',
               'AnnotationProperty',
               'DataRange',
               'DatatypeProperty',
               'DeprecatedClass',
               'DeprecatedProperty',
               'FunctionalProperty',
               'InverseFunctionalProperty',
               'Nothing',
               'ObjectProperty',
               'Ontology',
               'OntologyProperty',
               'Restriction',
               'SymmetricProperty',
               'TransitiveProperty'
              ]
  
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
                owl,func = p.split('#')
            else:
                owl =''
                func = p
                #print s, p, o
                #raise Exception
            if owl in [namespaces['owl'],namespaces['rdf'],namespaces['rdfs']]:
                pred = getattr(self, func)
            else:
                pred = None
            if pred: 
                res = pred(s, p, o) 
                if res == None:
                    continue
                if type(res) != list :
                    res = [res]
                avar = self.make_var(s) 
            else:
                res = [o]
                avar = self.make_var(s,p) 
            if self.variables.get(avar) and type(self.variables[avar]) == fd:
                self.variables[avar] = fd(list(self.variables[avar].getValues()) + res)
            else:
                self.variables[avar] = fd(res)
      #  for var in self.seen:
      #      self.variables.pop(var)
      #  self.seen = {}
                    
    def solve(self,verbose=0):
        rep = Repository(self.variables.keys(), self.variables, self.constraints)
        return Solver().solve(rep,verbose)

    def consistency(self):
        rep = Repository(self.variables.keys(), self.variables, self.constraints)
        rep.consistency()
 
    def get_list(self, subject):
        res = []
        p = URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#first')
        first = list(self.objects(subject, p)) 
        assert len(first) == 1
        self.seen[self.make_var(subject,p)]= 1
        if type(first[0]) == URIRef:
            var = self.make_var(first[0])
            if var not in self.variables.keys():
                self.variables[var] = ClassDomain(var)
        res += first
      
        p = URIRef(u'http://www.w3.org/1999/02/22-rdf-syntax-ns#rest')
        rest = list(self.objects(subject, p)) 
        self.seen[self.make_var(subject,p)]= 1
        if "#nil" in rest[0] :
           return res
        else:
           res += self.get_list(rest[0])
        return res

    def make_var(self,*args):
        res = []
        for a in args:
            if type(a) == URIRef:
                if a.find('#') != -1:
                    ns,name = a.split('#')
                else:
                    ns,name = a,''
                if ns not in uris.keys():
                    uris[ns] = ns.split('/')[-1]
                    namespaces[uris[ns]] = ns
                mangle_name = uris[ns] + '_' + name    
                res.append(mangle_name)
            else:
                res.append(a)
        var = '.'.join([str(a.replace('-','_')) for a in res])
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
                return
        #        pr = list( self.subjects(r,s) )
        #    assert len(pr) == 1
            return pr[0]
        else:
            return s
               
    def find_uriref(self, s):
        while type(s) == BNode:
            s = list(self.subjects(None,s))[0]
        return s

    def find_property(self, s):
        prop = self.find_prop(s)
        cls = self.find_cls(s)
        if cls :
            avar = self.make_var(cls, prop)
        else:
            avar = self.make_var( prop)
        if not self.variables.get(avar):
            self.variables[avar] = ClassDomain(avar)
        return avar
    
#---------------- Implementation ----------------

    def type(self, s, p, var):
        avar = self.make_var(var)
        svar = self.make_var(s)
        if (type(var) == URIRef and not 
           (var in [URIRef(namespaces['owl']+'#'+x) for x in builtin_voc])):
            # var is not one of the builtin classes
            if not self.variables.get(svar): 
                self.variables[svar] = ClassDomain(svar)
            if not self.variables.get(avar): 
                self.variables[avar] = ClassDomain(avar)
             
#            if self.variables[avar].values:
            self.variables[svar].values +=  self.variables[avar].values
            constrain = BinaryExpression([svar, avar],"%s in %s" %(svar,  avar))
            self.constraints.append(constrain)
        else:
            # var is a builtin class
            pass    

    def first(self, s, p, var):
        pass

    def rest(self, s, p, var):
        pass

    def range(self, s, p, var):
        pass

    def domain(self, s, p, var):
        pass

# --------- Class Axioms ---------------------

    def subClassOf(self, s, p, var):
        # s is a subclass of var means that the 
        # class extension of s is a subset of the
        # class extension of var. 
        avar = self.make_var(var)
        svar = self.make_var(s)
        if not self.variables.get(avar): 
            self.variables[avar] = ClassDomain(avar)
        constrain = SubClassConstraint(svar, avar) 
        self.constraints.append(constrain)
        
    def equivalentClass(self, s, p, var):
        avar = self.make_var(var)
        svar = self.make_var(s)
        if not self.variables.get(avar): 
            self.variables[avar] = ClassDomain(avar)
#        constrain = EquivalentClassConstraint(svar, avar) 
#        self.constraints.append(constrain)
        self.subClassOf(s, p, var)
        self.subClassOf(var, p, s)

    def disjointWith(self, s, p, var):
        avar = self.make_var(var)
        svar = self.make_var(s)
        if not self.variables.get(avar): 
            self.variables[avar] = ClassDomain(avar)
        constrain = DisjointClassConstraint(svar, avar) 
        self.constraints.append(constrain)

    def oneOf(self, s, p, var):
        res = self.get_list(var)
        prop = self.find_uriref(s)
        avar = self.make_var( prop)
        if self.variables.get(avar) and type(self.variables[avar]) == fd:
            self.variables[avar] = fd(list(self.variables[avar].getValues()) + res)
        else:
            self.variables[avar] = fd(res)

    def maxCardinality(self, s, p, var):
        """ Len of finite domain of the property shall be less than or equal to var"""
        avar = self.find_property(s)
        constrain = MaxCardinality(avar,int(var))
        self.constraints.append(constrain) 

    def minCardinality(self, s, p, var):
        """ Len of finite domain of the property shall be greater than or equal to var"""
        avar = self.find_property(s)
        constrain = MinCardinality(avar,int(var))
        self.constraints.append(constrain) 

    def cardinality(self, s, p, var):
        """ Len of finite domain of the property shall be equal to var"""
        avar = self.find_property(s)
        # Check if var is an int, else find the int buried in the structure
        constrain = Cardinality(avar,int(var))
        self.constraints.append(constrain) 

    def unionOf(self,s, p, var):
        res = self.get_list(var)
        return res #There might be doubles (but fd takes care of that)

    def intersectionOf(self, s, p, var):
        res = self.get_list(var)
        result = {}.fromkeys(res[0])
        for el in res:
            for cls in result.keys():
                if cls not in el:
                   result.pop(cls)
        return result.keys()

    def differentFrom(self, s, p, var):
        s_var = self.make_var(s)
        var_var = self.make_var(var)
        if not self.variables.get(s_var):
            self.variables[s_var] = ClassDomain(s_var)
        if not self.variables.get(var_var):
            self.variables[var_var] = fd([])
        constrain = BinaryExpression([s_var, var_var],"%s != %s" %(s_var,  var_var))
        self.constraints.append(constrain)

    def distinctMembers(self, s, p, var):
        res = self.get_list(var)
        self.constraints.append(AllDistinct([self.make_var(y) for y in res]))
        return res

    def sameAs(self, s, p, var):
        constrain = BinaryExpression([self.make_var(s), self.make_var(var)],"%s == %s" %(self.make_var(s), self.make_var( var)))
        self.constraints.append(constrain)

    def complementOf(self, s, p, var):
        # add constraint of not var
        pass

    def onProperty(self, s, p, var):
        pass

    def hasValue(self, s, p, var):
        pass

    def allValuesFrom(self, s, p, var):
        pass

    def someValuesFrom(self, s, p, var):
        pass

    def equivalentProperty(self, s, p, var):
        pass

    def inverseOf(self, s, p, var):
        pass

    def someValuesFrom(self, s, p, var):
        pass

    def subPropertyOf(self, s, p, var):
        pass

    def imports(self, s, p, var):
        pass

# ----------------- Helper classes ----------------

class MaxCardinality(AbstractConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, variable, cardinality):
        AbstractConstraint.__init__(self, [variable])
        # worst case complexity
        self.__cost = 1 #len(variables) * (len(variables) - 1) / 2
        self.cardinality = cardinality

    def __repr__(self):
        return '<MaxCardinality %s,%i>' % (str(self._variables[0]),self.cardinality)

    def estimateCost(self, domains):
        return self.__cost

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        if len(domains[self._variables[0]]) > self.cardinality:
            print " I Think I will raise an exception"
            raise ConsistencyFailure("Maxcardinality exceeded")
        else:
            return 1

class MinCardinality(MaxCardinality):

    def __repr__(self):
        return '<MinCardinality %s,%i>' % (str(self._variables[0]),self.cardinality)

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
          
        if len(domains[self._variables[0]]) < self.cardinality:
            raise ConsistencyFailure()
        else:
            return 1
        
class Cardinality(MaxCardinality):
    
    def __repr__(self):
        return '<Cardinality %s,%i>' % (str(self._variables[0]),self.cardinality)

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
          
        if len(domains[self._variables[0]]) != self.cardinality:
            raise ConsistencyFailure()
        else:
            return 1

def get_bases(cls_dom, domains):
    res = {}
    for bas in cls_dom.bases:
        res[bas] = 1
        if bas in domains.keys():
            res.update( get_bases(bas, domains))
    res[cls_dom] = 1
    return res

class SubClassConstraint(AbstractConstraint):

    def __init__(self, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [variable])
        # worst case complexity
        self.__cost = 1 #len(variables) * (len(variables) - 1) / 2
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]
        bases = get_bases(superdom, domains).keys()
        print subdom,superdom, bases, subdom.bases
        subdom.bases += [bas for bas in bases if bas not in subdom.bases]
       
class EquivalentClassConstraint(AbstractConstraint):

    def __init__(self, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [variable])
        # worst case complexity
        self.__cost = 1 #len(variables) * (len(variables) - 1) / 2
        self.other = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        otherdom = domains[self.other]
        bases = get_bases(subdom, domains).keys()
        otherbases = get_bases(otherdom, domains).keys()
        print subdom, otherdom, "----",bases , otherbases
        if bases != otherbases:
            raise ConsistencyFailure()
        else:
            return 1

class DisjointClassConstraint(AbstractConstraint):

    def __init__(self, variable, cls_or_restriction):
        AbstractConstraint.__init__(self, [variable])
        # worst case complexity
        self.__cost = 1 #len(variables) * (len(variables) - 1) / 2
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]
        bases = get_bases(superdom, domains).keys()
        print subdom,superdom, bases, subdom.bases
        subdom.bases += [bas for bas in bases if bas not in subdom.bases]
        
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

    def __repr__(self):
        return "<ClassDomain %s>" % str(self.name)

    def __getitem__(self, index):
        return None

    def __iter__(self):
        return iter(self.bases) 

    def size(self):
        return sys.maxint

    __len__ = size

    def copy(self):
        return self

    def removeValues(self, values):
        print "remove values from ClassDomain", values
        self.bases.pop(self.bases.index(values[0]))

    def getValues(self):
        return self.bases
 
