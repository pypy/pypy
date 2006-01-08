# tests for the Ontology class
import py

try:
    import logilab.constraint
    import rdflib
except ImportError:
    import py 
    py.test.skip("Logilab.constraint and/or rdflib not installed")

from pypy.lib.pyontology.pyontology import * # Ontology, ClassDomain, SubClassConstraint 
from rdflib import Graph, URIRef, BNode

def test_makevar():
    O = Ontology()
    var = URIRef(u'http://www.w3.org/2002/03owlt/unionOf/premises004#A-and-B')
    name = O.make_var(ClassDomain, var)
    cod = name+' = 1'
    exec cod
    assert O.make_var(None, var) in locals() 
    assert isinstance(O.variables[name], ClassDomain)
     
def test_subClassof():
    O = Ontology()
    a = URIRef(u'http://www.w3.org/2002/03owlt/unionOf/premises004#A')
    b = URIRef(u'http://www.w3.org/2002/03owlt/unionOf/premises004#B')
    c = URIRef(u'http://www.w3.org/2002/03owlt/unionOf/premises004#C')
    A = O.make_var(ClassDomain, a)
    C = O.make_var(ClassDomain, c)
    C = O.make_var(ClassDomain, b)
    O.subClassOf(b, a)
    O.subClassOf(c, b)
    for con in O.constraints:
        con.narrow(O.variables)
    assert len(O.variables) == 3
    assert O.variables[A] in O.variables[C].bases

def test_ClassDomain():
    a = ClassDomain()
    assert a.bases == [a]
    cls =  1
    b = ClassDomain('B',[],[a])
    assert b in b.bases
    assert a in b.bases
    assert len(b.bases) == 2

def test_subClassconstraint():
    a = ClassDomain('A')
    b = ClassDomain('B')
    c = ClassDomain('C')
    con = SubClassConstraint('b','a')
    con2 = SubClassConstraint('c','b')
    con.narrow({'a': a, 'b': b, 'c': c}) 
    con2.narrow({'a': a, 'b': b, 'c': c})
    assert a in c.bases
    assert b in c.bases
    assert c in c.bases

def test_subClassconstraintMulti():
    a = ClassDomain('A')
    b = ClassDomain('B')
    c = ClassDomain('C')
    con = SubClassConstraint('c','a')
    con2 = SubClassConstraint('c','b')
    con.narrow({'a': a, 'b': b, 'c': c}) 
    con2.narrow({'a': a, 'b': b, 'c': c})
    assert a in c.bases
    assert b in c.bases
    assert c in c.bases

def test_subClassconstraintMulti2():
    a = ClassDomain('A')
    b = ClassDomain('B')
    c = ClassDomain('C')
    con = SubClassConstraint('c','a')
    con2 = SubClassConstraint('c','b')
    con3 = SubClassConstraint('a','c')
    con.narrow({'a': a, 'b': b, 'c': c}) 
    con2.narrow({'a': a, 'b': b, 'c': c})
    con3.narrow({'a': a, 'b': b, 'c': c})
    assert a in c.bases
    assert b in c.bases
    assert c in c.bases
    assert c in a.bases
    assert len(c.bases) == len(a.bases)
    assert [bas in a.bases for bas in c.bases] == [True]*len(a.bases)

def test_equivalentClass():
    a = URIRef('A')
    b = URIRef('B')
    c = URIRef('C')
    O = Ontology()
    O.equivalentClass(c, a)
    O.equivalentClass(c, b)
    A = O.make_var(ClassDomain, a)
    B = O.make_var(ClassDomain, b)
    assert O.variables[A].values == O.variables[B].values

def test_type():
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef('o')
    O = Ontology()
    O.make_var(ClassDomain, obj)
    O.type(sub, obj)
    
    assert O.variables[O.make_var(None, sub)].__class__  == ClassDomain

def test_ObjectProperty():
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O = Ontology()
    O.type(sub, obj)
    assert O.variables[O.make_var(None, sub)].__class__  == ObjectProperty

def test_range():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef('b')
    O.variables['b_'] = fd([1,2,3,4])
    O.range(sub, obj)
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    assert len(O.constraints) == 1
    O.constraints[0].narrow(O.variables)
    assert O.variables['a_'].range == [1,2,3,4]

def test_merge():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef('b')
    O.variables['b_'] = fd([1,2,3,4])
    O.range(sub, obj)
    obj = URIRef('c')
    O.variables['c_'] = fd([3,4,5,6])
    O.range(sub, obj)
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    assert len(O.constraints) == 2
    O.consistency()
    assert O.variables['a_'].range == [ 3,4]

def test_domain():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef('b')
    O.variables['b_'] = ClassDomain('b')
    O.domain(sub, obj)
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    assert len(O.constraints) == 1
    O.constraints[0].narrow(O.variables)
    assert O.variables['a_'].domain == ['b_']

def test_domain_merge():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef('b')
    O.variables['b_'] = ClassDomain('b')
    O.domain(sub, obj)
    obj = URIRef('c')
    O.variables['c_'] = ClassDomain('c')
    O.domain(sub, obj)
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    
    assert len(O.constraints) == 2
    for con in O.constraints:
        con.narrow(O.variables)
    assert O.variables['a_'].getValues() ==[] #O.variables['b_']

def test_subproperty():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    b = URIRef('b')
    O.type(b, obj)
    O.subPropertyOf(sub, b)
    assert len(O.constraints) ==1
    O.variables['a_'].setValues([('individ_',42)])
    O.consistency()
    for val in O.variables['a_'].getValues():
        assert  val in O.variables['b_'].getValues()

def test_functionalproperty():
    
    O = Ontology()
    #Make functional property
    sub = URIRef('p')
    obj = URIRef(namespaces['owl']+'#FunctionalProperty')
    O.type(sub, obj)
    #Make class
    sub = URIRef('c')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(sub, obj)
    #Make individual with a value of the property
    sub = URIRef('individ')
    obj = URIRef('c')
    O.type(sub, obj)
    O.variables['p_'].setValues([('individ_',42)])
    #assert len(O.constraints) == 2
    #add another valueof the property
    O.variables['p_'].setValues([('individ_',42),('individ_',43)])
    #check that consistency raises
    py.test.raises(ConsistencyFailure, O.consistency)

def test_inversefunctionalproperty():
    
    O = Ontology()
    #Make functional property
    sub = URIRef('p')
    obj = URIRef(namespaces['owl']+'#InverseFunctionalProperty')
    O.type(sub, obj)
    #Make class
    sub = URIRef('c')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(sub, obj)
    #Make individual with a value of the property
    sub = URIRef('individ')
    obj = URIRef('c')
    O.type(sub, obj)
    O.variables['p_'].setValues([('individ_',42)])
    #assert len(O.constraints) == 2
    #add another individual with the same value for the property
    sub = URIRef('individ2')
    obj = URIRef('c')
    O.type(sub, obj)
    O.variables['p_'].setValues([('individ_',42),('individ2_',42)])
    #check that consistency raises
    py.test.raises(ConsistencyFailure, O.consistency)
    
def test_Transitiveproperty():
    
    O = Ontology()
    #Make functional property
    sub = URIRef('subRegionOf')
    obj = URIRef(namespaces['owl']+'#TransitiveProperty')
    O.type(sub, obj)
    #Make class
    sub = URIRef('c')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(sub, obj)
    #Make individual with a value of the property
    sub = URIRef('Italy')
    obj = URIRef('c')
    O.type(sub, obj)
    sub = URIRef('Tuscanny')
    O.type(sub, obj)
    sub = URIRef('Chianti')
    O.type(sub, obj)
    O.variables['subRegionOf_'].setValues([('Italy_','Tuscanny_'),('Tuscanny_','Chianti_')])
    O.consistency()
    assert ('Italy_', 'Chianti_') in O.variables['subRegionOf_'].getValues()
    
def test_symmetricproperty():
    
    O = Ontology()
    #Make functional property
    sub = URIRef('friend')
    obj = URIRef(namespaces['owl']+'#SymmetricProperty')
    O.type(sub, obj)
    assert O.variables[O.make_var(None, sub)].__class__.__name__=='SymmetricProperty'
    #Make class
    sub = URIRef('c')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(sub, obj)
    #Make individual with a value of the property
    sub = URIRef('Bob')
    obj = URIRef('c')
    O.type(sub, obj)
    sub = URIRef('Alice')
    O.type(sub, obj)
    O.variables['friend_'].setValues([('Bob_','Alice_')])
    O.consistency()
    assert ('Alice_', 'Bob_') in O.variables['friend_'].getValues()

def test_inverseof():
    O = Ontology()
    own = URIRef('owner')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(own, obj)
    owned = URIRef('ownedby')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(owned, obj)
    O.inverseOf(own, owned)
    #Make class
    sub = URIRef('c')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(sub, obj)
    #Make individual with a property value
    sub = URIRef('Bob')
    obj = URIRef('c')
    O.type(sub, obj)
    sub = URIRef('Fiat')
    obj = URIRef('car')
    O.type(sub, obj)
    O.variables['owner_'].setValues([('Bob_','Fiat_')])
    py.test.raises(ConsistencyFailure, O.consistency)
    O.variables['ownedby_'].setValues([('Fiat_','Bob_')])
    O.consistency()
    
def no_test_hasvalue():
    O = Ontology()
    own = URIRef('owner')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(own, obj)
    O.hasValue(own, 42)
    py.test.raises(ConsistencyFailure, O.consistency)
    #Make class
    O.variables['owner_'].setValues([('Fiat_', 42)])
    O.consistency()

def test_List():
    O = Ontology()
    own = URIRef('favlist')
    obj = URIRef(namespaces['rdf']+'#List')
    O.type(own, obj)
    O.first(own, 0)
    O.rest(own,  URIRef('1'))
    O.first( URIRef('1'), 1)
    O.rest( URIRef('1'),  URIRef('2'))
    O.first( URIRef('2'), 2)
    O.rest( URIRef('2'),  URIRef(namespaces['rdf']+'#nil'))
    assert len(O.constraints) == 1
    O.consistency(5)
    assert O.rep._domains['favlist_'].getValues() == [0,1,2]
    
def test_oneofrestriction():
    O = Ontology()
    restrict = BNode('anon')
    obj = URIRef(namespaces['owl']+'#Restriction')
    O.type(restrict, obj)
    p = URIRef('p')
    O.onProperty(restrict,p)
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(p, obj)
    p = URIRef('favlist')
    O.oneOf(restrict, p)
    own = URIRef('favlist')
    obj = URIRef(namespaces['rdf']+'#List')
    O.type(own, obj)
    O.first(own, 0)
    O.rest(own,  URIRef('1'))
    O.first( URIRef('1'), 1)
    O.rest( URIRef('1'),  URIRef('2'))
    O.first( URIRef('2'), 2)
    O.rest( URIRef('2'),  URIRef(namespaces['rdf']+'#nil'))
    own = URIRef('class')
    obj = URIRef(namespaces['rdf']+'#Class')
    O.type(own, obj)
    O.subClassOf(own,restrict)
    py.test.raises(ConsistencyFailure, O.consistency)

def test_oneofclassenumeration():
    O = Ontology()
    restrict = BNode('anon')
    own = URIRef('favlist')
    obj = URIRef(namespaces['rdf']+'#List')
    O.type(own, obj)
    O.first(own, URIRef('first'))
    O.rest(own,  URIRef('1'))
    O.first( URIRef('1'), URIRef('second'))
    O.rest( URIRef('1'),  URIRef('2'))
    O.first( URIRef('2'), URIRef('third'))
    O.rest( URIRef('2'),  URIRef(namespaces['rdf']+'#nil'))
    O.oneOf(restrict, own)
    O.type(restrict, namespaces['owl']+'#Class')
    O.consistency(4)
    assert len(O.rep._domains[restrict].getValues()) == 3