
You want to help with PyPy, now what?
=====================================

PyPy is a very large project that has a reputation of being hard to dive into.
Some of this fame is warranted, some of it is purely accidental. There are three
important lessons that everyone willing to contribute should learn:

* PyPy has layers. There are many pieces of architecture that are very well
  separated from each other. More about this below, but often the manifestation
  of this is that things are at a different layer than you would expect them
  to be. For example if you are looking for the JIT implementation, you will
  not find it in the implementation of the Python programming language.

* Because of the above, we are very serious about Test Driven Development.
  It's not only what we believe in, but also that PyPy's architecture is
  working very well with TDD in mind and not so well without it. Often
  the development means progressing in an unrelated corner, one unittest
  at a time; and then flipping a giant switch, bringing it all together.
  (It generally works out of the box.  If it doesn't, then we didn't
  write enough unit tests.)  It's worth repeating - PyPy
  approach is great if you do TDD, not so great otherwise.

* PyPy uses an entirely different set of tools - most of them included
  in the PyPy repository. There is no Makefile, nor autoconf. More below

Architecture
============

PyPy has layers. The 100 miles view:

* `RPython`_ is the language in which we write interpreters. Not the entire
  PyPy project is written in RPython, only the parts that are compiled in
  the translation process. The interesting point is that RPython has no parser,
  it's compiled from the live python objects, which make it possible to do
  all kinds of metaprogramming during import time. In short, Python is a meta
  programming language for RPython.

  The RPython standard library is to be found in the ``rlib`` subdirectory.

.. _`RPython`: coding-guide.html#RPython

* The translation toolchain - this is the part that takes care about translating
  RPython to flow graphs and then to C. There is more in the `architecture`_
  document written about it.

  It mostly lives in ``rpython``, ``annotator`` and ``objspace/flow``.

.. _`architecture`: architecture.html 

* Python Interpreter

  xxx

* Python modules

  xxx

* Just-in-Time Compiler (JIT): `we have a tracing JIT`_ that traces the
  interpreter written in RPython, rather than the user program that it
  interprets.  As a result it applies to any interpreter, i.e. any
  language.  But getting it to work correctly is not trivial: it
  requires a small number of precise "hints" and possibly some small
  refactorings of the interpreter.  The JIT itself also has several
  almost-independent parts: the tracer itself in ``jit/metainterp``, the
  optimizer in ``jit/metainterp/optimizer`` that optimizes a list of
  residual operations, and the backend in ``jit/backend/<machine-name>``
  that turns it into machine code.  Writing a new backend is a
  traditional way to get into the project.

.. _`we have a tracing JIT`: jit/index.html

* Garbage Collectors (GC): as you can notice if you are used to CPython's
  C code, there are no ``Py_INCREF/Py_DECREF`` equivalents in RPython code.
  `Garbage collection in PyPy`_ is inserted
  during translation.  Moreover, this is not reference counting; it is a real
  GC written as more RPython code.  The best one we have so far is in
  ``rpython/memory/gc/minimark.py``.

.. _`Garbage collection in PyPy`: garbage_collection.html


Toolset
=======

xxx
