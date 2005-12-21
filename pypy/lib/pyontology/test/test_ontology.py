# tests for the Ontology class

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

