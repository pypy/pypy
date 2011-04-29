==================================================
Goals and Architecture Overview 
==================================================

.. contents::


This document gives an overview of the goals and architecture of PyPy.
See `getting started`_ for a practical introduction and starting points. 

Mission statement 
====================

We aim to provide:

 * a common translation and support framework for producing
   implementations of dynamic languages, emphasizing a clean
   separation between language specification and implementation
   aspects.  We call this the `RPython toolchain`_.

 * a compliant, flexible and fast implementation of the Python_ Language 
   which uses the above toolchain to enable new advanced high-level features 
   without having to encode the low-level details.

By separating concerns in this way, our implementation
of Python - and other dynamic languages - is able to automatically
generate a Just-in-Time compiler for any dynamic language.  It also
allows a mix-and-match approach to implementation decisions, including
many that have historically been outside of a user's control, such as
target platform, memory and 
threading models, garbage collection strategies, and optimizations applied, 
including whether or not to have a JIT in the first place.

High Level Goals
=============================

PyPy - the Translation Framework 
-----------------------------------------------

Traditionally, language interpreters are written in a target platform language
such as C/Posix, Java or C#.  Each implementation provides 
a fundamental mapping between application source code and the target 
environment.  One of 
the goals of the "all-encompassing" environments, such as the .NET framework
and to some extent the Java virtual machine, is to provide standardized
and higher level functionalities in order to support language implementers
for writing language implementations. 

PyPy is experimenting with a more ambitious approach.  We are using a
subset of the high-level language Python, called RPython_, in which we
write languages as simple interpreters with few references to and
dependencies on lower level details.  The `RPython toolchain`_
produces a concrete virtual machine for the platform of our choice by
inserting appropriate lower level aspects.  The result can be customized
by selecting other feature and platform configurations.

Our goal is to provide a possible solution to the problem of language
implementers: having to write ``l * o * p`` interpreters for ``l``
dynamic languages and ``p`` platforms with ``o`` crucial design
decisions.  PyPy aims at making it possible to change each of these
variables independently such that:

* ``l``: the language that we analyze can be evolved or entirely replaced;

* ``o``: we can tweak and optimize the translation process to produce 
  platform specific code based on different models and trade-offs;

* ``p``: we can write new translator back-ends to target different
  physical and virtual platforms.

By contrast, a standardized target environment - say .NET -
enforces ``p=1`` as far as it's concerned.  This helps making ``o`` a
bit smaller by providing a higher-level base to build upon.  Still,
we believe that enforcing the use of one common environment 
is not necessary.  PyPy's goal is to give weight to this claim - at least 
as far as language implementation is concerned - showing an approach
to the ``l * o * p`` problem that does not rely on standardization.

The most ambitious part of this goal is to `generate Just-In-Time
Compilers`_ in a language-independent way, instead of only translating
the source interpreter into an interpreter for the target platform.
This is an area of language implementation that is commonly considered
very challenging because of the involved complexity.


PyPy - the Python Interpreter 
--------------------------------------------

Our main motivation for developing the translation framework is to
provide a full featured, customizable, fast_ and `very compliant`_ Python
implementation, working on and interacting with a large variety of
platforms and allowing the quick introduction of new advanced language
features.

This Python implementation is written in RPython as a relatively simple
interpreter, in some respects easier to understand than CPython, the C
reference implementation of Python.  We are using its high level and
flexibility to quickly experiment with features or implementation
techniques in ways that would, in a traditional approach, require
pervasive changes to the source code.  For example, PyPy's Python
interpreter can optionally provide lazily computed objects - a small
extension that would require global changes in CPython.  Another example
is the garbage collection technique: changing CPython to use a garbage
collector not based on reference counting would be a major undertaking,
whereas in PyPy it is an issue localized in the translation framework,
and fully orthogonal to the interpreter source code.


PyPy Architecture 
===========================

As you would expect from a project implemented using ideas from the world
of `Extreme Programming`_, the architecture of PyPy has evolved over time
and continues to evolve.  Nevertheless, the high level architecture is 
stable. As described above, there are two rather independent basic
subsystems: the `Python Interpreter`_ and the `Translation Framework`_.

.. _`translation framework`:

The Translation Framework
-------------------------

The job of the RPython toolchain is to translate RPython_ programs
into an efficient version of that program for one of the various target
platforms, generally one that is considerably lower-level than Python.

The approach we have taken is to reduce the level of abstraction of the
source RPython program in several steps, from the high level down to the
level of the target platform, whatever that may be.  Currently we
support two broad flavours of target platforms: the ones that assume a
C-like memory model with structures and pointers, and the ones that
assume an object-oriented model with classes, instances and methods (as,
for example, the Java and .NET virtual machines do).

The RPython toolchain never sees the RPython source code or syntax
trees, but rather starts with the *code objects* that define the
behaviour of the function objects one gives it as input.  It can be
considered as "freezing" a pre-imported RPython program into an
executable form suitable for the target platform.

The steps of the translation process can be summarized as follows:

* The code object of each source functions is converted to a `control
  flow graph` by the `Flow Object Space`_.

* The control flow graphs are processed by the Annotator_, which
  performs whole-program type inference to annotate each variable of
  the control flow graph with the types it may take at run-time.

* The information provided by the annotator is used by the RTyper_ to
  convert the high level operations of the control flow graphs into
  operations closer to the abstraction level of the target platform.

* Optionally, `various transformations`_ can then be applied which, for
  example, perform optimizations such as inlining, add capabilities
  such as stackless_-style concurrency, or insert code for the
  `garbage collector`_.

* Then, the graphs are converted to source code for the target platform
  and compiled into an executable.

This process is described in much more detail in the `document about
the RPython toolchain`_ and in the paper `Compiling dynamic language
implementations`_.

.. _`control flow graph`: translation.html#the-flow-model
.. _`Flow Object Space`: objspace.html#the-flow-object-space
.. _Annotator: translation.html#the-annotation-pass
.. _RTyper: rtyper.html#overview
.. _`various transformations`: translation.html#the-optional-transformations
.. _`document about the RPython toolchain`: translation.html
.. _`garbage collector`: garbage_collection.html
.. _`RPython toolchain`: translation.html
.. _`standard interpreter`: 
.. _`python interpreter`: 

The Python Interpreter
-------------------------------------

PyPy's *Python Interpreter* is written in RPython and implements the
full Python language.  This interpreter very closely emulates the
behavior of CPython.  It contains the following key components:

- a bytecode compiler responsible for producing Python code objects 
  from the source code of a user application;

- a `bytecode evaluator`_ responsible for interpreting 
  Python code objects;

- a `standard object space`_, responsible for creating and manipulating
  the Python objects seen by the application.

The *bytecode compiler* is the preprocessing phase that produces a
compact bytecode format via a chain of flexible passes (tokenizer,
lexer, parser, abstract syntax tree builder, bytecode generator).  The
*bytecode evaluator* interprets this bytecode.  It does most of its work
by delegating all actual manipulations of user objects to the *object
space*.  The latter can be thought of as the library of built-in types.
It defines the implementation of the user objects, like integers and
lists, as well as the operations between them, like addition or
truth-value-testing.

This division between bytecode evaluator and object space is very
important, as it gives a lot of flexibility.  One can plug in 
different `object spaces`_ to get different or enriched behaviours 
of the Python objects.  Additionally, a special more abstract object
space, the `flow object space`_, allows us to reuse the bytecode
evaluator for our translation framework.

.. _`bytecode evaluator`: interpreter.html
.. _`standard object space`: objspace.html#the-standard-object-space
.. _`object spaces`: objspace.html
.. _`flow object space`: objspace.html#the-flow-object-space

.. _`the translation framework`:


Further reading
===============

All of PyPy's documentation can be reached from the `documentation
index`_.  Of particular interest after reading this document might be:

 * `getting-started`_: a hands-on guide to getting involved with the
   PyPy source code.

 * `PyPy's approach to virtual machine construction`_: a paper
   presented to the Dynamic Languages Symposium attached to OOPSLA
   2006.

 * `The translation document`_: a detailed description of our
   translation process.

 * All our `Technical reports`_, including `Compiling dynamic language
   implementations`_.

 * `JIT Generation in PyPy`_, describing how we produce a Just-in-time
   Compiler from an interpreter.

.. _`documentation index`: docindex.html
.. _`getting-started`: getting-started.html
.. _`PyPy's approach to virtual machine construction`: https://bitbucket.org/pypy/extradoc/raw/tip/talk/dls2006/pypy-vm-construction.pdf
.. _`the translation document`: translation.html
.. _`Compiling dynamic language implementations`: https://bitbucket.org/pypy/extradoc/raw/tip/eu-report/D05.1_Publish_on_translating_a_very-high-level_description.pdf
.. _`Technical reports`: index-report.html

.. _`getting started`: getting-started.html
.. _`Extreme Programming`: http://www.extremeprogramming.org/

.. _fast: faq.html#how-fast-is-pypy
.. _`very compliant`: cpython_differences.html

.. _`RPython`: coding-guide.html#rpython

.. _Python: http://docs.python.org/reference/
.. _Psyco: http://psyco.sourceforge.net
.. _stackless: stackless.html
.. _`generate Just-In-Time Compilers`: jit/index.html
.. _`JIT Generation in PyPy`: jit/index.html

.. include:: _ref.txt

