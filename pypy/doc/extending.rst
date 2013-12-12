===================================
Writing extension modules for pypy
===================================

This document tries to explain how to interface the PyPy python interpreter
with any external library.

Right now, there are the following possibilities of providing
third-party modules for the PyPy python interpreter (in order of
usefulness):

* Write them in pure Python and use CFFI_.

* Write them in pure Python and use ctypes_.

* Write them in C++ and bind them through Reflex_.

* Write them in as `RPython mixed modules`_.


CFFI
====

CFFI__ is the recommended way.  It is a way to write pure Python code
that accesses C libraries.  The idea is to support either ABI- or
API-level access to C --- so that you can sanely access C libraries
without depending on details like the exact field order in the C
structures or the numerical value of all the constants.  It works on
both CPython (as a separate ``pip install cffi``) and on PyPy, where it
is included by default.

PyPy's JIT does a quite reasonable job on the Python code that call C
functions or manipulate C pointers with CFFI.  (As of PyPy 2.2.1, it
could still be improved, but is already good.)

See the documentation here__.

.. __: http://cffi.readthedocs.org/
.. __: http://cffi.readthedocs.org/


CTypes
======

The goal of the ctypes module of PyPy is to be as compatible as possible
with the `CPython ctypes`_ version.  It works for large examples, such
as pyglet.  PyPy's implementation is not strictly 100% compatible with
CPython, but close enough for most cases.

We also used to provide ``ctypes-configure`` for some API-level access.
This is now viewed as a precursor of CFFI, which you should use instead.
More (but older) information is available here__.
Also, ctypes' performance is not as good as CFFI's.

.. _`CPython ctypes`: http://docs.python.org/library/ctypes.html
.. __: ctypes-implementation.html

PyPy implements ctypes as pure Python code around two built-in modules
called ``_ffi`` and ``_rawffi``, which give a very low-level binding to
the C library libffi_.  Nowadays it is not recommended to use directly
these two modules.

.. _libffi: http://sourceware.org/libffi/


Reflex
======

This method is still experimental.  It adds the `cppyy`_ module.
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
Full details are `available here`_.

.. _`cppyy`: cppyy.html
.. _`reflex-support`: cppyy.html
.. _`Reflex package`: http://root.cern.ch/drupal/content/reflex
.. _`available here`: cppyy.html

Pros
----

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

.. _`cling`: http://root.cern.ch/drupal/content/cling
.. _`llvm`: http://llvm.org/

Cons
----

C++ is a large language, and cppyy is not yet feature-complete.
Still, the experience gained in developing the equivalent bindings for CPython
means that adding missing features is a simple matter of engineering, not a
question of research.
The module is written so that currently missing features should do no harm if
you don't use them, if you do need a particular feature, it may be necessary
to work around it in python or with a C++ helper function.
Although Reflex works on various platforms, the bindings with PyPy have only
been tested on Linux.


RPython Mixed Modules
=====================

This is the internal way to write built-in extension modules in PyPy.
It cannot be used by any 3rd-party module: the extension modules are
*built-in*, not independently loadable DLLs.

This is reserved for special cases: it gives direct access to e.g. the
details of the JIT, allowing us to tweak its interaction with user code.
This is how the numpy module is being developed.
