===========================
PyPy 1.6 - faster than ever
===========================

We're pleased to announce the 1.6 release of PyPy. This release brings a lot
of bugfixes and performance improvements over 1.5, and improves support for
Windows 32bit and OS X 64bit. This version fully implements Python 2.7.1 and
has beta level support for loading CPython C extensions.  You can download it
here:

    http://pypy.org/download.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7.1. It's fast (`pypy 1.5 and cpython 2.6.2`_ performance comparison)
due to its integrated tracing JIT compiler. XXX: compare to 2.7.1

This release supports Intel machines running Linux 32/64 or Mac OS X.  Windows
is beta (it roughly works but a lot of small issues have not been fixed so
far).  Windows 64 is not yet supported.

The main topics of this release are speed and stability: on average, PyPy 1.6
is between 20% and 30% faster than PyPy 1.5, and overall it's 4.3 times faster
than CPython when running our set of benchmarks.

The speed improvements have been made possible by optimizing many of the
layers which compose PyPy.  In particular, we improved: the Garbage Collector,
the JIT warmup time, the optimizations performed by the JIT, the quality of
the generated machine code and the implementation of our Python interpreter.


Highlights
==========

* Numerous performance improvements, overall giving considerable speedups:

  - better GC behavior when dealing with very large objects and arrays

  - `fast ctypes`_: now calls to ctypes functions are seen and optimized
    by the JIT, and they are up to 60 times faster than PyPy 1.5 and 10 times
    faster than CPython

  - improved generators(1): simple generators now are inlined into the caller
    loop, making performance up to 3.5 times faster than PyPy 1.5.

  - improved generators(2): thanks to other optimizations, even generators
    that are not inlined are between 10% and 20% faster than PyPy 1.5.

  - faster warmup time for the JIT

  - JIT support for single floats (e.g., for ``array('f')``)

  - optimized dictionaries: the internal representation of dictionaries is now
    dynamically selected depending on the type of stored objects, resulting in
    faster code and smaller memory footprint.  For example, dictionaries whose
    keys are all strings, or all integers.

* JitViewer: this is the first official release which includes the JitViewer,
  a web-based tool which helps you to see which parts of your Python code have
  been compiled by the JIT, down until the assembler. XXX: publish a public
  demo?

- The CPython extension module API has been improved and now supports many
  more extensions. For information on which one are supported, please refer to
  our `compatibility wiki`_.

* Multibyte encoding support: this was of of the last areas in which we were
  still behind CPython, but now we fully support them. (XXX: is that true?)

* Preliminary support for numpy: this release includes a preview of a very
  fast numpy module integrated with the PyPy JIT.  Unfortunately, this does
  not mean that you can expect to take an existing numpy program and run it on
  PyPy, because the module is still unfinished and supports only some of the
  numpy API.  However, what works is blaizingly fast :-)

* Bugfixes: since the 1.5 release we fixed 53 bugs in our `bug tracker`_, not
  counting the numerous bugs that were found and reported through other
  channels than the bug tracker.

Cheers,

Carl Friedrich Bolz, Laura Creighton, Antonio Cuni, Maciej Fijalkowski,
Amaury Forgeot d'Arc, Alex Gaynor, Armin Rigo and the PyPy team
