from rdflib import Graph, URIRef, BNode
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
        
class Property(ClassDomain):
    # Property contains the relationship between a class instance and a value
    # - a pair. To accomodate global assertions like 'range' and 'domain' anonymous
    # pairs are allowed, ie None as key
    def __init__(self, name='', values=[], bases = []):
        ClassDomain.__init__(self, name, values, bases)
        self._dict = {}

    def getValues(self):
        return tuple(self._dict.items())

    def setValues(self, values):
        for k,v in values:
            self._dict.setdefault(k,[])
            if type(v) == list:
                self._dict[k] = v
            else:
                if not v in self._dict[k]:
                    self._dict[k].append(v)

    def removeValues(self, values):
        for k,v in values:
            vals = self._dict[k]
            if vals == [None]:
                self._dict.pop(k)
            else:
                self._dict[k] = [ x for x in vals if x != v] 
            
class ObjectProperty(Property):

    pass

class DataTypeProperty(Property):

    pass

class Thing:

    pass

class AllDifferent(ClassDomain):
    # A special class whose members are distinct
    # Syntactic sugar
    pass

class Nothing:

    pass


class FunctionalProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = FunctionalCardinality(name, 1)
        
class InverseFunctionalProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = InverseFunctionalCardinality(name, 1)

class TransitiveProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = TransitiveConstraint(name)

class SymmetricProperty(Property):
    
    def __init__(self, name='', values=[], bases = []):
        Property.__init__(self, name, values, bases)
        self.constraint = SymmetricConstraint(name)

class DataRange:
    
    def __init__(self):
        pass

class Restriction(ClassDomain):
    pass

builtin_voc = {
               'Thing' : Thing,
               'Class' : ClassDomain,
               'ObjectProperty' : ObjectProperty,
               'AllDifferent' : AllDifferent ,
##               'AnnotationProperty' : AnnotationProperty,
##               'DataRange' : DataRange,
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
               'TransitiveProperty' : TransitiveProperty
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
                
            if ns in namespaces.items():
                pred = getattr(self, func)
                res = pred(s, p, o) 
                if res == None:
                    continue
                if type(res) != list :
                    res = [res]
                avar = self.make_var(fd, s) 
            else:
                res = [o]
                avar = self.make_var(Property, p)
                # Set the values of the property p to o
                sub = self.make_var(fd, s) 
                obj = self.make_var(fd, o) 
                res = self.variables[avar].getValues() 
                self.variables[avar].setValues(res + [(sub, obj)])
            if self.variables.get(avar) and type(self.variables[avar]) == fd:
                self.variables[avar] = fd(list(self.variables[avar].getValues()) + res)
            else:
                self.variables[avar] = fd(res)

    def merge_constraints(self):
        # Make the intersection of multiple rdfs:range constraints on the same variable
        cons_dict = {}
        new_cons =[]
        for con in self.constraints:
            if isinstance(con, RangeConstraint):
                cons_dict.setdefault(con.variable, [])
                cons_dict[con.variable].append(con)
            else:
                new_cons.append(con)
        for k,v in cons_dict.items():
            for con in v:
                pass
                
    def solve(self,verbose=0):
        #self.merge_constraints()
        rep = Repository(self.variables.keys(), self.variables, self.constraints)
        return Solver().solve(rep, verbose)

    def consistency(self):
        rep = Repository(self.variables.keys(), self.variables, self.constraints)
        rep.consistency()
 
    def get_list(self, subject):
        res = []
        first = list(self.objects(subject, rdf_first)) 
        assert len(first) == 1
        self.seen[self.make_var(fd, subject, p)]= 1
        if type(first[0]) == URIRef:
            var = self.make_var(fd, first[0])
            if var not in self.variables.keys():
                self.variables[var] = ClassDomain(var)
        res += first
        
        rest = list(self.objects(subject, rdf_rest)) 
        self.seen[self.make_var(fd, subject, p)]= 1
        if "#nil" in rest[0] :
           return res
        else:
           res += self.get_list(rest[0])
        return res

    def make_var(self, cls=fd, *args):
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
        if not var in self.variables.keys():
            self.variables[var] = cls(var)
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
            avar = self.make_var(ClassDomain, cls, prop)
        else:
            avar = self.make_var(ClassDomain, prop)
        if not self.variables.get(avar):
            self.variables[avar] = ClassDomain(avar)
        return avar
    
#---------------- Implementation ----------------

    def type(self, s, p, var):
        svar = self.make_var(ClassDomain, s)
        if (type(var) == URIRef and not 
           (var in [URIRef(namespaces['owl']+'#'+x) for x in builtin_voc])):
            # var is not one of the builtin classes
            avar = self.make_var(ClassDomain, var)
            self.variables[svar].setValues(self.variables[avar].getValues())
            constrain = BinaryExpression([svar, avar],"%s in %s" %(svar,  avar))
            self.constraints.append(constrain)
        else:
            # var is a builtin class
            cls =builtin_voc[var.split('#')[-1]](name=svar)
            if hasattr(cls, 'constraint'):
                self.constraints.append(cls.constraint)
            vals = self.variables[svar].getValues()
            cls.setValues(vals)
            self.variables[svar] =  cls

    def first(self, s, p, var):
        pass

    def rest(self, s, p, var):
        pass

#---Class Axioms---#000000#FFFFFF-----------------------------------------------

    def subClassOf(self, s, p, var):
        # s is a subclass of var means that the 
        # class extension of s is a subset of the
        # class extension of var. 
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(ClassDomain, s)
        cons = SubClassConstraint( svar, avar)
        self.constraints.append(cons)

    def equivalentClass(self, s, p, var):
        self.subClassOf(s, p, var)
        self.subClassOf(var, p, s)

    def disjointWith(self, s, p, var):
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(ClassDomain, s)
        constrain = DisjointClassConstraint(svar, avar) 
        self.constraints.append(constrain)

    def complementOf(self, s, p, var):
        # add constraint of not var
        # TODO: implementthis for OWL DL
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(ClassDomain, s)

    def oneOf(self, s, p, var):
        res = self.get_list(var)
        prop = self.find_uriref(s)
        avar = self.make_var(fd, prop)
        if self.variables.get(avar) and type(self.variables[avar]) == fd:
            self.variables[avar] = fd(list(self.variables[avar].getValues()) + res)
        else:
            self.variables[avar] = fd(res)

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

#---Property Axioms---#000000#FFFFFF--------------------------------------------

    def range(self, s, p, var):
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(Property, s)
        vals = get_values(self.variables[avar], self.variables)  
        for k,v in self.variables[svar].getValues():
            for x in v:
                if not x in vals:
                    vals.append(x)
        vals =[(None,val) for val in vals]
        self.variables[svar].setValues(vals)
        cons = RangeConstraint(svar, avar)
        self.constraints.append(cons)

    def domain(self, s, p, var):
        # The classes that has this property (s) must belong to the class extension of var
        avar = self.make_var(ClassDomain, var)
        svar = self.make_var(Property, s)
        assert isinstance(self.variables[svar], Property)
        assert isinstance(self.variables[avar], ClassDomain)
        vals = get_values(self.variables[avar], self.variables)  
        if len(vals) == 0 :
            vals = [(self.variables[avar], None)]
        for k,v in self.variables[svar].getValues():
            if not k in vals:
                vals.append((k,v))
        self.variables[svar].setValues(vals)
        cons = DomainConstraint(svar, avar)
        self.constraints.append(cons)

    def subPropertyOf(self, s, p, var):
        # s is a subproperty of var
        avar = self.make_var(Property, var)
        svar = self.make_var(Property, s)
        cons = SubPropertyConstraint( svar, avar)
        self.constraints.append(cons)

    def equivalentProperty(self, s, p, var):
        avar = self.make_var(Property, var)
        svar = self.make_var(Property, s)
        cons = EquivalentConstraint( svar, avar)
        self.constraints.append(cons)

    def inverseOf(self, s, p, var):
        # TODO: implement this 
        pass

#---Label---#000000#FFFFFF------------------------------------------------------

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

    def differentFrom(self, s, p, var):
        s_var = self.make_var(ClassDomain, s)
        var_var = self.make_var(fd, var)
        constrain = BinaryExpression([s_var, var_var],"%s != %s" %(s_var,  var_var))
        self.constraints.append(constrain)

    def distinctMembers(self, s, p, var):
        res = self.get_list(var)
        self.constraints.append(AllDistinct([self.make_var(ClassDomain, y) for y in res]))
        return res

    def sameAs(self, s, p, var):
        constrain = BinaryExpression([self.make_var(ClassDomain, s), self.make_var(ClassDomain, var)],
               "%s == %s" %(self.make_var(ClassDomain, s), self.make_var(ClassDomain, var)))
        self.constraints.append(constrain)

    def onProperty(self, s, p, var):
        # TODO: implement this 
        pass

    def hasValue(self, s, p, var):
        # TODO: implement this 
        pass

    def allValuesFrom(self, s, p, var):
        # TODO: implement this 
        pass

    def someValuesFrom(self, s, p, var):
        # TODO: implement this 
        pass

    def imports(self, s, p, var):
        # TODO: implement this 
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


class MaxCardinality(OwlConstraint):
    """Contraint: all values must be distinct"""

    def __init__(self, variable, cardinality):
        OwlConstraint.__init__(self, variable)
        self.__cost = 1
        self.cardinality = cardinality

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        if len(domains[self._variables[0]]) > self.cardinality:
            raise ConsistencyFailure("Maxcardinality exceeded")
        else:
            return 1

class MinCardinality(MaxCardinality):

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
          
        if len(domains[self._variables[0]]) < self.cardinality:
            raise ConsistencyFailure()
        else:
            return 1
        
class Cardinality(MaxCardinality):
    
    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
          
        if len(domains[self._variables[0]]) != self.cardinality:
            raise ConsistencyFailure()
        else:
            return 1


def get_values(dom, domains, attr = 'getValues'):
    res = []
    for val in getattr(dom, attr)():
        res.append(val)
        if type(val) == tuple:
            val = val[0]
        if val in domains.keys():
            res.extend(get_values(val, domains, attr))
    #res[dom] = 1
    return res

class SubClassConstraint(OwlConstraint):

    def __init__(self, variable, cls_or_restriction):
        OwlConstraint.__init__(self, variable)
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]
        bases = get_values(superdom, domains, 'getBases')  
        subdom.bases += [bas for bas in bases if bas not in subdom.bases]
        vals = get_values(subdom, domains, 'getValues')
        superdom.values += [val for val in vals if val not in superdom.values]

class DisjointClassConstraint(OwlConstraint):

    def __init__(self, variable, cls_or_restriction):
        OwlConstraint.__init__(self, [variable])
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]
        bases = get_values(superdom, domains, 'getBases')  
        subdom.bases += [bas for bas in bases if bas not in subdom.bases]
        vals1 = get_values(superdom, domains, 'getValues')  
        vals2 = get_values(variable, domains, 'getValues')  
        for i in vals1:
            if i in vals2:
                raise ConsistencyFailure()

class ComplementClassConstraint(OwlConstraint):

    def __init__(self, variable, cls_or_restriction):
        OwlConstraint.__init__(self, variable)
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]

class RangeConstraint(OwlConstraint):

    def __init__(self, variable, cls_or_restriction):
        OwlConstraint.__init__(self, variable)
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]
        vals = get_values(superdom, domains, 'getValues')  
        res = []
        svals = get_values(subdom, domains, 'getValues')
        for k,val in svals: 
            for v in val:
                if not v in vals:
                    res.append((k,v)) 
        subdom.removeValues(res)

class DomainConstraint(OwlConstraint):

    def __init__(self, variable, cls_or_restriction):
        OwlConstraint.__init__(self, variable)
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]
        vals = get_values(superdom, domains, 'getValues')  
        res = []
        for k,val in get_values(subdom, domains, 'getValues'):
            if not k in vals and k != superdom:
                res.append((k,val))
        subdom.removeValues(res)

class SubPropertyConstraint(OwlConstraint):

    def __init__(self, variable, cls_or_restriction):
        OwlConstraint.__init__(self, variable)
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]
        vals = get_values(superdom, domains, 'getValues')  
        for val in subdom.getValues():
            if not val in vals:
                vals.append(val)
        superdom.setValues(vals)

class EquivalentPropertyConstraint(OwlConstraint):

    def __init__(self, variable, cls_or_restriction):
        OwlConstraint.__init__(self, variable)
        self.super = cls_or_restriction
        self.variable = variable

    def narrow(self, domains):
        subdom = domains[self.variable]
        superdom = domains[self.super]
        vals = get_values(superdom, domains, 'getValues')  
        for val in subdom.getValues():
            if not val in vals:
                raise ConsistencyFailure("Value not in prescribed range")

class FunctionalCardinality(MaxCardinality):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        for cls, val in domain:
            if len(val) != self.cardinality:
                raise ConsistencyFailure("Maxcardinality exceeded")
        else:
            return 0

class InverseFunctionalCardinality(MaxCardinality):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        vals = {}
        for cls, val in domain:
            for v in val:
                if vals.has_key(v):
                    raise ConsistencyFailure("Maxcardinality exceeded")
                else:
                    vals[v] = 1
        else:
            return 0

class TransitiveConstraint(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        domain_dict = dict( domain )
        for cls, val in domain:
            for v in val:
                if v in domain_dict:
                    val.extend(domain_dict[v])
            domain_dict[cls] = val
        domains[self.variable].setValues(domain_dict.items())

class SymmetricConstraint(OwlConstraint):
    """Contraint: all values must be distinct"""

    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        domain = domains[self.variable].getValues()
        domain_dict = dict( domain )
        for cls, val in domain:
            for v in val:
                domain_dict.setdefault(v, [])
                domain_dict[v].append(cls)
        domains[self.variable].setValues(domain_dict.items())
