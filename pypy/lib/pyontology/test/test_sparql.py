
try:
    import pyparsing
    import rdflib
except ImportError:
    from py.test import skip
    skip("Pyparsing or Rdflib not installed")

from pypy.lib.pyontology.sparql_grammar import SPARQLGrammar as SP
from pypy.lib.pyontology.pyontology import Ontology, ConsistencyFailure
import py

qt = """
         PREFIX ns: <http://example.org/ns#>

         SELECT ?x ?y
         WHERE {
                 ?x ns:p 123 .
                 ?y ns:q 'a123' .
                 FILTER ( ?x < 2 )
               }
         """

def test_simple():
    query = SP.Query.parseString(qt)[0]
    assert query.PrefixDecl[0].ns == 'http://example.org/ns#'
    where = query.SelectQuery[0].WhereClause[0]
    assert len(where) == 1
    triples = where.GroupGraphPattern[0].Triples
    assert len(triples) == 2
#    assert triples[0][0].getName() == 'VAR1' 
#    assert triples[1][0].getName() == 'VAR1' 
    assert triples[1][0].VAR1[0][0] == 'x' 
    assert triples[0][0].VAR1[0][0] == 'y' 
    assert triples[1][1][0].asList() == ['ns', 'p'] 
    assert triples[0][1][0].asList() == ['ns', 'q'] 
    assert triples[1][2][0] == '123'
    assert type(triples[1][2][0]) == rdflib.Literal
    vars = query.SelectQuery[0].VAR1
    assert len(vars) == 2
    assert 'x' in vars[0][0]
    assert 'y' in vars[1][0]


def test_sparql():
    n = Ontology()
    result = n._sparql(qt)
    res = result[0]
    assert len(res) == 2
    assert len(res[0]) == len(res[1]) == 4
    assert res[0][1] in ['http://example.org/ns#p', 'http://example.org/ns#q']
    assert res[1][1] in ['http://example.org/ns#p', 'http://example.org/ns#q']
    assert result[3][0] == 'x<2'

# There are 8 ways of having the triples in the query, if predicate is not a builtin owl predicate
#
#   s               p               o
#
#   bound           bound           bound  ; Check if this triple entails
#   var             bound           bound  ; add a hasvalue constraint
#   bound           var             bound  ; for all p's return p if p[0]==s and p[1]==o 
#   bound           bound           var    ; search for s in p
#   var             var             bound  ; for all p's return p[0] if p[1]==o 
#   var             bound           var    ; return the values of p
#   bound           var             var    ; for all p's return p[1] if p[0]==s
#   var             var             var    ; for all p's return p.getvalues
#
# If p is a builtin owl property
Onto = """<rdf:RDF
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:owl="http://www.w3.org/2002/07/owl#"
      xmlns:ns="http://example.org/ns#"
      xmlns:base="http://example.org/ns#">

<owl:Class rdf:about="http://www.w3.org/2002/07/owl#Thing">
        <owl:oneOf rdf:parseType="Collection">
            <owl:Thing rdf:about="#s"/>
       </owl:oneOf>
      </owl:Class>
    <owl:Thing rdf:about="http://example.org/ns#sub">
        <ns:p rdf:datatype=
        "http://www.w3.org/2001/XMLSchema#int">123</ns:p>
    </owl:Thing>
    <owl:ObjectProperty rdf:about="http://example.org/ns#p" />
  </rdf:RDF>
    """

qt_proto = """
        PREFIX ns: <http://example.org/ns#>
        SELECT %s
        WHERE {
                %s 
              }
                                                                                          """
from StringIO import StringIO

def test_case_0():
    """ Check if the triple is entailed """
    py.test.skip("Doesn't work yet")

    query = qt_proto % ('?x', 'ns:sub ns:p 123 .')
    O = Ontology()
    O.add_file(StringIO(Onto))
    raises(ConsistencyFailure, O.sparql, query)

def test_case_1():
    #""" add a hasvalue constraint """

    query = qt_proto % ('?x', '?x ns:p 123 .')
    O = Ontology()
    O.add_file(StringIO(Onto))
    O.attach_fd()
    O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0].uri == u'http://example.org/ns#sub' 

def test_case_2():
    "for all p's return p if p[0]==s and p[1]==o """

    query = qt_proto % ('?x', 'ns:sub  ?x 123 .')
    O = Ontology()
    O.add_file(StringIO(Onto))
    O.attach_fd()

    O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0] == 'ns_p' 

def test_case_3():
    """search for s in p"""

    query = qt_proto % ('?x', 'ns:sub ns:p ?x .')
    O = Ontology()
    O.add_file(StringIO(Onto))

    O.attach_fd()

    O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0] == '123' 

def test_case_4():
    """ search for s in p """
    py.test.skip("Doesn't work yet")

    query = qt_proto % ('?x ?y', '?x ?y 123 .')
    O = Ontology()
    O.add_file(StringIO(Onto))
    O.attach_fd()

    O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0].uri == u'http://example.org/ns#sub' 

def test_case_5():
    """ for all p's return p[0] if p[1]==o """

    query = qt_proto % ('?x ?y', '?x ns:p ?y .')
    O = Ontology()
    O.add_file(StringIO(Onto))
    O.attach_fd()

    O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0].uri == u'http://example.org/ns#sub' 
    assert list(O.variables['query_y_'].getValues())[0] == u'123' 

def test_case_6():
    """ return the values of p """
    py.test.skip("Doesn't work yet")

    query = qt_proto % ('?x ?y', 'ns:sub ?x ?y .')
    O = Ontology()
    O.add_file(StringIO(Onto))
    O.attach_fd()

    O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0].uri == u'http://example.org/ns#sub' 

def test_case_7():
    """ for all p's return p[1] if p[0]==s """
    py.test.skip("Doesn't work yet")

    query = qt_proto % ('?x ?y ?z', '?x ?y ?z .')
    O = Ontology()
    O.add_file(StringIO(Onto))
    O.attach_fd()

    O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0].uri == u'http://example.org/ns#sub' 



