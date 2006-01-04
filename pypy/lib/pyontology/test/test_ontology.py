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
    assert O.make_var(ClassDomain, var) in locals() 
    assert isinstance(O.variables[name], ClassDomain)
     
def test_subClassof():
    O = Ontology()
    a = URIRef(u'http://www.w3.org/2002/03owlt/unionOf/premises004#A')
    b = URIRef(u'http://www.w3.org/2002/03owlt/unionOf/premises004#B')
    c = URIRef(u'http://www.w3.org/2002/03owlt/unionOf/premises004#C')
    O.subClassOf(b, None, a)
    O.subClassOf(c, None, b)
    A = O.make_var(ClassDomain, a)
    C = O.make_var(ClassDomain, c)
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
    O.equivalentClass(c, None, a)
    O.equivalentClass(c, None, b)
    A = O.make_var(ClassDomain, a)
    B = O.make_var(ClassDomain, b)
    assert O.variables[A].values == O.variables[B].values

def test_type():
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef('o')
    O = Ontology()
    O.type(sub, pred , obj)
    assert O.variables[O.make_var(ClassDomain, sub)].__class__  == ClassDomain

def test_ObjectProperty():
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O = Ontology()
    O.type(sub, pred , obj)
    assert O.variables[O.make_var(ClassDomain, sub)].__class__  == ObjectProperty

def test_range():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef('b')
    O.variables['b_'] = fd([1,2,3,4])
    O.range(sub, None , obj)
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, pred , obj)
    assert len(O.constraints) == 1
    O.constraints[0].narrow(O.variables)
    assert O.variables['a_'].getValues() == ((None,[1,2,3,4]),)

def test_merge():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef('b')
    O.variables['b_'] = fd([1,2,3,4])
    O.range(sub, None , obj)
    obj = URIRef('c')
    O.variables['c_'] = fd([3,4,5,6])
    O.range(sub, None , obj)
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, pred , obj)
    assert len(O.constraints) == 2
    O.consistency()
    assert O.variables['a_'].getValues() == ((None, [3,4]),)

def test_domain():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef('b')
    O.variables['b_'] = ClassDomain('b')
    O.domain(sub, None , obj)
    sub = URIRef('a')
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, pred , obj)
    assert len(O.constraints) == 1
    O.constraints[0].narrow(O.variables)
    assert O.variables['a_'].getValues() == ((O.variables['b_'], [None]),)

def test_domain_merge():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef('b')
    O.variables['b_'] = ClassDomain('b')
    O.domain(sub, None , obj)
    obj = URIRef('c')
    O.variables['c_'] = ClassDomain('c')
    O.domain(sub, None , obj)
    pred = URIRef('type')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, pred , obj)
    
    assert len(O.constraints) == 2
    for con in O.constraints:
        con.narrow(O.variables)
    assert O.variables['a_'].getValues() ==() #O.variables['b_']

def test_subproperty():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, None, obj)
    b = URIRef('b')
    O.type(b, None, obj)
    O.subPropertyOf(sub, None, b)
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
    O.type(sub, None, obj)
    #Make class
    sub = URIRef('c')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(sub, None, obj)
    #Make individual with a value of the property
    sub = URIRef('individ')
    obj = URIRef('c')
    O.type(sub, None, obj)
    O.variables['p_'].setValues([('individ_',42)])
    assert len(O.constraints) == 2
    #add another valueof the property
    O.variables['p_'].setValues([('individ_',42),('individ_',43)])
    #check that consistency raises
    py.test.raises(ConsistencyFailure, O.consistency)

def test_inversefunctionalproperty():
    
    O = Ontology()
    #Make functional property
    sub = URIRef('p')
    obj = URIRef(namespaces['owl']+'#InverseFunctionalProperty')
    O.type(sub, None, obj)
    #Make class
    sub = URIRef('c')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(sub, None, obj)
    #Make individual with a value of the property
    sub = URIRef('individ')
    obj = URIRef('c')
    O.type(sub, None, obj)
    O.variables['p_'].setValues([('individ_',42)])
    assert len(O.constraints) == 2
    #add another individual with the same value for the property
    sub = URIRef('individ2')
    obj = URIRef('c')
    O.type(sub, None, obj)
    O.variables['p_'].setValues([('individ2_',42)])
    #check that consistency raises
    py.test.raises(ConsistencyFailure, O.consistency)
    
def test_Transitiveproperty():
    
    O = Ontology()
    #Make functional property
    sub = URIRef('subRegionOf')
    obj = URIRef(namespaces['owl']+'#TransitiveProperty')
    O.type(sub, None, obj)
    #Make class
    sub = URIRef('c')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(sub, None, obj)
    #Make individual with a value of the property
    sub = URIRef('Italy')
    obj = URIRef('c')
    O.type(sub, None, obj)
    sub = URIRef('Tuscanny')
    O.type(sub, None, obj)
    sub = URIRef('Chianti')
    O.type(sub, None, obj)
    O.variables['subRegionOf_'].setValues([('Italy_','Tuscanny_'),('Tuscanny_','Chianti_')])
    O.consistency()
    assert ('Italy_', ['Tuscanny_', 'Chianti_']) in O.variables['subRegionOf_'].getValues()