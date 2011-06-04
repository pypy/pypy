
Potential project list
======================

This is a list of projects that are interesting for potential contributors
who are seriously interested in the PyPy project. They mostly share common
patterns - they're mid-to-large in size, they're usually well defined as
a standalone projects and they're not being actively worked on. For small
projects that you might want to work on, it's much better to either look
at the `issue tracker`_, pop up on #pypy on irc.freenode.net or write to the
`mailing list`_. This is simply for the reason that small possible projects
tend to change very rapidly.

XXX: write a paragraph that this is a loose collection and where to go
from here

Numpy improvements
------------------

This is more of a project-container than a single project. Possible ideas:

* experiment with auto-vectorization using SSE or implement vectorization
  without automatically detecting it for array operations.

* improve numpy, for example implement memory views.

* interface with fortran/C libraries.

JIT tooling
-----------

Analyzing performance of applications is always tricky. We have various
tools, for example a `jitviewer`_ that help us analyze performance.
Improvements to existing tools as well as new tools would be of great help.

Work on some of other languages
-------------------------------

There are various languages implemented using the RPython translation toolchain.
One of the most interesting is the `JavaScript implementation`_, but there
are others like scheme or prolog. An interesting project would be to improve
the jittability of those or to experiment with various optimizations.

Various GCs
-----------

PyPy has pluggable garbage collection policy. This means that various garbage
collectors can be written for specialized purposes, or even various
experiments can be done for the general purpose. Examples

* An incremental garbage collector that has specified maximal pause times,
  crucial for games

* A garbage collector that compact memory better for mobile devices

* A concurrent garbage collector (a lot of work)

Remove the GIL
--------------

This is a major task that requiers lots of thinking. However, few subprojects
can be potentially specified, unless a better plan can be thought out:

* A thread-aware garbage collector

* Better RPython primitives for dealing with concurrency

* JIT passes to remove locks on objects

* (maybe) implement locking in Python interpreter

Experiment (again) with LLVM backend for RPython compilation
------------------------------------------------------------

We already tried working with LLVM and at the time, LLVM was not mature enough
for our needs. It's possible that this has changed, reviving the LLVM backend
(or writing new from scratch) for static compilation would be a good project.

.. _`issue tracker`: ...
.. _`mailing list`: ...
.. _`jitvirwer`: ...
.. _`JavaScript implementation`: ...
