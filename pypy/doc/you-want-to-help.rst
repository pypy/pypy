
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
  at a time and then flipping a giant switch. It's worth repeating - PyPy
  approach is great if you do TDD, not so great otherwise.

* PyPy uses an entirely different set of tools - most of them included
  in the PyPy repository. There is no Makefile, nor autoconf. More below

Architecture
============

PyPy has layers. The 100 mile view:

* `RPython`_ is a language in which we write interpreter in PyPy. Not the entire
  PyPy project is written in RPython, only parts that are compiled in
  the translation process. The interesting point is that RPython has no parser,
  it's compiled from the live python objects, which make it possible to do
  all kinds of metaprogramming during import time. In short, Python is a meta
  programming language for RPython.

  RPython standard library is to be found in ``rlib`` subdirectory.

.. _`RPython`: coding-guide.html#RPython

* Translation toolchain - this is the part that takes care about translating
  RPython to flow graphs and then to C. There is more in `architecture`_
  document written about it.

  It mostly lives in ``rpython``, ``annotator`` and ``objspace/flow``.

.. _`architecture`: architecture.html 

* Python Interpreter

  xxx

* Python modules

  xxx

* JIT

  xxx

* Garbage Collectors

  xxx

Toolset
=======

xxx
