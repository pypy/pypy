#!/usr/bin/env python

import sys
import paths
from os.path import join

sys.path.insert(0, paths.distdir)
sys.path.insert(0, paths.depssir)

from pypy.lib.pyontology.pyontology import Ontology

import SimpleXMLRPCServer

port = 9000

class OntologyWrapper(Ontology):

    def sparql(self, query):
        ans = []
        for result in Ontology.sparql(self, query):
           for (k, v) in result.items():
                ans.append("%s: %s" % (k, v))
        return '\n'.join(ans)

def sparql_with_ontology(sparql, rdffile):
    o = OntologyWrapper()
    o.add_file(rdffile)
    o.attach_fd()
    #o.consistency()
    return o.sparql(sparql)

if __name__ == "__main__":
    import SimpleXMLRPCServer

    server = SimpleXMLRPCServer.SimpleXMLRPCServer(("localhost", port))
    server.register_function(sparql_with_ontology)

    if len(sys.argv) > 1:
        rdffile = sys.argv[-1]
        o = OntologyWrapper()
        o.add_file(rdffile)
        o.attach_fd()
        #o.consistency()
        server.register_instance(o)
    
    print "Startng to serve queries"
    server.serve_forever()
