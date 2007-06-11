How to run the pyontology demo
------------------------------

The following configuration of modules should be used to test the
system with Python 2.4.

* Check out PyPy from http://codespeak.net/svn/pypy/dist/

* Check out dependencies from http://codespeak.net/svn/user/arigo/hack/pypy-hack/pyontology-deps
  This will load the following packages:

   * Logilab common (ftp://ftp.logilab.fr/pub/common)
   * Logilab constraint (ftp://ftp.logilab.fr/pub/constraint/logilab-constraint-0.3.0)
   * rdflib_ (http://rdflib.net)

  At the same time it will avoid the installation of an outdated
  commercial version of VisualStudio that would otherwise be needed
  for compilation. 

* Install pyparsing.py (available from Sourceforge.net)

For the GUI, some components need to be installed to support graphical
interfaces. 

* Install Pythoncard (http://pythoncard.sourceforge.net)

* Install Wxpython (http://www.wxpython.org/) 

In the current directory

* adapt path names in paths.py
* start server: ./ontoserver <ontology>
  where <ontology> is a file specification for your OWL file
* start GUI: ./python ontodemo

To define SPARQL queries, write each in a file. Edit file queries.py,
adding lines of the following kind:
"<natural language question>": ("<filename>", None),

In the GUI, select a question and press "answer" to see the result.
