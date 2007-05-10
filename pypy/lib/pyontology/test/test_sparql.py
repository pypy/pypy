import py
try:
    import pyparsing
    import rdflib
except ImportError:
    from py.test import skip
    skip("Pyparsing or Rdflib not installed")

from pypy.lib.pyontology.sparql_grammar import SPARQLGrammar as SP
from pypy.lib.pyontology.pyontology import Ontology, ConsistencyFailure
import datetime

import os
import pypy.lib.pyontology
DATAPATH = os.path.join(os.path.split(pypy.lib.pyontology.__file__)[0], 'test')

def datapath(name):
    """
    Making the tests location independent:
    We need to turn the file name into an URL, or the drive letter
    would be misinterpreted as protocol on windows.
    Instead of a plain file name, we pass an open URL.
    But careful, URLs don't have a seek method, so we need to avoid
    inspection of the beginning of the file by passing the file type
    'xml' explicitly.
    """
    from urllib import urlopen, pathname2url
    url = pathname2url(os.path.join(DATAPATH, name))
    return urlopen(url)


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
    query = SP.Query.parseString(qt)
    assert query.Prefix[0]['ns'] == 'http://example.org/ns#'
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
   # assert result[3].formula == 'query_x<2'
    assert (['query_x<2'], {}).formula == 'query_x<2'

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

    query = qt_proto % ('?x', 'ns:sub ns:p "a123" .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')
    O.attach_fd()
    raises(ConsistencyFailure, O.sparql, query)

def test_case_1():
    #""" add a hasvalue constraint """

    query = qt_proto % ('?x', '?x ns:p 123 .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')
    O.attach_fd()
    O.finish()
    res = O.sparql(query)
    assert len(res) == 1
    assert res[0]['x'] == u'http://example.org/ns#sub' 

def test_case_2():
    "for all p's return p if p[0]==s and p[1]==o """

    query = qt_proto % ('?x', 'ns:sub  ?x 123 .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')
    O.attach_fd()

    O.finish()
    res = O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0] == 'ns_p' 
    assert res[0]['x'] == 'ns_p'

def test_case_3():
    """search for s in p"""

    query = qt_proto % ('?x', 'ns:sub ns:p ?x .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')

    O.attach_fd()
    O.finish()
    res = O.sparql(query)
    assert res[0]['x'] == 123

def test_case_4():
    """ search for s in p """

    query = qt_proto % ('?x ?y', '?x ?y 123 .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')
    O.attach_fd()
    O.finish()

    res = O.sparql(query)
    assert res[0]['x'] == u'http://example.org/ns#sub' 
    assert res[0]['y'] == 'ns_p' #u'http://example.org/ns#p' 
    assert res[0]['x'] == u'http://example.org/ns#sub' 

def test_case_5():
    """ for all p's return p[0] if p[1]==o """

    query = qt_proto % ('?x ?y', '?x ns:p ?y .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')
    O.attach_fd()
    O.finish()

    res = O.sparql(query)
    assert res[0]['x'] == u'http://example.org/ns#sub' 
    assert res[0]['y'] == 123 

def test_case_6():
    """ return the values of p """
    py.test.skip("Doesn't work yet")

    query = qt_proto % ('?x ?y', 'ns:sub ?x ?y .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')
    O.attach_fd()
    O.finish()

    res = O.sparql(query)
    assert list(O.variables['x'].getValues())[0].uri == u'http://example.org/ns#sub' 
    assert res[0]['x'] == u'http://example.org/ns#sub' 

def test_case_7():
    """ for all p's return p[1] if p[0]==s """

    query = qt_proto % ('?x ?y ?z', '?x ?y ?z .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')
    O.attach_fd()
    O.finish()
    res = O.sparql(query)
    assert list(O.variables['query_x_'].getValues())[0].uri == u'http://example.org/ns#sub' 
    assert res[0]['x'] == u'http://example.org/ns#sub' 

def test_filter():
    query = qt_proto % ('?x ?y', '?x ns:p ?y  .\n FILTER(?y < 124) .')
    O = Ontology()
    O.add_file(datapath("testont.rdf"), 'xml')
    O.attach_fd()
    O.finish()
    res = O.sparql(query)
    assert res[0]['y'] == 123

query_x = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?x
                WHERE {
                        ?x rdf:type ltw:Active_FundingOrganisation .
                        ?x ltw:organisationNameAbbreviation 'BMBF' .
                                }"""

    
def test_queryx():
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    res = O.sparql(query_x)
    assert len(res) == 8
    assert res[0]['x'] == u'http://www.lt-world.org/ltw.owl#obj_61128'

query_y = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
        SELECT ?project
                WHERE {
                        ?project ltw:dateStart ?date_begin .
                        ?project ltw:dateEnd ?date_end .
                        FILTER ( ?date_begin  < "2007-01-01T00:00:00Z"^^xsd:dateTime
                        &&  ?date_end >= "2006-01-01T00:00:00Z"^^xsd:dateTime) .
                                }"""

    
def test_queryy():
    py.test.skip("Needs special care for dateTime type")
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    res = O.sparql(query_y)
    assert len(res) == 1
    assert res[0]['project'] == u'http://www.lt-world.org/ltw.owl#obj_61128'


query1_a = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?person ?activity
                WHERE {
                                ?activity rdf:type ltw:Active_Project .
                                ?person rdf:type ltw:Active_Person .
                                }
                ORDER BY ?person"""
query1_b = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?person ?activity
                WHERE {
                                ?activity ltw:hasParticipant ?person_obj .
                                ?person_obj ltw:personName ?person .
                                }
                ORDER BY ?person"""
def test_query1_a():
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    res = O.sparql(query1_a)
    assert len(res) == 81

def test_query1_b():
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    res = O.sparql(query1_b)
    assert len(res) == 1


#List of people
query0a = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        SELECT ?person
                WHERE {
                        ?person_obj rdf:type ltw:Active_Person .
                        ?person_obj ltw:personName ?person .
                      }"""

def test_query0a():
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    query_vars = ['person'] 
    res = O.sparql(query0a)
    for result in res:

         for v in query_vars:
             print "%s:" % v, result[v],
         print
         
    assert len(res) == 2
    


query1 = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?person ?activity
                WHERE {
                                ?activity_obj rdf:type ltw:Active_Project .
                                ?person_obj rdf:type ltw:Active_Person .
                                ?activity_obj ltw:hasParticipant ?person_obj .
                                ?activity_obj ltw:projectName ?activity .
                                ?person_obj ltw:personName ?person .
                                }
                ORDER BY ?person"""
#how many projects have been funded by BMBF in 2006
query2 = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?project ?date_begin ?x
                WHERE {
                        ?project ltw:supportedBy  ?x .
                        ?x rdf:type ltw:Active_FundingOrganisation .
                        ?x ltw:organisationNameAbbreviation 'BMBF' .
                        ?project ltw:dateStart ?date_begin .
                        ?project ltw:dateEnd ?date_end .
                        FILTER ( ?date_begin  < 2007  &&  ?date_end >= 2006) .
                                }"""
#which project is funded in a technological area (i.e. Semantic web),
query_3 = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?project ?x ?y
                WHERE {
                                ?project rdf:type ltw:Active_Project .
                                ?project ltw:lt_technologicalMethod ?y .
                                ?y rdf:type ltw:Semantic_Web .
                                ?project ltw:supportedBy ?x .
                                }"""

query3a = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?project ?x ?y
                WHERE {
                                ?project rdf:type ltw:Active_Project .
                                ?project ltw:lt_technologicalMethod ?y .
                                }"""

query3b = """
        PREFIX ltw : <http://www.lt-world.org/ltw.owl#>
        PREFIX owl : <http://www.w3.org/2002/07/owl#>
        PREFIX rdf : <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?project ?x ?y
                WHERE {
                                ?y rdf:type ltw:Semantic_Web .
                                ?project ltw:supportedBy ?x .
                                }"""

def test_query3a():
    py.test.skip("WIP")
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    res = O.sparql(query3a)
    assert len(res) == 1
    assert res[0]['project'] == u'http://www.lt-world.org/ltw.owl#obj_59773' 

def test_query3b():
    py.test.skip("WIP")
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    res = O.sparql(query3a)
    assert len(res) == 1
    assert res[0]['project'] == u'http://www.lt-world.org/ltw.owl#obj_59773' 

def test_query_1():
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    query_vars = ['person','activity'] 
    res = O.sparql(query1)
    for result in res:
         for v in query_vars:
             print "%s:" % v, result[v],
         print  
            
    assert len(res) == 1
    assert res[0]['person'] == u'\nKlara Vicsi'
    

def test_query_2():
   # py.test.skip("Needs special care for dateTime type")
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    res = O.sparql(query2)
    assert len(res) == 3
    assert res[0]['project'] == u'http://www.lt-world.org/ltw.owl#obj_59754' 
    assert res[0]['date_begin'] == datetime.date(1998,9,1) 

def test_query_3():
    py.test.skip("WIP")
    O = Ontology()
    O.add_file(datapath("testont2.rdf"), 'xml')
    O.attach_fd()

    res = O.sparql(query_3)
    assert len(res) == 1
    assert res[0]['project'] == u'http://www.lt-world.org/ltw.owl#obj_59773' 


import xmlrpclib, socket, os, signal

class _TestXMLRPC:

    def setup_class(self):
        from subprocess import Popen 
        import sys
        exe = sys.executable
        print exe
        self.oldcwd = os.getcwd()
        os.chdir(DATAPATH)
        self.shell = Popen("%s ../pyontology.py testont.rdf" % exe, shell=True)
        server = xmlrpclib.ServerProxy("http://localhost:9000")
        print "setup"

        while 1:
            try:
                server.ok()
            except socket.error:
                pass
            else:
                break
    def teardown_class(self):
        print " teardown", self.shell.pid
        os.chdir(self.oldcwd)
        try:
            os.kill(self.shell.pid, signal.SIGTERM)
        except AttributeError:
            print "SORRY can't kill process in this OS"

    def test_xmlrpc(self):
        print "test_xmlrpc"
        server = xmlrpclib.ServerProxy("http://localhost:9000", allow_none=True)
        result = server.sparql(qt_proto % ('?x', 'ns:sub ns:p ?x .'))
        result2 = server.sparql(qt_proto % ('?x', 'ns:test ns:p ?x .'))
        print "Result 2",result2
        assert result[0]['x'] == 123

def check_have_oldstyle():
    class A:pass
    return object not in A.__bases__

if check_have_oldstyle():
    TestXMLRPC = _TestXMLRPC
else:
    py.test.skip('Please build PyPy with --oldstyle, needed by xmlrpclib')
