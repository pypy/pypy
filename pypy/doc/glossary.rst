.. include:: needswork.txt

.. _glossary:

********
Glossary
********

PyPy, like any large project, has developed a jargon of its own.  This
document gives brief definition of some of these terms and provides
links to more information.

.. if you add new entries, keep the alphabetical sorting!

.. glossary::

    annotator
        The component of the :term:`translator`\ 's :term:`toolchain` that performs a form
        of :term:`type inference` on the flow graph. See the `annotator pass`_
        in the documentation.

    application level
        applevel_ code is normal Python code running on top of the PyPy or
        :term:`CPython` interpreter (see :term:`interpreter level`)

    backend
        Code generator that converts an `RPython
        <coding-guide.html#restricted-python>`__ program to a `target
        language`_ using the PyPy :term:`toolchain`. A backend uses either the
        :term:`lltypesystem` or the :term:`ootypesystem`.

    compile-time
        In the context of the :term:`JIT`, compile time is when the JIT is
        generating machine code "just in time".

    CPython
        The "default" implementation of Python, written in C and
        distributed by the PSF_ on http://www.python.org.

    external function
        Functions that we don't want to implement in Python for various
        reasons (e.g. they need to make calls into the OS) and whose
        implementation will be provided by the backend.

    garbage collection framework
        Code that makes it possible to write `PyPy's garbage collectors`_
        in Python itself.

    interpreter level
        Code running at this level is part of the implementation of the
        PyPy interpreter and cannot interact normally with :term:`application
        level` code; it typically provides implementation for an object
        space and its builtins.

    jit
      `just in time compiler`_.

    llinterpreter
       Piece of code that is able to interpret flow graphs.  This is very
       useful for testing purposes, especially if you work on the :term:`RPython`
       Typer.

    lltypesystem
       A `C-like type model <rtyper.html#low-level-types>`__ that contains
       structs and pointers.  A :term:`backend` that uses this type system is also
       called a low-level backend.  The C backend uses this
       typesystem.

    low-level helper
        A function that the :term:`RTyper` can use a call to as part of implementing
        some operation in terms of the target :term:`type system`.

    mixed module
      a module that accesses PyPy's :term:`interpreter level`.  The name comes
      from the fact that the module's implementation can be a mixture of
      :term:`application level` and :term:`interpreter level` code.

    object space
       The `object space <objspace.html>`__ (often abbreviated to
       "objspace") creates all objects and knows how to perform operations
       on the objects. You may think of an object space as being a library
       offering a fixed API, a set of operations, with implementations
       that a) correspond to the known semantics of Python objects, b)
       extend or twist these semantics, or c) serve whole-program analysis
       purposes.

    ootypesystem
       An `object oriented type model <rtyper.html#object-oriented-types>`__
       containing classes and instances.  A :term:`backend` that uses this type system
       is also called a high-level backend.  The JVM and CLI backends
       all use this typesystem.

    prebuilt constant
       In :term:`RPython` module globals are considered constants.  Moreover,
       global (i.e. prebuilt) lists and dictionaries are supposed to be
       immutable ("prebuilt constant" is sometimes abbreviated to "pbc").

    promotion
       :term:`JIT` terminology.  *promotion* is a way of "using" a :term:`run-time`
       value at :term:`compile-time`, essentially by deferring compilation
       until the run-time value is known. See if `the jit docs`_ help.

    rpython
       `Restricted Python`_, a limited subset of the Python_ language.
       The limitations make :term:`type inference` possible.
       It is also the language that the PyPy interpreter itself is written
       in.

    rtyper
       Based on the type annotations, the `RPython Typer`_ turns the flow
       graph into one that fits the model of the target platform/:term:`backend`
       using either the :term:`lltypesystem` or the :term:`ootypesystem`.

    run-time
       In the context of the :term:`JIT`, run time is when the code the JIT has
       generated is executing.

    specialization
       A way of controlling how a specific function is handled by the
       :term:`annotator`.  One specialization is to treat calls to a function
       with different argument types as if they were calls to different
       functions with identical source.

    stackless
        Technology that enables various forms of non conventional control
        flow, such as coroutines, greenlets and tasklets.  Inspired by
        Christian Tismer's `Stackless Python <http://www.stackless.com>`__.

    standard interpreter
       It is the `subsystem implementing the Python language`_, composed
       of the bytecode interpreter and of the standard objectspace.

    toolchain
       The `annotator pass`_, `The RPython Typer`_, and various
       :term:`backend`\ s.

    transformation
       Code that modifies flowgraphs to weave in translation aspects

    translation-time
       In the context of the :term:`JIT`, translation time is when the PyPy
       source is being analyzed and the JIT itself is being created.

    translator
      Tool_ based on the PyPy interpreter which can translate
      sufficiently static Python programs into low-level code.

    type system
        The RTyper can target either the :term:`lltypesystem` or the :term:`ootypesystem`.

    type inference
       Deduces either partially or fully the type of expressions as
       described in this `type inference article on Wikipedia`_.
       PyPy's tool-chain own flavour of type inference is described
       in the `annotator pass`_ section.

.. _applevel: coding-guide.html#application-level
.. _`target language`: getting-started-dev.html#trying-out-the-translator
.. _`just in time compiler`: jit/index.html
.. _`the jit docs`: jit/index.html
.. _`type inference article on Wikipedia`: http://en.wikipedia.org/wiki/Type_inference
.. _`annotator pass`: translation.html#the-annotation-pass
.. _`The RPython Typer`: translation.html#the-rpython-typer
.. _`backends`: getting-started-dev.html#trying-out-the-translator
.. _Tool: getting-started-dev.html#trying-out-the-translator
.. _`PyPy's garbage collectors`: garbage_collection.html
.. _`Restricted Python`: coding-guide.html#restricted-python
.. _PSF: http://www.python.org/psf/
.. _Python: http://www.python.org
.. _`RPython Typer`: rtyper.html
.. _`subsystem implementing the Python language`: architecture.html#standard-interpreter

.. include:: _ref.txt
