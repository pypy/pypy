============================
Getting Started with RPython
============================

.. contents::

.. warning::

    Please `read this FAQ entry`_ first!

.. _`read this FAQ entry`: http://doc.pypy.org/en/latest/faq.html#do-i-have-to-rewrite-my-programs-in-rpython

RPython is a subset of Python that can be statically compiled. The PyPy
interpreter is written mostly in RPython (with pieces in Python), while
the RPython compiler is written in Python. The hard to understand part
is that Python is a meta-programming language for RPython, that is,
"being valid RPython" is a question that only makes sense on the
live objects **after** the imports are done.
This might require more explanation. You start writing RPython from
``entry_point``, a good starting point is
``rpython/translator/goal/targetnopstandalone.py``. This does not do all that
much, but is a start. Now if code analyzed (in this case ``entry_point``)
calls some functions, those calls will be followed. Those followed calls
have to be RPython themselves (and everything they call etc.), however not
entire module files. To show how you can use metaprogramming, we can do
a silly example (note that closures are not RPython)::

  def generator(operation):
      if operation == 'add':
         def f(a, b):
             return a + b
      else:
         def f(a, b):
             return a - b
      return f

  add = generator('add')
  sub = generator('sub')

  def entry_point(argv):
      print add(sub(int(argv[1]), 3) 4)
      return 0

In this example ``entry_point`` is RPython,  ``add`` and ``sub`` are RPython,
however, ``generator`` is not.

The following introductory level articles are available:

* Laurence Tratt -- `Fast Enough VMs in Fast Enough Time`_.

* `How to write interpreters in RPython`_ and `part 2`_ by Andrew Brown.

.. _`Fast Enough VMs in Fast Enough Time`: http://tratt.net/laurie/tech_articles/articles/fast_enough_vms_in_fast_enough_time

.. _`How to write interpreters in RPython`: http://morepypy.blogspot.com/2011/04/tutorial-writing-interpreter-with-pypy.html

.. _`part 2`: http://morepypy.blogspot.com/2011/04/tutorial-part-2-adding-jit.html

.. _`try out the translator`:

Trying out the translator
-------------------------

The translator is a tool based on the PyPy interpreter which can translate
sufficiently static RPython programs into low-level code (in particular it can
be used to translate the `full Python interpreter`_). To be able to experiment with it
you need to download and install the usual (CPython) version of:

  * Pygame_
  * `Dot Graphviz`_

To start the interactive translator shell do::

    cd rpython
    python bin/translatorshell.py

Test snippets of translatable code are provided in the file
``rpython/translator/test/snippet.py``, which is imported under the name
``snippet``.  For example::

    >>> t = Translation(snippet.is_perfect_number, [int])
    >>> t.view()

After that, the graph viewer pops up, that lets you interactively inspect the
flow graph. To move around, click on something that you want to inspect.
To get help about how to use it, press 'H'. To close it again, press 'Q'.

Trying out the type annotator
+++++++++++++++++++++++++++++

We have a type annotator that can completely infer types for functions like
``is_perfect_number`` (as well as for much larger examples)::

    >>> t.annotate()
    >>> t.view()

Move the mouse over variable names (in red) to see their inferred types.


Translating the flow graph to C code
++++++++++++++++++++++++++++++++++++

The graph can be turned into C code::

   >>> t.rtype()
   >>> lib = t.compile_c()

The first command replaces the operations with other low level versions that
only use low level types that are available in C (e.g. int). The compiled
version is now in a ``.so`` library. You can run it say using ctypes:

   >>> f = get_c_function(lib, snippet.is_perfect_number)
   >>> f(5)
   0
   >>> f(6)
   1

A slightly larger example
+++++++++++++++++++++++++

There is a small-to-medium demo showing the translator and the annotator::

    python bin/rpython --view --annotate translator/goal/bpnn.py

This causes ``bpnn.py`` to display itself as a call graph and class
hierarchy.  Clicking on functions shows the flow graph of the particular
function.  Clicking on a class shows the attributes of its instances.  All
this information (call graph, local variables' types, attributes of
instances) is computed by the annotator.

To turn this example to C code (compiled to the executable ``bpnn-c``),
type simply::

    python bin/rpython translator/goal/bpnn.py


Translating Full Programs
+++++++++++++++++++++++++

To translate full RPython programs, there is the script ``translate.py`` in
``rpython/translator/goal``. Examples for this are a slightly changed version of
Pystone::

    python bin/rpython translator/goal/targetrpystonedalone

This will produce the executable "targetrpystonedalone-c".

The largest example of this process is to translate the `full Python
interpreter`_. There is also an FAQ about how to set up this process for `your
own interpreters`_.

There are several environment variables you can find useful while playing with the RPython:

``PYPY_USESSION_DIR``
    RPython uses temporary session directories to store files that are generated during the
    translation process(e.g., translated C files). ``PYPY_USESSION_DIR`` serves as a base directory for these session
    dirs. The default value for this variable is the system's temporary dir.

``PYPY_USESSION_KEEP``
    By default RPython keeps only the last ``PYPY_USESSION_KEEP`` (defaults to 3) session dirs inside ``PYPY_USESSION_DIR``.
    Increase this value if you want to preserve C files longer (useful when producing lots of lldebug builds).

.. _`your own interpreters`: faq.html#how-do-i-compile-my-own-interpreters

.. _`start reading sources`:

Where to start reading the sources
----------------------------------

PyPy is made from parts that are relatively independent of each other.
You should start looking at the part that attracts you most (all paths are
relative to the PyPy top level directory).  You may look at our `directory reference`_
or start off at one of the following points:

*  `pypy/interpreter`_ contains the bytecode interpreter: bytecode dispatcher
   in `pypy/interpreter/pyopcode.py`_, frame and code objects in `pypy/interpreter/eval.py`_ and `pypy/interpreter/pyframe.py`_,
   function objects and argument passing in `pypy/interpreter/function.py`_ and `pypy/interpreter/argument.py`_,
   the object space interface definition in `pypy/interpreter/baseobjspace.py`_, modules in
   `pypy/interpreter/module.py`_ and `pypy/interpreter/mixedmodule.py`_.  Core types supporting the bytecode
   interpreter are defined in `pypy/interpreter/typedef.py`_.

*  `pypy/interpreter/pyparser`_ contains a recursive descent parser,
   and grammar files that allow it to parse the syntax of various Python
   versions. Once the grammar has been processed, the parser can be
   translated by the above machinery into efficient code.

*  `pypy/interpreter/astcompiler`_ contains the compiler.  This
   contains a modified version of the compiler package from CPython
   that fixes some bugs and is translatable.

*  `pypy/objspace/std`_ contains the `Standard object space`_.  The main file
   is `pypy/objspace/std/objspace.py`_.  For each type, the files ``xxxtype.py`` and
   ``xxxobject.py`` contain respectively the definition of the type and its
   (default) implementation.

*  `rpython/translator`_ contains the code analysis and generation stuff.
   Start reading from translator.py, from which it should be easy to follow
   the pieces of code involved in the various translation phases.

*  `rpython/annotator`_ contains the data model for the type annotation that
   can be inferred about a graph.  The graph "walker" that uses this is in
   `rpython/annotator/annrpython.py`_.

*  `rpython/rtyper`_ contains the code of the RPython typer. The typer transforms
   annotated flow graphs in a way that makes them very similar to C code so
   that they can be easy translated. The graph transformations are controlled
   by the code in `rpython/rtyper/rtyper.py`_. The object model that is used can
   be found in `rpython/rtyper/lltypesystem/lltype.py`_. For each RPython type
   there is a file rxxxx.py that contains the low level functions needed for
   this type.

*  `rpython/rlib`_ contains the `RPython standard library`_, things that you can
   use from rpython.

.. _`RPython standard library`: rlib.html

.. _optionaltool:


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

.. _`py.test testing tool`: http://pytest.org
.. _`py.test usage and invocations`: http://pytest.org/usage.html#usage

Special Introspection Features of the Untranslated Python Interpreter
---------------------------------------------------------------------

If you are interested in the inner workings of the PyPy Python interpreter,
there are some features of the untranslated Python interpreter that allow you
to introspect its internals.

Interpreter-level console
+++++++++++++++++++++++++

If you start an untranslated Python interpreter via::

    python pypy/bin/pyinteractive.py

If you press
<Ctrl-C> on the console you enter the interpreter-level console, a
usual CPython console.  You can then access internal objects of PyPy
(e.g. the `object space`_) and any variables you have created on the PyPy
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

.. _`object space`: objspace.html

Note that the prompt of the interpreter-level console is only '>>>' since
it runs on CPython level. If you want to return to PyPy, press <Ctrl-D> (under
Linux) or <Ctrl-Z>, <Enter> (under Windows).

You may be interested in reading more about the distinction between
`interpreter-level and app-level`_.

.. _`interpreter-level and app-level`: coding-guide.html#interpreter-level

.. _`trace example`:

Tracing bytecodes
+++++++++++++++++

You can use a simple tracing mode to monitor the interpretation of
bytecodes.  To enable it, set ``__pytrace__ = 1`` on the interactive
PyPy console::

    >>>> __pytrace__ = 1
    Tracing enabled
    >>>> x = 5
            <module>:           LOAD_CONST    0 (5)
            <module>:           STORE_NAME    0 (x)
            <module>:           LOAD_CONST    1 (None)
            <module>:           RETURN_VALUE    0 
    >>>> x
            <module>:           LOAD_NAME    0 (x)
            <module>:           PRINT_EXPR    0 
    5
            <module>:           LOAD_CONST    0 (None)
            <module>:           RETURN_VALUE    0 
    >>>>

Demos
-------

The `example-interpreter`_ repository contains an example interpreter
written using the RPython translation toolchain.

.. _`example-interpreter`: https://bitbucket.org/pypy/example-interpreter

Additional Tools for running (and hacking) PyPy
-----------------------------------------------

We use some optional tools for developing PyPy. They are not required to run
the basic tests or to get an interactive PyPy prompt but they help to
understand  and debug PyPy especially for the translation process.

graphviz & pygame for flow graph viewing (highly recommended)
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

graphviz and pygame are both necessary if you
want to look at generated flow graphs:

	graphviz: http://www.graphviz.org/Download.php

	pygame: http://www.pygame.org/download.shtml

py.test and the py lib
+++++++++++++++++++++++

The `py.test testing tool`_ drives all our testing needs.

We use the `py library`_ for filesystem path manipulations, terminal
writing, logging and some other support  functionality.

You don't necessarily need to install these two libraries because
we also ship them inlined in the PyPy source tree.

Getting involved
-----------------

PyPy employs an open development process.  You are invited to join our
`pypy-dev mailing list`_ or look at the other `contact
possibilities`_.  Usually we give out commit rights fairly liberally, so if you
want to do something with PyPy, you can become a committer. We are also doing
coding Sprints which are
separately announced and often happen around Python conferences such
as EuroPython or Pycon. Upcoming events are usually announced on `the blog`_.

.. _`full Python interpreter`: getting-started-python.html
.. _`the blog`: http://morepypy.blogspot.com
.. _`pypy-dev mailing list`: http://mail.python.org/mailman/listinfo/pypy-dev
.. _`contact possibilities`: index.html

.. _`py library`: http://pylib.org

.. _`Spidermonkey`: http://www.mozilla.org/js/spidermonkey/

.. _`.NET Framework SDK`: http://msdn.microsoft.com/netframework/
.. _Mono: http://www.mono-project.com/Main_Page
.. _`CLI backend`: cli-backend.html
.. _clr: clr-module.html

.. _`Dot Graphviz`:           http://www.graphviz.org/
.. _Pygame:                 http://www.pygame.org/
.. _Standard object space:  objspace.html#the-standard-object-space
.. _mailing lists:          index.html
.. _documentation:          index.html#project-documentation
.. _unit tests:             coding-guide.html#test-design

.. _`directory reference`: index.html#pypy-directory-reference

.. include:: _ref.txt
