Writing extension modules for pypy
==================================

This document tries to explain how to interface the PyPy python interpreter
with any external library.

Right now, there are the following possibilities of providing
third-party modules for the PyPy python interpreter (in order, from most
directly useful to most messy to use with PyPy):

* Write them in pure Python and use CFFI_.

* Write them in pure Python and use ctypes_.

* Write them in C++ and bind them through Reflex_.

* Write them in as `RPython mixed modules`_.


CFFI
----

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
------

The goal of the ctypes module of PyPy is to be as compatible as possible
with the `CPython ctypes`_ version.  It works for large examples, such
as pyglet.  PyPy's implementation is not strictly 100% compatible with
CPython, but close enough for most cases.

We also used to provide ``ctypes-configure`` for some API-level access.
This is now viewed as a precursor of CFFI, which you should use instead.
More (but older) information is available :doc:`here <discussion/ctypes-implementation>`.
Also, ctypes' performance is not as good as CFFI's.

.. _CPython ctypes: http://docs.python.org/library/ctypes.html

PyPy implements ctypes as pure Python code around two built-in modules
called ``_ffi`` and ``_rawffi``, which give a very low-level binding to
the C library libffi_.  Nowadays it is not recommended to use directly
these two modules.

.. _libffi: http://sourceware.org/libffi/


Reflex
------

The builtin :doc:`cppyy <cppyy>` module uses reflection information, provided by
`Reflex`_ (which needs to be `installed separately`_), of C/C++ code to
automatically generate bindings at runtime.
In Python, classes and functions are always runtime structures, so when they
are generated matters not for performance.
However, if the backend itself is capable of dynamic behavior, it is a much
better functional match, allowing tighter integration and more natural
language mappings.

The :doc:`cppyy <cppyy>` module is written in RPython, thus PyPy's JIT is able to remove
most cross-language call overhead.

:doc:`Full details <cppyy>` are `available here <cppyy>`.

.. _installed separately: http://cern.ch/wlav/reflex-2013-08-14.tar.bz2
.. _Reflex: https://root.cern.ch/how/how-use-reflex


RPython Mixed Modules
---------------------

This is the internal way to write built-in extension modules in PyPy.
It cannot be used by any 3rd-party module: the extension modules are
*built-in*, not independently loadable DLLs.

This is reserved for special cases: it gives direct access to e.g. the
details of the JIT, allowing us to tweak its interaction with user code.
This is how the numpy module is being developed.


.. toctree::
   :hidden:

   cppyy
