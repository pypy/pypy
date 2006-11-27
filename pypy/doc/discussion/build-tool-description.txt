============
PyPyBuilder
============

NOTE: this package is under construction, it does not contain all the 
functionality described below. Also described functionality may differ from
the actual (test) implementation.

What is this?
=============

PyPyBuilder is an application that allows people to build PyPy instances on
demand. If you have a nice idle machine connected to the Internet, and don't
mind us 'borrowing' it every once in a while, you can start up the client
script (in bin/client) and have the server send compile jobs to your machine.
If someone requests a build of PyPy that is not already available on the PyPy
website, and your machine is capable of making such a build, the server may ask
your machine to create it. If enough people participate, with diverse enough
machines, a 'build farm' is created.

Components
==========

The application consists of 3 main components: a server component, a client 
component that handles compilations (let's call this a 'participating client')
and a small client component to start compile jobs (which we'll call 'compiling
client' for now).

The server waits for participating clients to register, and for compile job
requests. When participating clients register, they pass the server information
about what compilations they can handle (system info). Then when a compiling
client requests a compilation job, the server checks whether a binary is
already available, and if so returns that. 

If there isn't one, the server walks through a list of connected participating
clients to see if one of them can handle the job, and if so dispatches the
compilation. If there's no participating client to handle the job, it gets
queued until there is. Also, if a client crashes during compilation, the job
gets re-queued. This process will continue until a suitable build is available.

Once a build is available, the server will send an email to all email addresses
(it could be that more than one person asked for some build at the same time!)
passed to it by the compiling clients.

Configuration
=============

There are several aspects to configuration on this system. Of course, for the
server, client and startcompile components there is configuration for the host
and port to connect to, and there is some additional configuration for things
like which mailhost to use (only applies to the server), but also there are
configurations passed around to determine what client is picked, and what the
client needs to compile exactly.

Application configuration
-------------------------

The 'host and port configuration' as dicussed in the previous paragraph, for
all components this can be found in 'pypy/tool/build/config.py'. Unless you are
using a test version of the build tool, participate in a project that is not
PyPy, or want to do testing yourself, this should generally be left alone.

System configuration
--------------------

This information is used by the client and startcompile components. On the
participating clients this information is retrieved by querying the system, on
the compiling clients the system values are used by default, but may be
overridden (so a compiling client running an x86 can still request PPC builds,
for instance). The server finds a matching participant client for a certain
compilation request by determining if the provided compilation system
configuration is a subset of that provided by participating clients. Note that
the version of the source code (either the release number or SVN revision)
is a special part of this configuration, the participating clients tell what
PyPy versions they can provide, the compiling clients give a range of versions
that it doesn't mind getting (XXX not sure if I agree here, I think having the
participating clients 'svn switch' for each compilation makes more sense...)

Compilation configuration
-------------------------

The third form of configuration is that of the to-be-built application itself,
its compilation arguments. This configuration is only provided by the
compiling clients, assumed is that participating clients can deal with any
application configuration. (XXX oops, this is not by default true, is it?
For instance, not all modules can be built on all systems, depending on which
libraries are installed, right? Or can we deal with that through system 
config somehow?)

Compilation configuration can be controlled using command-line arguments (use 
'--help' for an overview).

Installation
============

Client
------

Installing the system should not be required: just run './bin/client' to start
the client. Note that it depends on the `py lib`_ (as does the rest of PyPy).

Server
------

Also for the server there's no real setup required, and again there's a 
dependency on the `py lib`_. Starting it is done by running './bin/server'.

.. _`py lib`: http://codespeak.net/py

Running a compile job
---------------------

Again installation is not required, just run './bin/startcompile [options]
<email>' (see --help for the options) to start.

More info
=========

For more information, bug reports, patches, etc., please send an email to 
guido@merlinux.de.
