Getting Started with RPython
============================

.. contents::

RPython is a subset of Python that can be statically compiled. The PyPy
interpreter is written mostly in RPython (with pieces in Python), while
the RPython compiler is written in Python. The hard to understand part
is that Python is a meta-programming language for RPython, that is,
RPython is considered from live objects **after** the imports are done.
This might require more explanation. You start writing RPython from
``entry_point``, a good starting point is
:source:`rpython/translator/goal/targetnopstandalone.py`. This does not do all that
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

A good introductory level articles are available:

* Laurence Tratt -- `Fast Enough VMs in Fast Enough Time`_.

* `How to write interpreters in RPython`_ and `part 2`_ by Andrew Brown.

.. _Fast Enough VMs in Fast Enough Time: http://tratt.net/laurie/tech_articles/articles/fast_enough_vms_in_fast_enough_time

.. _How to write interpreters in RPython: http://morepypy.blogspot.com/2011/04/tutorial-writing-interpreter-with-pypy.html

.. _part 2: http://morepypy.blogspot.com/2011/04/tutorial-part-2-adding-jit.html


.. _try-out-the-translator:

Trying out the translator
-------------------------

The translator is a tool based on the PyPy interpreter which can translate
sufficiently static RPython programs into low-level code (in particular it can
be used to translate the `full Python interpreter`_). To be able to experiment with it
you need to download and install the usual (CPython) version of:

  * Pygame_
  * `Dot Graphviz`_

.. _Pygame:                 http://www.pygame.org/
.. _Dot Graphviz:           http://www.graphviz.org/

To start the interactive translator shell do::

    cd rpython
    python bin/translatorshell.py

Test snippets of translatable code are provided in the file
:source:`rpython/translator/test/snippet.py`, which is imported under the name
``snippet``.  For example::

    >>> t = Translation(snippet.is_perfect_number, [int])
    >>> t.view()

After that, the graph viewer pops up, that lets you interactively inspect the
flow graph. To move around, click on something that you want to inspect.
To get help about how to use it, press 'H'. To close it again, press 'Q'.


Trying out the type annotator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We have a type annotator that can completely infer types for functions like
``is_perfect_number`` (as well as for much larger examples)::

    >>> t.annotate()
    >>> t.view()

Move the mouse over variable names (in red) to see their inferred types.


Translating the flow graph to C code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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


Translating the flow graph to CLI or JVM code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyPy also contains a :ref:`CLI backend <gencli>` and :ref:`JVM backend <genjvm>` which
can translate flow graphs into .NET executables or a JVM jar
file respectively.  Both are able to translate the entire
interpreter.  You can try out the CLI and JVM backends
from the interactive translator shells as follows::

    >>> def myfunc(a, b): return a+b
    ...
    >>> t = Translation(myfunc, [int, int])
    >>> t.annotate()
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
installed (at least version 6) and ``java``/``javac`` on your path.

.. _CLI backend: cli-backend.html
.. _.NET Framework SDK: http://msdn.microsoft.com/netframework/
.. _Mono: http://www.mono-project.com/Main_Page


A slightly larger example
~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~

To translate full RPython programs, there is the script ``translate.py`` in
:source:`rpython/translator/goal`. Examples for this are a slightly changed version of
Pystone::

    python bin/rpython translator/goal/targetrpystonedalone

This will produce the executable "targetrpystonedalone-c".

The largest example of this process is to translate the `full Python
interpreter`_. There is also an FAQ about how to set up this process for :ref:`your
own interpreters <compile-own-interpreters>`.

There are several environment variables you can find useful while playing with the RPython:

``PYPY_USESSION_DIR``
    RPython uses temporary session directories to store files that are generated during the
    translation process(e.g., translated C files). ``PYPY_USESSION_DIR`` serves as a base directory for these session
    dirs. The default value for this variable is the system's temporary dir.

``PYPY_USESSION_KEEP``
    By default RPython keeps only the last ``PYPY_USESSION_KEEP`` (defaults to 3) session dirs inside ``PYPY_USESSION_DIR``.
    Increase this value if you want to preserve C files longer (useful when producing lots of lldebug builds).


Sources
-------

*  :source:`rpython/translator` contains the code analysis and generation stuff.
   Start reading from translator.py, from which it should be easy to follow
   the pieces of code involved in the various translation phases.

*  :source:`rpython/annotator` contains the data model for the type annotation that
   can be inferred about a graph.  The graph "walker" that uses this is in
   :source:`rpython/annotator/annrpython.py`.

*  :source:`rpython/rtyper` contains the code of the RPython typer. The typer transforms
   annotated flow graphs in a way that makes them very similar to C code so
   that they can be easy translated. The graph transformations are controlled
   by the code in :source:`rpython/rtyper/rtyper.py`. The object model that is used can
   be found in :source:`rpython/rtyper/lltypesystem/lltype.py`. For each RPython type
   there is a file rxxxx.py that contains the low level functions needed for
   this type.

*  :source:`rpython/rlib` contains the :doc:`RPython standard library <rlib>`, things that you can
   use from rpython.


.. _full Python interpreter: http://pypy.readthedocs.org/en/latest/getting-started-python.html
