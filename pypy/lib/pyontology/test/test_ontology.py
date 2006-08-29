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

UR = URIRef
def rdf_list(ont, name, data):
    owllist = URIRef(name)
    obj = URIRef(namespaces['rdf']+'#List')
    ont.type(owllist, obj)
    own =owllist
    for i,dat in enumerate(data[:-1]):
        next = BNode( name + str(i))
        next,i,dat,own
        ont.first(own, dat)
        ont.type(next, obj)
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
#    assert len(O.variables) == 4
    assert 'A_' in O.variables['C_'].bases

def test_addvalue():
    O = Ontology()
    a = O.make_var(Property, URIRef('a'))
    O.variables[a].addValue('key', 42)
    assert O.variables[a].getValues() == [('key', 42)]
    O.variables[a].addValue('key', 43)
    assert O.variables[a].getValues() == [('key', 42), ('key', 43)]

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
    O = Ontology()
    a = O.make_var(ClassDomain,URIRef('A'))
    b = O.make_var(ClassDomain,URIRef('B'))
    c = O.make_var(ClassDomain,URIRef('C'))
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
    
    assert O.variables[O.make_var(None, sub)].__class__  == Individual 

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
    O.variables['b_'] = ClassDomain(values=[1,2,3,4])
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
    O.variables['b_'] = ClassDomain(values=[1,2,3,4])
    O.range(sub, obj)
    obj = URIRef('c')
    O.variables['c_'] = ClassDomain(values=[3,4,5,6])
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
    assert O.variables['a_'].getValues() ==[] 

def test_subproperty():
    O = Ontology()
    sub = URIRef('a')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    b = URIRef('b')
    O.type(b, obj)
    O.variables['a_'].setValues([('individ_',42)])
    O.subPropertyOf(sub, b)
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
    O.variables['p_'].setValues([('individ',42)])
    #add another valueof the property
    O.variables['p_'].addValue('individ',43)
    py.test.raises(ConsistencyFailure, O.consistency )
    #check that consistency raises

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
    py.test.raises(ConsistencyFailure, O.variables['p_'].setValues, [('individ_',42),('individ2_',42)])
    
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
    assert 'Chianti_' in O.variables['subRegionOf_']._dict['Italy_']
    
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
    O.inverseOf(own, owned)
    O.consistency()
    assert ('Fiat_','Bob_') in O.variables['ownedby_'].getValues()   
    
def test_hasvalue():
  #  py.test.skip("")
    O = Ontology()
    cls = URIRef('class')
    obj = URIRef(namespaces['owl']+'#Thing')
    O.type(cls, obj)
    restrict = BNode('anon1')
    obj = URIRef(namespaces['owl']+'#Restriction')
    O.type(restrict, obj)
    p = URIRef('p')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(p, obj)
    O.consider_triple((cls, p, 2))
    O.onProperty(restrict,p)
    O.consider_triple((cls, p, 1))
    O.hasValue(restrict, 2)
#    O.type(2, URIRef(namespaces['owl']+'#Thing'))
#    O.type(1, URIRef(namespaces['owl']+'#Thing'))
    
    cls2 = URIRef('class2')
    obj = URIRef(namespaces['owl']+'#Thing')
    O.type(cls2, obj)
    O.subClassOf(cls2,restrict)
    O.variables[O.make_var(None, cls2)].finish(O.variables, O.constraints) 
    O.consistency()
    assert cls in O.variables[O.make_var(None, cls2)].getValues()
#    py.test.raises(ConsistencyFailure, O.consistency)

def test_List():
    py.test.skip("Need to be rewritten using RDF-XML")
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
    O.flatten_rdf_list(own)
    O.consistency()
    assert O.rep._domains['favlist_'].getValues() == [0,1,2]

def test_oneofclassenumeration():
    O = Ontology()
    restrict = BNode('anon')
    own = [UR('first'), UR('second'), UR('third')]
    O.oneOf(restrict, own)
    O.type(restrict, UR(namespaces['owl']+'#Class'))
    O.consistency()
    assert len(O.rep._domains[restrict].getValues()) == 3
    assert set(O.rep._domains[restrict].getValues()) == set(own)

def test_unification_of_two_oneofclassenumeration():
    O = Ontology()
    restrict = BNode('anon')
    own = [UR('first'), UR('second'), UR('third')]
    for i in own:
        O.type(i,UR(namespaces['owl']+'#Thing'))
    O.oneOf(restrict, own)
    restrict1 = BNode('anon1')
    own = [UR('second'), UR('third'), UR('first')]
    O.oneOf(restrict1, own)
    O.type(UR('test'), UR(namespaces['owl']+'#Thing'))
    O.type(UR('test'), restrict)
    O.type(UR('test'), restrict1)
    O.consistency()
    assert len(O.rep._domains[restrict].getValues()) == 3
    assert set(O.rep._domains[restrict].getValues()) == set(own)


def test_oneofdatarange():
    O = Ontology()
    restrict = BNode('anon')
    own = ['1','2','3'] 
    O.oneOf(restrict, own)
    O.type(restrict, UR(namespaces['owl']+'#DataRange'))
    O.consistency()
    assert len(O.rep._domains[restrict].getValues()) == 3
    assert set(O.rep._domains[restrict].getValues()) == set(own)

def test_somevaluesfrom_datarange():
    py.test.skip("reconsider if the test is correct - make it simpler")
    O = Ontology()
    datarange = BNode('anon')
    own =  ['1','2','3']
    O.oneOf(datarange, own)
    O.type(datarange, namespaces['owl']+'#DataRange')
    restrict = BNode('anon1')
    obj = URIRef(namespaces['owl']+'#Restriction')
    O.type(restrict, obj)
    p = URIRef('p')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(p, obj)
    cls = URIRef('class')
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(cls, obj)
    O.variables['p_'].setValues([(cls,'1')])
    O.onProperty(restrict,p)
    O.someValuesFrom(restrict, datarange)
    O.subClassOf(cls,restrict)
    O.consistency()
    assert cls in O.variables[O.make_var(None, cls)].getValues()

def test_allvaluesfrom_datarange():
    py.test.skip("")
    O = Ontology()
    datarange = BNode('anon')
    own = ['1','2','3']
    O.oneOf(datarange, own)
    O.type(datarange, namespaces['owl']+'#DataRange')
    restrict = BNode('anon1')
    obj = URIRef(namespaces['owl']+'#Restriction')
    O.type(restrict, obj)
    p = URIRef('p')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(p, obj)
    cls = URIRef('class')
    O.variables['p_'].setValues([(cls,'1'),(cls,'2'),(cls,'3')])
    obj = URIRef(namespaces['owl']+'#Class')
    O.type(cls, obj)
    O.onProperty(restrict,p)
    O.allValuesFrom(restrict, datarange)
    O.subClassOf(cls,restrict)
    assert cls in O.variables[O.make_var(None, cls)].getValues()

def test_unionof():
    py.test.skip("Rewrite the test")
    O = Ontology()
    cls = BNode('anon')
    own1 = BNode('liist1')
    own2 = BNode('liist2')
    list1 =  ['1', '2', '3'] 
    list2 =  ['3', '4', '5'] 
    own = [list1, list2] 
    O.oneOf( own1, list1)
    O.oneOf( own2, list2)
    O.unionOf(cls, own)
    O.type(cls, namespaces['owl']+'#Class')
    O.consistency()
    res = O.rep._domains[cls].getValues()
    res.sort()
    assert res == ['1', '2', '3', '4', '5']

def test_intersectionof():
    py.test.skip("Rewrite the test")
    O = Ontology()
    cls = BNode('anon')
    O.intersectionOf(cls, [['1','2','3'],['3','4','5']])
    O.type(cls, namespaces['owl']+'#Class')
    O.consistency()
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
    O.type(cls, UR(namespaces['owl']+'#Thing'))
    O.type(own1, UR(namespaces['owl']+'#Thing'))
    O.type(own2, UR(namespaces['owl']+'#Thing'))
    O.consistency()
    assert len(O.rep._constraints) == 4

def test_differentfromconsistency():
    O = Ontology()
    cls = BNode('anon')
    O.differentFrom(cls, cls)
    O.type(cls, UR(namespaces['owl']+'#Thing'))
    py.test.raises(ConsistencyFailure, O.consistency)

def test_sameas():
    O = Ontology()
    cls = BNode('anon')
    own1 = BNode('liist1')
    own2 = BNode('liist2')
    O.sameAs(cls, own1)
    O.sameAs(own1, own2)
    O.sameAs(cls, own2)
    O.type(cls, UR(namespaces['owl']+'#Thing'))
    O.type(own1, UR(namespaces['owl']+'#Thing'))
    O.type(own2, UR(namespaces['owl']+'#Thing'))
    sub = URIRef('a')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    O.variables[O.make_var(None,sub)].setValues([(cls,'1')])
    O.consistency()
    assert ('liist1','1') in O.rep._domains[O.make_var(None,sub)].getValues()

def test_sameasconsistency():
    O = Ontology()
    cls = BNode('anon')
    own1 = BNode('liist1')
    O.sameAs(cls, own1)
    O.type(cls, UR(namespaces['owl']+'#Thing'))
    O.type(own1, UR(namespaces['owl']+'#Thing'))
    sub = URIRef('a')
    obj = URIRef(namespaces['owl']+'#ObjectProperty')
    O.type(sub, obj)
    O.variables[O.make_var(None,sub)].setValues([(cls,'1'), (own1,'2')])
    py.test.raises(ConsistencyFailure, O.consistency)


def test_terminology_cardinality():
    # Modeled after one of the standard tests (approved/maxCardinality)
    # 'cls' by subclassing two maxCardinality restrictions becomes the set of
    # individuals satisfying both restriction, ie having exactly 2 values of
    # predicate p
    cls = URIRef('cls')
    O = Ontology()
    O.add((cls, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#Class')))
    p = O.make_var(Property,URIRef('p'))
    p = URIRef('p')
    O.add((p, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#ObjectProperty')))

    restr = BNode('anon')
    O.add((restr, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#Restriction') ))
    O.add((restr, UR(namespaces['rdfs']+'#onProperty'), p ))
    O.add((cls, UR(namespaces['rdfs']+'#subClassOf'),restr ))
    O.add((restr, UR(namespaces['rdfs']+'#maxCardinality'), 2 ))

    restr2 = BNode('anon2')
    O.add((restr2, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#Restriction') ))
    O.add((restr2, UR(namespaces['rdfs']+'#onProperty'), p ))
    O.add((cls, UR(namespaces['rdfs']+'#subClassOf'),restr2 ))
    O.add((restr2, UR(namespaces['rdfs']+'#minCardinality'), 3 ))
    O.attach_fd()
    for var in O.variables.values():
        var.finish(O.variables, O.constraints)
    py.test.raises(ConsistencyFailure, O.consistency)

def test_terminology_subclassof_cardinality():
    cls = URIRef('cls')
    cls2 = URIRef('cls2')
    O = Ontology()
    O.add((cls, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#Class')))
    O.add((cls2, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#Class')))
    p = O.make_var(Property,URIRef('p'))
    p = URIRef('p')
    O.add((p, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#ObjectProperty')))

    restr = BNode('anon')
    O.add((restr, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#Restriction')))
    O.add((restr, UR(namespaces['rdfs']+'#onProperty'), p ))
    O.add((cls, UR(namespaces['rdfs']+'#subClassOf'),restr ))
    O.add((restr, UR(namespaces['rdfs']+'#maxCardinality'), 2 ))

    restr2 = BNode('anon2')
    O.add((restr2, UR(namespaces['rdfs']+'#type'), UR(namespaces['owl']+'#Restriction')))
    O.add((restr2, UR(namespaces['rdfs']+'#onProperty'), p ))
    O.add((cls, UR(namespaces['rdfs']+'#subClassOf'),restr2 ))
    O.add((restr2, UR(namespaces['rdfs']+'#minCardinality'), 3 ))
    O.add((cls2, UR(namespaces['rdfs']+'#subClassOf'), cls ))
    O.attach_fd()
    for var in O.variables.values():
        var.finish(O.variables, O.constraints)
    py.test.raises(ConsistencyFailure, O.consistency)
    
def test_add_file():
    O = Ontology()
    O.add_file('premises001.rdf')
    trip = list(O.graph.triples((None,)*3))
#    O.attach_fd()
    ll = len(O.variables)
    l = len(trip)
    O.add_file('conclusions001.rdf')
    O.attach_fd()
    lll = len(O.variables)
    assert len(list(O.graph.triples((None,)*3))) > l

def test_more_cardinality():
    O = Ontology()
    O.add_file('premises003.rdf')
    trip = list(O.graph.triples((None,)*3))
 #   O.attach_fd()
    ll = len(O.variables)
    l = len(trip)
    O.add_file('conclusions003.rdf')
    O.attach_fd()
    O.consistency()
    lll = len(O.variables)
    assert len(list(O.graph.triples((None,)*3))) > l

def test_allvalues_file():
    O = Ontology()
    O.add_file('approved/allValuesfrom/premises002.rdf')
    O.add_file('approved/allValuesfrom/nonconclusions002.rdf')
    
def test_import():
    O = Ontology()
    s = URIRef('s')
    O.imports(s,URIRef('http://www.w3.org/2002/03owlt/imports/support001-A'))

def test_complementof():
    O = Ontology()
    a_cls = URIRef('a')
    b_cls = URIRef('b')
    O.type(a_cls, URIRef(namespaces['owl']+'#Class'))
    O.type(b_cls, URIRef(namespaces['owl']+'#Class'))
    O.oneOf(a_cls, [URIRef('i1'), URIRef('i2'), URIRef('i3'), URIRef('i4')])
    for i in ['i1', 'i2', 'i3', 'i4']: 
        O.type(URIRef(i), URIRef(namespaces['owl']+'#Thing'))
    O.type(URIRef('i5'), URIRef(namespaces['owl']+'#Thing'))
    O.complementOf(b_cls, a_cls)
    O.consistency()
    assert O.variables[O.make_var(None, b_cls)].getValues() == ['i5']

def test_complementof_raise():
    O = Ontology()
    a_cls = URIRef('a')
    b_cls = URIRef('b')
    O.type(a_cls, URIRef(namespaces['owl']+'#Class'))
    O.type(b_cls, URIRef(namespaces['owl']+'#Class'))
    O.oneOf(a_cls, [URIRef('i1'), URIRef('i2'), URIRef('i3'), URIRef('i4')])
    for i in ['i1', 'i2', 'i3', 'i4']: 
        O.type(URIRef(i), URIRef(namespaces['owl']+'#Thing'))
    O.type(URIRef('i5'), URIRef(namespaces['owl']+'#Thing'))
    O.type(URIRef('i4'), b_cls)
    O.type(URIRef('i4'), a_cls)
    O.complementOf(b_cls, a_cls)
    # The above ontology states that 'b' is complement of 'a'. But that leads
    # to an inconsistency as 'i4' is of type 'a' and 'b'
    raises(ConsistencyFailure, O.consistency)

def test_class_promotion():
    O = Ontology()
    a_cls = URIRef('a')
    O.type(a_cls, URIRef(namespaces['owl']+'#Class'))

    assert isinstance(O.variables['a_'], ClassDomain)   
    O.type(a_cls, URIRef(namespaces['owl']+'#Restriction'))
    assert isinstance(O.variables['a_'], Restriction)   

def test_class_demotion():
    O = Ontology()
    a_cls = URIRef('a')
    O.type(a_cls, URIRef(namespaces['owl']+'#Restriction'))
    O.variables[O.make_var(None, a_cls)].property = "SomeProp"
    assert isinstance(O.variables['a_'], Restriction)   

    O.type(a_cls, URIRef(namespaces['owl']+'#Class'))

    assert isinstance(O.variables['a_'], Restriction)   
    assert O.variables[O.make_var(None, a_cls)].property == "SomeProp"

def test_property_to_objectproperty():
    O = Ontology()
    a_cls = URIRef('a')
    O.type(a_cls, URIRef(namespaces['rdf']+'#Property'))
    assert isinstance(O.variables['a_'], Property)      
    O.type(a_cls, URIRef(namespaces['owl']+'#ObjectProperty'))
    assert isinstance(O.variables['a_'], Property)      

    O.type(a_cls, URIRef(namespaces['rdf']+'#Property'))

    assert isinstance(O.variables['a_'], ObjectProperty)        

def test_individual():
    # test comparison (unknown, equal, different)
    O = Ontology()
    first = URIRef('first')
    second = URIRef('second')
    O.type(first, URIRef(namespaces['owl']+'#Thing'))
    assert isinstance((O.variables['owl_Thing'].getValues()[0]), Individual)
