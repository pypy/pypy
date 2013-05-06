==============================================
Getting Started with the Translation Toolchain
==============================================

.. contents::

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

Translating the flow graph to CLI or JVM code
+++++++++++++++++++++++++++++++++++++++++++++

PyPy also contains a `CLI backend`_ and JVM backend which
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

A slightly larger example
+++++++++++++++++++++++++

There is a small-to-medium demo showing the translator and the annotator::

    cd demo
    ../rpython/translator/goal/translate.py --view --annotate bpnn.py

This causes ``bpnn.py`` to display itself as a call graph and class
hierarchy.  Clicking on functions shows the flow graph of the particular
function.  Clicking on a class shows the attributes of its instances.  All
this information (call graph, local variables' types, attributes of
instances) is computed by the annotator.

To turn this example to C code (compiled to the executable ``bpnn-c``),
type simply::

    ../rpython/translator/goal/translate.py bpnn.py


Translating Full Programs
+++++++++++++++++++++++++

To translate full RPython programs, there is the script ``translate.py`` in
``rpython/translator/goal``. Examples for this are a slightly changed version of
Pystone::

    cd rpython/translator/goal
    python translate.py targetrpystonedalone

This will produce the executable "targetrpystonedalone-c".

The largest example of this process is to translate the `full Python
interpreter`_. There is also an FAQ about how to set up this process for `your
own interpreters`_.

.. _`your own interpreters`: faq.html#how-do-i-compile-my-own-interpreters

Sources
-------

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
