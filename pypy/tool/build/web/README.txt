py.tool.build.web
=================

What is this?
-------------

This is a web front-end for the PyPy build tool, which builds an ad-hoc network
of 'build-servers', all connected to a main 'meta server' to allow connecting
'compile clients' to compile on them. This allows the compile clients to use
a build of PyPy even if they do not have the resources to build it themselves.

The web front-end provides some status information about the server: what
build servers are connected to the network, how many builds are in progress,
details per build, etc. and also allows downloading a build if it's done.

How do I use it?
----------------

NOTE: Using the server only makes sense if you run a pypy.tool.build meta
server and want to allow clients to view status information!

Using it is relatively simple, just (XXX temporary solution!) run::

  $ PYTHONPATH=path/to/pypy/parentdir python app.py

and you will have a server running. 'path/to/pypy/parentdir' is an absolute
path to the _parent_ of the pypy package (to make 'import pypy' work), and
'app.py' is the script 'app.py' found in this directory.

Requirements
------------

The dependencies for this package are a reasonably new Python (tested on 2.4),
and a recent PyPy checkout or release (which you have, else you wouldn't be
reading this ;).

Questions, remarks, etc.
------------------------

For questions, remarks, etc. about this program, mail guido@merlinux.de.

