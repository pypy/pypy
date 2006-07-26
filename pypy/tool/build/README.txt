============
PyPyBuilder
============

NOTE: this package is under construction, it does not contain all the 
functionality described below. It is useful for testing, but e.g. it does not
really compile anything yet.

What is this?
=============

PyPyBuilder is an application that allows people to build PyPy instances on
demand. If you have a nice idle machine connected to the Internet, and don't
mind us 'borrowing' it every once in a while, you can start up the client
script (in bin/client) and have the server send compile jobs to your machine.
If someone requests a build of PyPy that is not already available on the PyPy
website, and your machine is capable of making such a build, the server may ask
your machine to create it. If enough people participate, with diverse enough
machines, an ad-hoc 'build farm' is created this way.

Components
==========

The application consists of 3 main components: a server component, a client and
a small component to start compile jobs, which we'll call 'startcompile' for
now. 

The server waits for clients to register, and for compile job requests. When
clients register, they pass the server information about what compilations they
can handle (system info). Then when the 'startcompile' component requests a
compilation job, the server first checks whether a binary is already available,
and if so returns that. 

If there isn't one, the server walks through a list of connected clients to see
if there is one that can handle the job, and if so tells it to perform it. If
there's no client to handle the job, it gets queued until there is.

Once a build is available, the server will send an email to all email addresses
(it could be more than one person asked for the same build at the same time!)
passed to it by 'startcompile'.

Installation
============

Client
------

Installing the system should not be required: just run './bin/client' to start
the client. Note that it depends on the `py lib`_.

Server
------

Also for the server there's no real setup required, and again there's a 
dependency on the `py lib`_.

.. _`py lib`: http://codespeak.net/py

More info
=========

For more information, bug reports, patches, etc., please send an email to 
guido@merlinux.de.
