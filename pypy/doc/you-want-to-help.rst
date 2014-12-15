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
  development means progressing in an unrelated corner, one unittest
  at a time; and then flipping a giant switch, bringing it all together.
  (It generally works out of the box.  If it doesn't, then we didn't
  write enough unit tests.)  It's worth repeating - PyPy's
  approach is great if you do TDD, and not so great otherwise.

* PyPy uses an entirely different set of tools - most of them included
  in the PyPy repository. There is no Makefile, nor autoconf. More below.


Architecture
------------

PyPy has layers. The 100 miles view:

* :ref:`RPython <rpython:language>` is the language in which we write interpreters. Not the entire
  PyPy project is written in RPython, only the parts that are compiled in
  the translation process. The interesting point is that RPython has no parser,
  it's compiled from the live python objects, which makes it possible to do
  all kinds of metaprogramming during import time. In short, Python is a meta
  programming language for RPython.

  The RPython standard library is to be found in the ``rlib`` subdirectory.

* The translation toolchain - this is the part that takes care of translating
  RPython to flow graphs and then to C. There is more in the :doc:`architecture <architecture>`
  document written about it.

  It lives in the ``rpython`` directory: ``flowspace``, ``annotator``
  and ``rtyper``.

* Python Interpreter and modules

  This is in the ``pypy`` directory.  ``pypy/interpreter`` is a standard
  interpreter for Python written in RPython.  The fact that it is
  RPython is not apparent at first.  Built-in modules are written in
  ``pypy/module/*``.  Some modules that CPython implements in C are
  simply written in pure Python; they are in the top-level ``lib_pypy``
  directory.  The standard library of Python (with a few changes to
  accomodate PyPy) is in ``lib-python``.

* :ref:`Just-in-Time Compiler (JIT) <rpython:jit>`: we have a tracing JIT that traces the
  interpreter written in RPython, rather than the user program that it
  interprets.  As a result it applies to any interpreter, i.e. any
  language.  But getting it to work correctly is not trivial: it
  requires a small number of precise "hints" and possibly some small
  refactorings of the interpreter.  The JIT itself also has several
  almost-independent parts: the tracer itself in ``rpython/jit/metainterp``, the
  optimizer in ``rpython/jit/metainterp/optimizer`` that optimizes a list of
  residual operations, and the backend in ``rpython/jit/backend/<machine-name>``
  that turns it into machine code.  Writing a new backend is a
  traditional way to get into the project.

* Garbage Collectors (GC): as you may notice if you are used to CPython's
  C code, there are no ``Py_INCREF/Py_DECREF`` equivalents in RPython code.
  :ref:`rpython:garbage-collection` is inserted
  during translation.  Moreover, this is not reference counting; it is a real
  GC written as more RPython code.  The best one we have so far is in
  ``rpython/memory/gc/incminimark.py``.


Toolset
-------

xxx
