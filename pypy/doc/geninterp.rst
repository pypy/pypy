The Interpreter-Level backend
-----------------------------

http://codespeak.net/pypy/trunk/pypy/translator/geninterplevel.py

Motivation
++++++++++

PyPy often makes use of `application-level`_ helper methods.
The idea of the 'geninterplevel' backend is to automatically transform
such application level implementations to their equivalent representation
at interpreter level.  Then, the RPython to C translation hopefully can
produce more efficient code than always re-interpreting these methods.

One property of translation from application level Python to
Python is, that the produced code does the same thing as the
corresponding interpreted code, but no interpreter is needed
any longer to execute this code.

.. _`application-level`: coding-guide.html#app-preferable

Bootstrap issue
+++++++++++++++

One issue we had so far was of bootstrapping: some pieces of the
interpreter (e.g. exceptions) were written in geninterped code.
It is unclear how much of it is left, thought.

That bootstrap issue is (was?) solved by invoking a new bytecode interpreter
which runs on FlowObjspace. FlowObjspace is complete without
complicated initialization. It is able to do abstract interpretation
of any Rpythonic code, without actually implementing anything. It just
records all the operations the bytecode interpreter would have done by
building flowgraphs for all the code. What the Python backend does is
just to produce correct Python code from these flowgraphs and return
it as source code. In the produced code Python operations recorded in
the original flowgraphs are replaced by calls to the corresponding
methods in the `object space`_ interface.

.. _`object space`: objspace.html

Example
+++++++

.. _implementation: ../../pypy/translator/geninterplevel.py

Let's try a little example. You might want to look at the flowgraph that it
produces. Here, we directly run the Python translation and look at the
generated source. See also the header section of the implementation_ for the
interface::

    >>> from pypy.translator.geninterplevel import translate_as_module
    >>> entrypoint, source = translate_as_module("""
    ...
    ... def g(n):
    ...     i = 0
    ...     while n:
    ...         i = i + n
    ...         n = n - 1
    ...     return i
    ...
    ... """)

This call has invoked a PyPy bytecode interpreter running on FlowObjspace,
recorded every possible codepath into a flowgraph, and then rendered the
following source code:: 

    #!/bin/env python
    # -*- coding: LATIN-1 -*-

    def initapp2interpexec(space):
      """NOT_RPYTHON"""

      def g(space, w_n_1):
        goto = 3 # startblock
        while True:

            if goto == 1:
                v0 = space.is_true(w_n)
                if v0 == True:
                    goto = 2
                else:
                    goto = 4

            if goto == 2:
                w_1 = space.add(w_0, w_n)
                w_2 = space.sub(w_n, gi_1)
                w_n, w_0 = w_2, w_1
                goto = 1
                continue

            if goto == 3:
                w_n, w_0 = w_n_1, gi_0
                goto = 1
                continue

            if goto == 4:
                return w_0

      fastf_g = g

      g3dict = space.newdict()
      gs___name__ = space.new_interned_str('__name__')
      gs_app2interpexec = space.new_interned_str('app2interpexec')
      space.setitem(g3dict, gs___name__, gs_app2interpexec)
      gs_g = space.new_interned_str('g')
      from pypy.interpreter import gateway
      gfunc_g = space.wrap(gateway.interp2app(fastf_g, unwrap_spec=[gateway.ObjSpace, gateway.W_Root]))
      space.setitem(g3dict, gs_g, gfunc_g)
      gi_1 = space.wrap(1)
      gi_0 = space.wrap(0)
      return g3dict

You see that actually a single function is produced:
``initapp2interpexec``. This is the function that you will call with a
space as argument. It defines a few functions and then does a number
of initialization steps, builds the global objects the function need,
and produces the PyPy function object ``gfunc_g``.

The return value is ``g3dict``, which contains a module name and the
function we asked for.

Let's have a look at the body of this code: The definition of ``g`` is
used as ``fast_g`` in the ``gateway.interp2app`` which constructs a
PyPy function object which takes care of argument unboxing (based on
the ``unwrap_spec``), and of invoking the original ``g``.

We look at the definition of ``g`` itself which does the actual
computation. Comparing to the flowgraph, you see a code block for
every block in the graph.  Since Python has no goto statement, the
jumps between the blocks are implemented by a loop that switches over
a ``goto`` variable.

::

    .       if goto == 1:
                v0 = space.is_true(w_n)
                if v0 == True:
                    goto = 2
                else:
                    goto = 4

This is the implementation of the "``while n:``". There is no implicit state,
everything is passed over to the next block by initializing its
input variables. This directly resembles the nature of flowgraphs.
They are completely stateless.


::

    .       if goto == 2:
                w_1 = space.add(w_0, w_n)
                w_2 = space.sub(w_n, gi_1)
                w_n, w_0 = w_2, w_1
                goto = 1
                continue

The "``i = i + n``" and "``n = n - 1``" instructions.
You see how every instruction produces a new variable.
The state is again shuffled around by assigning to the
input variables ``w_n`` and ``w_0`` of the next target, block 1.

Note that it is possible to rewrite this by re-using variables,
trying to produce nested blocks instead of the goto construction
and much more. The source would look much more like what we
used to write by hand. For the C backend, this doesn't make much
sense since the compiler optimizes it for us. For the Python interpreter it could
give a bit more speed. But this is a temporary format and will
get optimized anyway when we produce the executable.

Interplevel Snippets in the Sources
+++++++++++++++++++++++++++++++++++

Code written in application space can consist of complete files
to be translated, or they
can be tiny snippets scattered all over a source file, similar
to our example from above.

Translation of these snippets is done automatically and cached
in pypy/_cache with the modulename and the md5 checksum appended
to it as file name. If you have run your copy of pypy already,
this folder should exist and have some generated files in it.
These files consist of the generated code plus a little code
that auto-destructs the cached file (plus .pyc/.pyo versions)
if it is executed as __main__. On windows this means you can wipe
a cached code snippet clear by double-clicking it. Note also that
the auto-generated __init__.py file wipes the whole directory
when executed.
