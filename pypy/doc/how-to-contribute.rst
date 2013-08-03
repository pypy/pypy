How to contribute to PyPy
-------------------------

This page describes how to contribute to the PyPy project. The first thing
to remember is that PyPy project is very different than most projects out there.
It's also different from a classic compiler project, so academic courses
about compilers often don't apply or lead in the wrong direction.

Don't just hack
---------------

The first and most important rule how not to contribute to PyPy is
"just hacking". This won't work. There are two major reasons why not
-- build times are large and PyPy has very thick layer separation which
make it harder to "just hack a feature".

Test driven development
-----------------------

Instead, we practice a lot of test driven development. This is partly because
of very high quality requirements for compilers and partly because there is
simply no other way to get around such complex project, that will keep you sane.
There are probably people out there who are smart enough not to need it, we're
not one of those. You may consider familiarizing yourself with `pytest`_,
since this is a tool we use for tests.
This leads to the next issue:

Layers
------

PyPy has layers. Just like Ogres or onions.
Those layers help us keep the respective parts separated enough
to be worked on independently and make the complexity manageable. This is,
again, just a sanity requirement for such a complex project. For example writing
a new optimization for the JIT usually does **not** involve touching a Python
interpreter at all or the JIT assembler backend or the garbage collector.
Instead it requires writing small tests in
``rpython/jit/metainterp/optimizeopt/test/test_*`` and fixing files there.
After that, you can just compile PyPy and things should just work.

The short list of layers for further reading. For each of those layers, a good
entry point is a test subdirectory in respective directories. It usually
describes (better or worse) the interfaces between the submodules. For the
``pypy`` subdirectory, most tests are small snippets of python programs that
check for correctness (calls ``AppTestXxx``) that will call the appropriate
part of the interpreter. For the ``rpython`` directory, most tests are small
RPython interpreters that perform certain tasks. To see how they translate
to low-level graphs, run them with ``--view``. To see small interpreters
with a JIT compiler, use ``--viewloops`` option.

* **python interpreter** - it's the part implemented in the ``pypy/`` directory.
  It's implemented in RPython, which is a high level static language with
  classes, garbage collection, just-in-time compiler generation and the ability
  to call C. A cool part about it is that it can be run untranslated, so all
  the tests are runnable without translating PyPy.

  **interpreter** contains the interpreter core

  **objspace** contains implementations of various objects exported to
  the Python layer

  **module** directory contains extension modules written in RPython

* **rpython compiler** that resides in ``rpython/annotator`` and
  ``rpython/rtyper`` directories. Consult `introduction to RPython`_ for
  further reading

* **JIT generator** lives in ``rpython/jit`` directory. optimizations live
  in ``rpython/jit/metainterp/optimizeopt``, the main JIT in
  ``rpython/jit/metainterp`` (runtime part) and
  ``rpython/jit/codewriter`` (translation-time part). Backends live in
  ``rpython/jit/backend``.

* **garbage collection** lives in ``rpython/memory``

The rest of directories serve specific niche goal and are unlikely a good
entry point.

.. _`introduction to RPython`: getting-started-dev.html
.. _`pytest`: http://pytest.org/
