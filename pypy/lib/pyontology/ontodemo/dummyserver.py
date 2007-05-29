#!/usr/bin/env python

import SimpleXMLRPCServer

port = 9000

class Ontology:

    def sparql(self, sparql):
        return "Answer to SPARQL query:\n%s" % sparql

    def constr(self, sparql):
        return "Constraints for SPARQL query:\n%s" % sparql

if __name__ == "__main__":
    import SimpleXMLRPCServer

    server = SimpleXMLRPCServer.SimpleXMLRPCServer(("localhost", port))
    server.register_instance(Ontology())
    print "Starting XMLRPC server on port %s" % port
    server.serve_forever()
    
