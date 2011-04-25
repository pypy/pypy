===============================================================================
Getting Started with the Translation Toolchain and Development Process
===============================================================================

.. contents::

.. _`try out the translator`:

Trying out the translator
------------------------- 

The translator is a tool based on the PyPy interpreter which can translate
sufficiently static Python programs into low-level code (in particular it can
be used to translate the `full Python interpreter`_). To be able to use it
you need to (if you want to look at the flowgraphs, which you obviously
should):

  * Download and install Pygame_.

  * Download and install `Dot Graphviz`_ 

To start the interactive translator shell do::

    cd pypy
    python bin/translatorshell.py

Test snippets of translatable code are provided in the file
``pypy/translator/test/snippet.py``, which is imported under the name
``snippet``.  For example::

    >>> t = Translation(snippet.is_perfect_number)
    >>> t.view()
        
After that, the graph viewer pops up, that lets you interactively inspect the
flow graph. To move around, click on something that you want to inspect.
To get help about how to use it, press 'H'. To close it again, press 'Q'.

Trying out the type annotator
+++++++++++++++++++++++++++++

We have a type annotator that can completely infer types for functions like
``is_perfect_number`` (as well as for much larger examples)::

    >>> t.annotate([int])
    >>> t.view()

Move the mouse over variable names (in red) to see their inferred types.


Translating the flow graph to C code
++++++++++++++++++++++++++++++++++++

The graph can be turned into C code::

   >>> t.rtype()
   >>> f = t.compile_c()

The first command replaces the operations with other low level versions that
only use low level types that are available in C (e.g. int). To try out the
compiled version::

   >>> f(5)
   False
   >>> f(6)
   True

Translating the flow graph to CLI or JVM code
+++++++++++++++++++++++++++++++++++++++++++++

PyPy also contains a `CLI backend`_ and JVM backend which
can translate flow graphs into .NET executables or a JVM jar
file respectively.  Both are able to translate the entire
interpreter.  You can try out the CLI and JVM backends
from the interactive translator shells as follows::

    >>> def myfunc(a, b): return a+b
    ... 
    >>> t = Translation(myfunc)
    >>> t.annotate([int, int])
    >>> f = t.compile_cli() # or compile_jvm()
    >>> f(4, 5)
    9

The object returned by ``compile_cli`` or ``compile_jvm``
is a wrapper around the real
executable: the parameters are passed as command line arguments, and
the returned value is read from the standard output.  

Once you have compiled the snippet, you can also try to launch the
executable directly from the shell. You will find the 
executable in one of the ``/tmp/usession-*`` directories::

    # For CLI:
    $ mono /tmp/usession-trunk-<username>/main.exe 4 5
    9

    # For JVM:
    $ java -cp /tmp/usession-trunk-<username>/pypy pypy.Main 4 5
    9

To translate and run for the CLI you must have the SDK installed: Windows
users need the `.NET Framework SDK`_, while Linux and Mac users
can use Mono_.  To translate and run for the JVM you must have a JDK 
installed (at least version 5) and ``java``/``javac`` on your path.

A slightly larger example
+++++++++++++++++++++++++

There is a small-to-medium demo showing the translator and the annotator::

    cd demo
    ../pypy/translator/goal/translate.py --view --annotate bpnn.py

This causes ``bpnn.py`` to display itself as a call graph and class
hierarchy.  Clicking on functions shows the flow graph of the particular
function.  Clicking on a class shows the attributes of its instances.  All
this information (call graph, local variables' types, attributes of
instances) is computed by the annotator.

To turn this example to C code (compiled to the executable ``bpnn-c``),
type simply::

    ../pypy/translator/goal/translate.py bpnn.py


Translating Full Programs
+++++++++++++++++++++++++

To translate full RPython programs, there is the script ``translate.py`` in
``translator/goal``. Examples for this are a slightly changed version of
Pystone::

    cd pypy/translator/goal
    python translate.py targetrpystonedalone

This will produce the executable "targetrpystonedalone-c".

The largest example of this process is to translate the `full Python
interpreter`_. There is also an FAQ about how to set up this process for `your
own interpreters`_.

.. _`your own interpreters`: faq.html#how-do-i-compile-my-own-interpreters

.. _`start reading sources`: 

Where to start reading the sources
---------------------------------- 

PyPy is made from parts that are relatively independent from each other.
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
   and input data files that allow it to parse both Python 2.3 and 2.4
   syntax.  Once the input data has been processed, the parser can be
   translated by the above machinery into efficient code.
 
*  `pypy/interpreter/astcompiler`_ contains the compiler.  This
   contains a modified version of the compiler package from CPython
   that fixes some bugs and is translatable.  That the compiler and
   parser are translatable is new in 0.8.0 and it makes using the
   resulting binary interactively much more pleasant.

*  `pypy/objspace/std`_ contains the `Standard object space`_.  The main file
   is `pypy/interpreter/objspace.py`_.  For each type, the files ``xxxtype.py`` and
   ``xxxobject.py`` contain respectively the definition of the type and its
   (default) implementation.

*  `pypy/objspace`_ contains a few other object spaces: the `pypy/objspace/thunk.py`_,
   `pypy/objspace/trace`_ and `pypy/objspace/flow`_ object spaces.  The latter is a relatively short piece
   of code that builds the control flow graphs when the bytecode interpreter
   runs in it.

*  `pypy/translator`_ contains the code analysis and generation stuff.
   Start reading from translator.py, from which it should be easy to follow
   the pieces of code involved in the various translation phases.

*  `pypy/annotation`_ contains the data model for the type annotation that
   can be inferred about a graph.  The graph "walker" that uses this is in
   `pypy/annotation/annrpython.py`_.

*  `pypy/rpython`_ contains the code of the RPython typer. The typer transforms
   annotated flow graphs in a way that makes them very similar to C code so
   that they can be easy translated. The graph transformations are controlled
   by the stuff in `pypy/rpython/rtyper.py`_. The object model that is used can
   be found in `pypy/rpython/lltypesystem/lltype.py`_. For each RPython type
   there is a file rxxxx.py that contains the low level functions needed for
   this type.

*  `pypy/rlib`_ contains the RPython standard library, things that you can
   use from rpython.

.. _optionaltool: 


Running PyPy's unit tests
-------------------------

PyPy development always was and is still thorougly test-driven. 
We use the flexible `py.test testing tool`_ which you can `install independently
<http://pytest.org/getting-started.html>`_ and use indepedently
from PyPy for other projects.

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

    py.test lib-python/2.7.0/test/test_datetime.py

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

    python pypy/bin/py.py

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

Tracing bytecode and operations on objects
++++++++++++++++++++++++++++++++++++++++++ 

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
-------

The `demo/`_ directory contains examples of various aspects of PyPy,
ranging from running regular Python programs (that we used as compliance goals) 
over experimental distribution mechanisms to examples translating 
sufficiently static programs into low level code. 

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

CTypes on Python 2.4
++++++++++++++++++++++++++++

`ctypes`_ is included in CPython 2.5 and higher.  CPython 2.4 users needs to
install it if they want to run low-level tests. See
the `download page of ctypes`_.

.. _`download page of ctypes`: https://sourceforge.net/projects/ctypes/files/
.. _`ctypes`: http://starship.python.net/crew/theller/ctypes/

.. _`py.test`:

py.test and the py lib 
+++++++++++++++++++++++

The `py.test testing tool`_ drives all our testing needs.

We use the `py library`_ for filesystem path manipulations, terminal
writing, logging and some other support  functionality.

You don't neccessarily need to install these two libraries because 
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
.. _`pypy-dev mailing list`: http://codespeak.net/mailman/listinfo/pypy-dev
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
.. _documentation:          docindex.html 
.. _unit tests:             coding-guide.html#test-design

.. _`directory reference`: docindex.html#directory-reference

.. include:: _ref.rst

