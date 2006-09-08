from pypy.lib.pyontology.sparql_grammar import SPARQLGrammar as SP


qt = """
         PREFIX ns : <http://example.org/ns#>
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
    assert triples[0][0].getName() == 'VAR1' 
    assert triples[1][0].getName() == 'VAR1' 
    assert triples[1][0][0] == 'x' 
    assert triples[0][0][0] == 'y' 
    assert triples[1][1].asList() == ['ns', 'p'] 
    assert triples[0][1].asList() == ['ns', 'q'] 
    assert triples[1][2][0] == '123'
    assert triples[1][2].getName() == 'Object'
    vars = query.SelectQuery[0].VARNAME
    assert len(vars) == 2
    assert 'x' in vars[0][0]
    assert 'y' in vars[1][0]

class notest:

    def sparql(self, query):
        qe = SP.Query.parseString(query)[0]

        prefixes = qe.PrefixDecl[0]

        resvars = []
        for v in qe.SelectQuery[0].VARNAME:
            resvars.append(v[0])
        
        where = qe.SelectQuery[0].WhereClause[0]

        triples = where.GroupGraphPattern[0].Triples
        new = []
        for trip in triples:
            newtrip = []
            for item in trip:
                if item.NCNAME_PREFIX:
                    uri = prefixes[item.NCNAME_PREFIX[0]] + item.NCNAME[0]
                    newtrip.append(uri)
                elif item.getName() == 'VAR1':
                    newtrip.append(item[0])
                else:
                    newtrip.append(item)
            new.append(newtrip)
        constrain = where.GroupGraphPattern[0].Constraint
        return new, prefixes, resvars, constrain

def test_sparql():
    n = notest()
    result = n.sparql(qt)
    res = result[0]
    assert len(res) == 2
    assert len(res[0]) == len(res[1]) == 3
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

