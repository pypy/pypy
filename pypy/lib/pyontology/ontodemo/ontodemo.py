#!/usr/bin/env python

"""
Demo of the PyPy SPARQL handling functionality.
"""

from PythonCard import model
import webbrowser
import queries
import commands
import paths
import xmlrpclib
from os.path import join

ltworld = "file:" + join(paths.demodir, "lt-world.html")

class Server:

    def __init__(self):
        # Maybe some error handling?
        self.server = xmlrpclib.ServerProxy("http://localhost:9000", allow_none=True)

    def constrquery(self, sparql):
        return self.server.constr(sparql)

    def sparqlquery(self, sparql, ontofile):
        if ontofile:
            return self.server.sparql_with_ontology(sparql, ontofile)
        else:
            return self.server.sparql(sparql)

server = Server()

class SPARQL(model.Background):

    def on_initialize(self, event):
        self.components.Queries.items = queries.queries.keys()

    def on_PyPy_mouseClick(self, event):
        webbrowser.open('http://codespeak.net/pypy/dist/pypy/doc/news.html', 1, 1)

    def on_DFKI_mouseClick(self, event):
        webbrowser.open('http://dfki.de/', 1, 1)

    def on_LTWorld_mouseClick(self, event):
        # webbrowser.open('http://www.lt-world.org/', 1, 1)
        webbrowser.open(ltworld, 1, 1)

    def on_Queries_select(self, event):
        query = self.components.Queries.stringSelection
        self.components.SparqlTextArea.text =  queries.sparql(query)
        self.components.AnswerTextArea.text = ""

    def on_AnswerButton_mouseClick(self, event):
        query = self.components.Queries.stringSelection
        sparql = self.components.SparqlTextArea.text
        ontofile = queries.ontofile(query)
        res = server.sparqlquery(sparql, ontofile)
        self.components.AnswerTextArea.text = res

if __name__ == '__main__':
    app = model.Application(SPARQL)
    app.MainLoop()
