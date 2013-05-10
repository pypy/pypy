Getting Started with PyPy's Development Process
===============================================

.. contents::

.. _start-reading-sources:

Where to start reading the sources
----------------------------------

PyPy is made from parts that are relatively independent of each other.
You should start looking at the part that attracts you most (all paths are
relative to the PyPy top level directory).  You may look at our :doc:`directory reference <dir-reference>`
or start off at one of the following points:

*  :source:`pypy/interpreter` contains the bytecode interpreter: bytecode dispatcher
   in :source:`pypy/interpreter/pyopcode.py`, frame and code objects in :source:`pypy/interpreter/eval.py` and :source:`pypy/interpreter/pyframe.py`,
   function objects and argument passing in :source:`pypy/interpreter/function.py` and :source:`pypy/interpreter/argument.py`,
   the object space interface definition in :source:`pypy/interpreter/baseobjspace.py`, modules in
   :source:`pypy/interpreter/module.py` and :source:`pypy/interpreter/mixedmodule.py`.  Core types supporting the bytecode
   interpreter are defined in :source:`pypy/interpreter/typedef.py`.

*  :source:`pypy/interpreter/pyparser` contains a recursive descent parser,
   and grammar files that allow it to parse the syntax of various Python
   versions. Once the grammar has been processed, the parser can be
   translated by the above machinery into efficient code.

*  :source:`pypy/interpreter/astcompiler` contains the compiler.  This
   contains a modified version of the compiler package from CPython
   that fixes some bugs and is translatable.

*  :source:`pypy/objspace/std` contains the :ref:`Standard object space <standard-object-space>`.  The main file
   is :source:`pypy/objspace/std/objspace.py`.  For each type, the files ``xxxtype.py`` and
   ``xxxobject.py`` contain respectively the definition of the type and its
   (default) implementation.


Running PyPy's unit tests
-------------------------

PyPy development always was and is still thoroughly test-driven.
We use the flexible `py.test testing tool`_ which you can `install independently
<http://pytest.org/getting-started.html>`_ and use for other projects.

The PyPy source tree comes with an inlined version of ``py.test``
which you can invoke by typing::

    python pytest.py -h

This is usually equivalent to using an installed version::

    py.test -h

If you encounter problems with the installed version
make sure you have the correct version installed which
you can find out with the ``--version`` switch.

Now on to running some tests.  PyPy has many different test directories
and you can use shell completion to point at directories or files::

    py.test pypy/interpreter/test/test_pyframe.py

    # or for running tests of a whole subdirectory
    py.test pypy/interpreter/

See `py.test usage and invocations`_ for some more generic info
on how you can run tests.

Beware trying to run "all" pypy tests by pointing to the root
directory or even the top level subdirectory ``pypy``.  It takes
hours and uses huge amounts of RAM and is not recommended.

To run CPython regression tests you can point to the ``lib-python``
directory::

    py.test lib-python/2.7/test/test_datetime.py

This will usually take a long time because this will run
the PyPy Python interpreter on top of CPython.  On the plus
side, it's usually still faster than doing a full translation
and running the regression test with the translated PyPy Python
interpreter.

.. _py.test testing tool: http://pytest.org
.. _py.test usage and invocations: http://pytest.org/usage.html#usage


Special Introspection Features of the Untranslated Python Interpreter
---------------------------------------------------------------------

If you are interested in the inner workings of the PyPy Python interpreter,
there are some features of the untranslated Python interpreter that allow you
to introspect its internals.


Interpreter-level console
~~~~~~~~~~~~~~~~~~~~~~~~~

If you start an untranslated Python interpreter via::

    python pypy/bin/pyinteractive.py

If you press
<Ctrl-C> on the console you enter the interpreter-level console, a
usual CPython console.  You can then access internal objects of PyPy
(e.g. the :ref:`object space <objspace>`) and any variables you have created on the PyPy
prompt with the prefix ``w_``::

    >>>> a = 123
    >>>> <Ctrl-C>
    *** Entering interpreter-level console ***
    >>> w_a
    W_IntObject(123)

The mechanism works in both directions. If you define a variable with the ``w_`` prefix on the interpreter-level, you will see it on the app-level::

    >>> w_l = space.newlist([space.wrap(1), space.wrap("abc")])
    >>> <Ctrl-D>
    *** Leaving interpreter-level console ***

    KeyboardInterrupt
    >>>> l
    [1, 'abc']

Note that the prompt of the interpreter-level console is only '>>>' since
it runs on CPython level. If you want to return to PyPy, press <Ctrl-D> (under
Linux) or <Ctrl-Z>, <Enter> (under Windows).

You may be interested in reading more about the distinction between
:ref:`interpreter-level and app-level <interpreter-level>`.


.. _trace example:

Tracing bytecode and operations on objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the trace object space to monitor the interpretation
of bytecodes in connection with object space operations.  To enable
it, set ``__pytrace__=1`` on the interactive PyPy console::

    >>>> __pytrace__ = 1
    Tracing enabled
    >>>> a = 1 + 2
    |- <<<< enter <inline>a = 1 + 2 @ 1 >>>>
    |- 0    LOAD_CONST    0 (W_IntObject(1))
    |- 3    LOAD_CONST    1 (W_IntObject(2))
    |- 6    BINARY_ADD
      |-    add(W_IntObject(1), W_IntObject(2))   -> W_IntObject(3)
    |- 7    STORE_NAME    0 (a)
      |-    hash(W_StringObject('a'))   -> W_IntObject(-468864544)
      |-    int_w(W_IntObject(-468864544))   -> -468864544
    |-10    LOAD_CONST    2 (<W_NoneObject()>)
    |-13    RETURN_VALUE
    |- <<<< leave <inline>a = 1 + 2 @ 1 >>>>


Demos
-----

The `example-interpreter`_ repository contains an example interpreter
written using the RPython translation toolchain.

.. _example-interpreter: https://bitbucket.org/pypy/example-interpreter


Additional Tools for running (and hacking) PyPy
-----------------------------------------------

We use some optional tools for developing PyPy. They are not required to run
the basic tests or to get an interactive PyPy prompt but they help to
understand  and debug PyPy especially for the translation process.


graphviz & pygame for flow graph viewing (highly recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

graphviz and pygame are both necessary if you
want to look at generated flow graphs:

	graphviz: http://www.graphviz.org/Download.php

	pygame: http://www.pygame.org/download.shtml


py.test and the py lib
~~~~~~~~~~~~~~~~~~~~~~

The `py.test testing tool`_ drives all our testing needs.

We use the `py library`_ for filesystem path manipulations, terminal
writing, logging and some other support  functionality.

You don't necessarily need to install these two libraries because
we also ship them inlined in the PyPy source tree.


Getting involved
----------------

PyPy employs an open development process.  You are invited to join our
`pypy-dev mailing list`_ or look at the other :ref:`contact
possibilities <contact>`.  Usually we give out commit rights fairly liberally, so if you
want to do something with PyPy, you can become a committer. We are also doing
coding Sprints which are
separately announced and often happen around Python conferences such
as EuroPython or Pycon. Upcoming events are usually announced on `the blog`_.

.. _the blog: http://morepypy.blogspot.com
.. _pypy-dev mailing list: http://python.org/mailman/listinfo/pypy-dev

.. _py library: http://pylib.org
