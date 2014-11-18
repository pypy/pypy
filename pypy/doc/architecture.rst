Goals and Architecture Overview
===============================

.. contents::

This document gives an overview of the goals and architecture of PyPy. If you're
interested in :ref:`using PyPy <using-pypy>` or :ref:`hacking on it <developing-pypy>`,
have a look at our :ref:`getting started <getting-started-index>` section.


Mission statement
-----------------

We aim to provide a compliant, flexible and fast implementation of the Python_
Language which uses the RPython toolchain to enable new advanced high-level
features without having to encode the low-level details.  We call this PyPy.

.. _Python: http://docs.python.org/reference/


High Level Goals
----------------

Our main motivation for developing the translation framework is to
provide a full featured, customizable, :ref:`fast <how-fast-is-pypy>` and
:doc:`very compliant <cpython_differences>` Python
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


.. _python-interpreter:

PyPy Python Interpreter
-----------------------

PyPy's *Python Interpreter* is written in RPython and implements the
full Python language.  This interpreter very closely emulates the
behavior of CPython.  It contains the following key components:

- a bytecode compiler responsible for producing Python code objects
  from the source code of a user application;

- a :doc:`bytecode evaluator <interpreter>` responsible for interpreting
  Python code objects;

- a :ref:`standard object space <standard-object-space>`, responsible for creating and manipulating
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

This division between bytecode evaluator and object space gives a lot of
flexibility.  One can plug in different :doc:`object spaces <objspace>` to get
different or enriched behaviours of the Python objects.
