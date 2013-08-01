==============================================
Unipycation: A Language Composition Experiment
==============================================

Unipycation is an experimental composition of a Python interpreter (PyPy
http://pypy.org/) and a Prolog interpreter (Pyrolog by Carl Friedrich
Bolz https://bitbucket.org/cfbolz/pyrolog). The languages are composed
using RPython, meaning that the entire composition is meta-traced.

The goal of the project is to identify the challenges associated with composing 
programming languages whose paradigms differ vastly.

Building
========

Check out pyrolog somewhere::

    $ hg clone https://vext01@bitbucket.org/cfbolz/pyrolog

Add pyrolog to the PYTHONPATH::

    $ export PYTHONPATH=/path/to/pyrolog/checkout

Get the unipycation sources::

    $ hg clone https://vext01@bitbucket.org/vext01/pypy

Switch into the unipycation branch::

    $  hg update -C unipycation

And begin translation::

    $ rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py --withmod-unipycation

On a 64-bit architecture this process will consume about 8GB of memory at peak.

The resulting pypy-c binary is the composed Python/Prolog compiler.

Using Unipycation
=================

For the moment, the languages are composed without any adjustments to
syntax. In other words, communication between Python and Prolog is in
the form of an API. Better syntactic composition will come later.

Currently all programs begin in Python.

There are two interfaces to unipycation:

 * A low-level logic programming interface.
 * A high-level logic programming interface.

High-Level Interface
--------------------

The high-level interface provides a concise way to execute 90% of the
most common Prolog usage patterns from Python. For example::

        # Find all combinations of two lists which when concatenated
        # give [1, 2, 3, 4, 5]

        import uni                                                              
                                                                                
        e = uni.Engine("""                                                      
            app([], X, X).                                                      
            app([H | T1], T2, [H | T3]) :- app(T1, T2, T3).                     
        """)                                                                    
        e.db.app.many_solutions = True                                          
                                                                                
        for (x, y) in e.db.app(None, None, [1, 2, 3, 4, 5]):                    
            print("X = %s, Y = %s" % (x, y))

Limitations of the High-Level Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

 * Lists (which are automagically converted) must not have an undefined tail.
 * It is not possible to place variables inside terms/lists in a query.

If you need to do either of the above, then you must use the low-level
interface.

Low-Level Interface
-------------------

The low level interface gives more control at the cost of verbosity::

        # Enumerate all f(X, Y) pairs

        import unipycation as u

        e = u.CoreEngine("f(666, 667). f(222, 334). f(777, 778).")
        vs = [X, Y] = [u.Var(), u.Var()]

        t = u.Term('f', vs)
        it = e.query_iter(t, vs)

        for sol in it:
            print("Solution: X=%s, Y=%s" % (sol[X], sol[Y]))

"Gotchas" with the Low-Level Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  * Note that variables retain their binding even after the result
    dictionary has fallen out of scope. Be careful when re-using variable
    instances between queries.
  * The second argument to CoreEngine.query_single() and
    CoreEngine.query_iter() must be exactly the list of free variables
    in the query.

Authors
=======

Unpycation is authored by Edd Barrett and Carl Friedrich Bolz.
