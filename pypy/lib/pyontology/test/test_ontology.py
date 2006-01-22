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

def rdf_list(ont, name, data):
    owllist = URIRef(name)
    obj = URIRef(namespaces['rdf']+'#List')
    ont.type(owllist, obj)
    own =owllist
    for i,dat in enumerate(data[:-1]):
        next = URIRef( name + str(i))
        print next,i,dat,own
        ont.first(own, dat)
        ont.rest(own,  next)
        own = next
    ont.first(own, data[-1])
    ont.rest(own,  URIRef(namespaces['rdf']+'#nil'))
    return owllist

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
    a = URIRef(u'A')
    b = URIRef(u'B')
    c = URIRef(u'C')
    O.subClassOf(b, a)
    O.subClassOf(c, b)
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(a,obj)
    O.consistency()
    O.consistency()
    assert len(O.variables) == 3
    assert 'C_' in O.variables['A_'].getValues()

def no_test_ClassDomain():
    a = ClassDomain()
    cls =  1
    b = ClassDomain('B',[],[a])
    assert b in b.getValues()
    assert a in b.getValues()

def test_subClassconstraint():
    a = ClassDomain('A')
    b = ClassDomain('B')
    c = ClassDomain('C')
    con = SubClassConstraint('b','a')
    con2 = SubClassConstraint('c','b')
    con.narrow({'a': a, 'b': b, 'c': c}) 
    con2.narrow({'a': a, 'b': b, 'c': c})
    con.narrow({'a': a, 'b': b, 'c': c}) 
    assert 'b' in a.getValues()
    assert 'c' in a.getValues()

def test_subClassconstraintMulti():
    a = ClassDomain('A')
    b = ClassDomain('B')
    c = ClassDomain('C')
    con = SubClassConstraint('c','a')
    con2 = SubClassConstraint('c','b')
    con.narrow({'a': a, 'b': b, 'c': c}) 
    con2.narrow({'a': a, 'b': b, 'c': c})
    assert 'c' in a.getValues()
    assert 'c' in b.getValues()

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
    assert 'c' in a.getValues()
    assert 'c' in b.getValues()
    assert 'a' in c.getValues()

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
    
def test_hasvalue():
    O = Ontology()
    restrict = BNode('anon1')
    obj = URIRef(namespaces['owl']+'#Restriction')
    O.type(restrict, obj)
    p = URIRef('p')
    O.onProperty(restrict,p)
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(p, obj)
    O.hasValue(restrict, 2)
    cls = URIRef('class')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(cls, obj)
    O.subClassOf(cls,restrict)
    O.variables['p_'].setValues([(cls,1)])
    py.test.raises(ConsistencyFailure, O.consistency)

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
    own = rdf_list(O, 'favlist', [0, 1, 2])
    own = URIRef('class')
    obj = URIRef(namespaces['rdf']+'#Class')
    O.type(own, obj)
    O.subClassOf(own,restrict)
    py.test.raises(ConsistencyFailure, O.consistency)

def test_oneofclassenumeration():
    O = Ontology()
    restrict = BNode('anon')
    own = rdf_list(O, 'favlist', ['first', 'second', 'third'])
    O.oneOf(restrict, own)
    O.type(restrict, namespaces['owl']+'#Class')
    O.consistency(4)
    print O.rep._domains
    assert len(O.rep._domains[restrict].getValues()) == 3

def test_oneofdatarange():
    O = Ontology()
    restrict = BNode('anon')
    own = rdf_list(O, 'favlist', ['1','2','3'])
    O.oneOf(restrict, own)
    O.type(restrict, namespaces['owl']+'#DataRange')
    O.consistency(4)
    print O.rep._domains
    assert len(O.rep._domains[restrict].getValues()) == 3

def test_somevaluesfrom_datarange():
    O = Ontology()
    datarange = BNode('anon')
    own = rdf_list(O, 'favlist', ['1','2','3'])
    O.oneOf(datarange, own)
    O.type(datarange, namespaces['owl']+'#DataRange')
    restrict = BNode('anon1')
    obj = URIRef(namespaces['owl']+'#Restriction')
    O.type(restrict, obj)
    p = URIRef('p')
    O.onProperty(restrict,p)
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(p, obj)
    O.someValuesFrom(restrict, datarange)
    cls = URIRef('class')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(cls, obj)
    O.subClassOf(cls,restrict)
    O.variables['p_'].setValues([(cls,1)])
    py.test.raises(ConsistencyFailure, O.consistency)

def test_allvaluesfrom_datarange():
    O = Ontology()
    datarange = BNode('anon')
    own = rdf_list(O, 'favlist', ['1','2','3'])
    O.oneOf(datarange, own)
    O.type(datarange, namespaces['owl']+'#DataRange')
    restrict = BNode('anon1')
    obj = URIRef(namespaces['owl']+'#Restriction')
    O.type(restrict, obj)
    p = URIRef('p')
    O.onProperty(restrict,p)
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(p, obj)
    O.allValuesFrom(restrict, datarange)
    cls = URIRef('class')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(cls, obj)
    O.subClassOf(cls,restrict)
    O.variables['p_'].setValues([(cls,1)])
    py.test.raises(ConsistencyFailure, O.consistency)

def test_unionof():
    O = Ontology()
    cls = BNode('anon')
    own1 = BNode('liist1')
    own2 = BNode('liist2')
    list1 = rdf_list(O, 'favlist1', ['1', '2', '3'])
    list2 = rdf_list(O, 'favlist2', ['3', '4', '5'])
    own = rdf_list(O, 'favlist', [own1, own2])
    O.oneOf( own1, list1)
    O.oneOf( own2, list2)
    O.unionOf(cls, own)
    O.type(cls, namespaces['owl']+'#Class')
    O.consistency(3)
    assert O.rep._domains[cls].getValues() == ['1', '2', '3', '4', '5']

def test_intersectionof():
    O = Ontology()
    cls = BNode('anon')
    own1 = BNode('liist1')
    own2 = BNode('liist2')
    list1 = rdf_list(O, 'favlist1', ['1', '2', '3'])
    list2 = rdf_list(O, 'favlist2', ['3', '4', '5'])
    own = rdf_list(O, 'favlist', [own1, own2])
    O.oneOf( own1, list1)
    O.oneOf( own2, list2)
    O.intersectionOf(cls, own)
    O.type(cls, namespaces['owl']+'#Class')
    O.consistency(3)
    assert O.rep._domains[cls].getValues() == ['3']

def test_differentfrom():
    O = Ontology()
    cls = BNode('anon')
    own1 = BNode('liist1')
    own2 = BNode('liist2')
    O.differentFrom(cls, own1)
    O.differentFrom(own1, own2)
    O.differentFrom(cls, own2)
    O.differentFrom(own2,cls)
    O.type(cls, namespaces['owl']+'#Thing')
    O.type(own1, namespaces['owl']+'#Thing')
    O.type(own2, namespaces['owl']+'#Thing')
    O.consistency(3)
    assert len(O.rep._constraints) == 4

def test_differentfromconsistency():
    O = Ontology()
    cls = BNode('anon')
    O.differentFrom(cls, cls)
    O.type(cls, namespaces['owl']+'#Thing')
    py.test.raises(ConsistencyFailure, O.consistency, 3)

def test_sameas():
    O = Ontology()
    cls = BNode('anon')
    own1 = BNode('liist1')
    own2 = BNode('liist2')
    O.sameAs(cls, own1)
    O.sameAs(own1, own2)
    O.sameAs(cls, own2)
    O.type(cls, namespaces['owl']+'#Thing')
    O.type(own1, namespaces['owl']+'#Thing')
    O.type(own2, namespaces['owl']+'#Thing')
    sub = URIRef('a')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    O.variables[O.make_var(None,sub)].setValues([(cls,'1')])
    O.consistency(3)
#    assert len(O.rep._constraints) == 4
    assert ('_liist1','1') in O.rep._domains[O.make_var(None,sub)].getValues()

def test_sameasconsistency():
    O = Ontology()
    cls = BNode('anon')
    own1 = BNode('liist1')
    O.sameAs(cls, own1)
    O.type(cls, namespaces['owl']+'#Thing')
    O.type(own1, namespaces['owl']+'#Thing')
    sub = URIRef('a')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    O.variables[O.make_var(None,sub)].setValues([(cls,'1'), (own1,'2')])
    print O.variables
    for dom in O.variables.values() :print type(dom)
    py.test.raises(ConsistencyFailure, O.consistency, 3)


