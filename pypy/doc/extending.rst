===================================
Writing extension modules for pypy
===================================

This document tries to explain how to interface the PyPy python interpreter
with any external library.

Note: We try to describe state-of-the art, but it
might fade out of date as this is the front on which things are changing
in pypy rapidly.

Possibilities
=============

Right now, there are three possibilities of providing third-party modules
for the PyPy python interpreter (in order of usefulness):

* Write them in pure python and use ctypes, see ctypes_
  section

* Write them in pure python and use direct libffi low-level bindings, See
  \_rawffi_ module description.

* Write them in RPython as mixedmodule_, using *rffi* as bindings.

.. _ctypes: #CTypes
.. _\_rawffi: #LibFFI
.. _mixedmodule: #Mixed Modules

CTypes
======

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

.. _`ctypes-configure`: ctypes-implementation.html#ctypes-configure

Pros
----

Stable, CPython-compatible API

Cons
----

Only pure-python code (slow), problems with platform-dependency (although
we partially solve those). PyPy implementation is now very slow.

_`CPython ctypes`: http://python.net/crew/theller/ctypes/

LibFFI
======

Mostly in order to be able to write a ctypes module, we developed a very
low-level libffi bindings. (libffi is a C-level library for dynamic calling,
which is used by CPython ctypes). This library provides stable and usable API,
although it's API is a very low-level one. It does not contain any
magic.

Pros
----

Works. Combines disadvantages of using ctypes with disadvantages of
using mixed modules. Probably more suitable for a delicate code
where ctypes magic goes in a way.

Cons
----

Slow. CPython-incompatible API, very rough and low-level

Mixed Modules
=============

This is the most advanced and powerful way of writing extension modules.
It has some serious disadvantages:

* a mixed module needs to be written in RPython, which is far more
  complicated than Python (XXX link)

* due to lack of separate compilation (as of April 2008), each
  compilation-check requires to recompile whole PyPy python interpreter,
  which takes 0.5-1h. We plan to solve this at some point in near future.

* although rpython is a garbage-collected language, the border between
  C and RPython needs to be managed by hand (each object that goes into the
  C level must be explicitly freed) XXX we try to solve this

Some document is available `here`_

.. _`here`: rffi.html

XXX we should provide detailed docs about lltype and rffi, especially if we
    want people to follow that way.
