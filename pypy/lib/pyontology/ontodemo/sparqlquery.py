import sys
from pypy.lib.pyontology.pyontology import Ontology

def query(sparqlfile, ontofile):
    # return "An answer string"
    O = Ontology()
    O.add_file(ontofile, 'xml')
    q = file(sparqlfile).read()
    res = O.sparql(q)
    return res
    
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Usage: %s <sparql query file> <RDF ontology file>" % sys.argv[0]
        sys.exit(1)
    print query(sys.argv[1], sys.argv[2])
