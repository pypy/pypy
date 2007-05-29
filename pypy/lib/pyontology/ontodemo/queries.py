from os.path import join
import paths

# !!!! We now ignore the RDF file and assume the server will use the
# same preset ontology for all SPARQL queries !!!

ontodir = paths.demodir
sparqldir = paths.demodir

def ontofile(query):
    if queries[query][1]:
        return join(ontodir, queries[query][1])
    else:
        return None

# def onto(query):
#     return file(ontofile(query)).read()

def sparqlfile(query):
    return join(sparqldir, queries[query][0])

def sparql(query):
    return file(sparqlfile(query)).read()

queries = {
    # Format:
    # "Natural language query": (<SPARQL file>, <RDF ontology file>),

    #"Query One": ("query1.spql", "query1.rdf"),
    #"Query Two":  ("query2.spql", "query1.rdf"),
    #"Query Seven":  ("query7.spql", "testont_test.rdf"),
    "Give me active persons in LT!": ("query1.spql", None),
    "Who is associated with a project?":  ("query2.spql", None),
    "What is Semantic Web technology?":("query3.spql", None),
    #"Which projects have been funded by BMBF" :("query5.spql", None),
    #"What is the aim of the project DIINAR-MBS":("query7.spql", None),
    "What are projects in NLG Technology and relevant publications?":("query8.spql", None),
    
}
