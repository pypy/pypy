Writing extension modules for pypy
==================================

This document tries to explain how to interface the PyPy python interpreter
with any external library.

Note: We try to describe state-of-the art, but it
might fade out of date as this is the front on which things are changing
in pypy rapidly.


Possibilities
-------------

Right now, there are three possibilities of providing third-party modules
for the PyPy python interpreter (in order of usefulness):

* Write them in pure python and use ctypes, see CTypes_ section

* Write them in pure python and use direct libffi low-level bindings, See
  `\_ffi <LibFFI>`_ module description.

* Write them in RPython as `mixedmodule <Mixed Modules>`_, using *rffi* as bindings.

* Write them in C++ and bind them through Reflex_


CTypes
------

The ctypes module in PyPy is ready to use.
It's goal is to be as-compatible-as-possible with the
`CPython ctypes`_ version. Right now it's able to support large examples,
such as pyglet. PyPy is planning to have a 100% compatible ctypes
implementation, without the CPython C-level API bindings (so it is very
unlikely that direct object-manipulation trickery through this API will work).

We also provide a `ctypes-configure`_ for overcoming the platform dependencies,
not relying on the ctypes codegen. This tool works by querying gcc about
platform-dependent details (compiling small snippets of C code and running
them), so it'll benefit not pypy-related ctypes-based modules as well.

ctypes call are optimized by the JIT and the resulting machine code contains a
direct call to the target C function.  However, due to the very dynamic nature
of ctypes, some overhead over a bare C call is still present, in particular to
check/convert the types of the parameters.  Moreover, even if most calls are
optimized, some cannot and thus need to follow the slow path, not optimized by
the JIT.

.. _ctypes-configure: ctypes-implementation.html#ctypes-configure
.. _CPython ctypes: http://docs.python.org/library/ctypes.html


Pros
~~~~

Stable, CPython-compatible API.  Most calls are fast, optimized by JIT.


Cons
~~~~

Problems with platform-dependency (although we partially solve
those). Although the JIT optimizes ctypes calls, some overhead is still
present.  The slow-path is very slow.


LibFFI
------

Mostly in order to be able to write a ctypes module, we developed a very
low-level libffi bindings called ``_ffi``. (libffi is a C-level library for dynamic calling,
which is used by CPython ctypes). This library provides stable and usable API,
although it's API is a very low-level one. It does not contain any
magic.  It is also optimized by the JIT, but has much less overhead than ctypes.


Pros
~~~~

It Works. Probably more suitable for a delicate code where ctypes magic goes
in a way.  All calls are optimized by the JIT, there is no slow path as in
ctypes.


Cons
~~~~

It combines disadvantages of using ctypes with disadvantages of using mixed
modules. CPython-incompatible API, very rough and low-level.


Mixed Modules
-------------

This is the most advanced and powerful way of writing extension modules.
It has some serious disadvantages:

* a mixed module needs to be written in RPython, which is far more
  complicated than Python (XXX link)

* due to lack of separate compilation (as of July 2011), each
  compilation-check requires to recompile whole PyPy python interpreter,
  which takes 0.5-1h. We plan to solve this at some point in near future.

* although rpython is a garbage-collected language, the border between
  C and RPython needs to be managed by hand (each object that goes into the
  C level must be explicitly freed).

Some documentation is available :doc:`here <rpython:rffi>`


Reflex
------

This method is still experimental and is being exercised on a branch,
reflex-support, which adds the :doc:`cppyy <cppyy>` module.
The method works by using the `Reflex package`_ to provide reflection
information of the C++ code, which is then used to automatically generate
bindings at runtime.
From a python standpoint, there is no difference between generating bindings
at runtime, or having them "statically" generated and available in scripts
or compiled into extension modules: python classes and functions are always
runtime structures, created when a script or module loads.
However, if the backend itself is capable of dynamic behavior, it is a much
better functional match to python, allowing tighter integration and more
natural language mappings.
Full details are available :doc:`here <cppyy>`.

.. _Reflex package: http://root.cern.ch/drupal/content/reflex


Pros
~~~~

The cppyy module is written in RPython, which makes it possible to keep the
code execution visible to the JIT all the way to the actual point of call into
C++, thus allowing for a very fast interface.
Reflex is currently in use in large software environments in High Energy
Physics (HEP), across many different projects and packages, and its use can be
virtually completely automated in a production environment.
One of its uses in HEP is in providing language bindings for CPython.
Thus, it is possible to use Reflex to have bound code work on both CPython and
on PyPy.
In the medium-term, Reflex will be replaced by `cling`_, which is based on
`llvm`_.
This will affect the backend only; the python-side interface is expected to
remain the same, except that cling adds a lot of dynamic behavior to C++,
enabling further language integration.

.. _cling: http://root.cern.ch/drupal/content/cling
.. _llvm: http://llvm.org/


Cons
~~~~

C++ is a large language, and cppyy is not yet feature-complete.
Still, the experience gained in developing the equivalent bindings for CPython
means that adding missing features is a simple matter of engineering, not a
question of research.
The module is written so that currently missing features should do no harm if
you don't use them, if you do need a particular feature, it may be necessary
to work around it in python or with a C++ helper function.
Although Reflex works on various platforms, the bindings with PyPy have only
been tested on Linux.
