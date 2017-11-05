Getting Started Developing With PyPy
====================================

.. contents::


Using Mercurial
---------------

PyPy development is based on Mercurial (hg).  If you are not used to
version control, the cycle for a new PyPy contributor goes typically
like this:

* Make an account on bitbucket_.

* Go to https://bitbucket.org/pypy/pypy/ and click "fork" (left
  icons).  You get a fork of the repository, e.g. in
  https://bitbucket.org/yourname/pypy/.

* Clone this new repo (i.e. the fork) to your local machine with the command 
  ``hg clone ssh://hg@bitbucket.org/yourname/pypy``.  It is a very slow
  operation but only ever needs to be done once.  See also 
  http://pypy.org/download.html#building-from-source .
  If you already cloned
  ``https://bitbucket.org/pypy/pypy`` before, even if some time ago,
  then you can reuse the same clone by editing the file ``.hg/hgrc`` in
  your clone to contain the line ``default =
  ssh://hg@bitbucket.org/yourname/pypy``, and then do ``hg pull && hg
  up``.  If you already have such a clone but don't want to change it,
  you can clone that copy with ``hg clone /path/to/other/copy``, and
  then edit ``.hg/hgrc`` as above and do ``hg pull && hg up``.

* Now you have a complete copy of the PyPy repo.  Make a branch
  with a command like ``hg branch name_of_your_branch``.

* Edit things.  Use ``hg diff`` to see what you changed.  Use ``hg add``
  to make Mercurial aware of new files you added, e.g. new test files.
  Use ``hg status`` to see if there are such files.  Write and run tests!
  (See the rest of this page.)

* Commit regularly with ``hg commit``.  A one-line commit message is
  fine.  We love to have tons of commits; make one as soon as you have
  some progress, even if it is only some new test that doesn't pass yet,
  or fixing things even if not all tests pass.  Step by step, you are
  building the history of your changes, which is the point of a version
  control system.  (There are commands like ``hg log`` and ``hg up``
  that you should read about later, to learn how to navigate this
  history.)

* The commits stay on your machine until you do ``hg push`` to "push"
  them back to the repo named in the file ``.hg/hgrc``.  Repos are
  basically just collections of commits (a commit is also called a
  changeset): there is one repo per url, plus one for each local copy on
  each local machine.  The commands ``hg push`` and ``hg pull`` copy
  commits around, with the goal that all repos in question end up with
  the exact same set of commits.  By opposition, ``hg up`` only updates
  the "working copy" by reading the local repository, i.e. it makes the
  files that you see correspond to the latest (or any other) commit
  locally present.

* You should push often; there is no real reason not to.  Remember that
  even if they are pushed, with the setup above, the commits are (1)
  only in ``bitbucket.org/yourname/pypy``, and (2) in the branch you
  named.  Yes, they are publicly visible, but don't worry about someone
  walking around the thousands of repos on bitbucket saying "hah, look
  at the bad coding style of that guy".  Try to get into the mindset
  that your work is not secret and it's fine that way.  We might not
  accept it as is for PyPy, asking you instead to improve some things,
  but we are not going to judge you.

* The final step is to open a pull request, so that we know that you'd
  like to merge that branch back to the original ``pypy/pypy`` repo.
  This can also be done several times if you have interesting
  intermediate states, but if you get there, then we're likely to
  proceed to the next stage, which is...

* Get a regular account for pushing directly to
  ``bitbucket.org/pypy/pypy`` (just ask and you'll get it, basically).
  Once you have it you can rewrite your file ``.hg/hgrc`` to contain
  ``default = ssh://hg@bitbucket.org/pypy/pypy``.  Your changes will
  then be pushed directly to the official repo, but (if you follow these
  rules) they are still on a branch, and we can still review the
  branches you want to merge.

* If you get closer to the regular day-to-day development, you'll notice
  that we generally push small changes as one or a few commits directly
  to the branch ``default``.  Also, we often collaborate even if we are
  on other branches, which do not really "belong" to anyone.  At this
  point you'll need ``hg merge`` and learn how to resolve conflicts that
  sometimes occur when two people try to push different commits in
  parallel on the same branch.  But it is likely an issue for later ``:-)``

.. _bitbucket: https://bitbucket.org/


Running PyPy's unit tests
-------------------------

PyPy development always was and is still thoroughly test-driven.
We use the flexible `py.test testing tool`_ which you can `install independently
<http://pytest.org/latest/getting-started.html#getstarted>`_ and use for other projects.

The PyPy source tree comes with an inlined version of ``py.test``
which you can invoke by typing::

    python pytest.py -h

This is usually equivalent to using an installed version::

    py.test -h

If you encounter problems with the installed version
make sure you have the correct version installed which
you can find out with the ``--version`` switch.

You will need the `build requirements`_ to run tests successfully, since many of
them compile little pieces of PyPy and then run the tests inside that minimal
interpreter

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
.. _py.test usage and invocations: http://pytest.org/latest/usage.html#usage
.. _`build requirements`: build.html#install-build-time-dependencies

Special Introspection Features of the Untranslated Python Interpreter
---------------------------------------------------------------------

If you are interested in the inner workings of the PyPy Python interpreter,
there are some features of the untranslated Python interpreter that allow you
to introspect its internals.


Interpreter-level console
~~~~~~~~~~~~~~~~~~~~~~~~~

To start interpreting Python with PyPy, install a C compiler that is
supported by distutils and use Python 2.7 or greater to run PyPy::

    cd pypy
    python bin/pyinteractive.py

After a few seconds (remember: this is running on top of CPython), you should
be at the PyPy prompt, which is the same as the Python prompt, but with an
extra ">".

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

Also note that not all modules are available by default in this mode (for
example: ``_continuation`` needed by ``greenlet``) , you may need to use one of
``--withmod-...`` command line options.

You may be interested in reading more about the distinction between
:ref:`interpreter-level and app-level <interpreter-level>`.

pyinteractive.py options
~~~~~~~~~~~~~~~~~~~~~~~~

To list the PyPy interpreter command line options, type::

    cd pypy
    python bin/pyinteractive.py --help

pyinteractive.py supports most of the options that CPython supports too (in addition to a
large amount of options that can be used to customize pyinteractive.py).
As an example of using PyPy from the command line, you could type::

    python pyinteractive.py --withmod-time -c "from test import pystone; pystone.main(10)"

Alternatively, as with regular Python, you can simply give a
script name on the command line::

    python pyinteractive.py --withmod-time ../../lib-python/2.7/test/pystone.py 10

The ``--withmod-xxx`` option enables the built-in module ``xxx``.  By
default almost none of them are, because initializing them takes time.
If you want anyway to enable all built-in modules, you can use
``--allworkingmodules``.

See our :doc:`configuration sections <config/index>` for details about what all the commandline
options do.


.. _trace example:

Tracing bytecode and operations on objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

.. _py library: http://pylib.readthedocs.org/


Getting involved
----------------

PyPy employs an open development process.  You are invited to join our
`pypy-dev mailing list`_ or look at the other :ref:`contact
possibilities <contact>`.  Usually we give out commit rights fairly liberally, so if you
want to do something with PyPy, you can become a committer. We also run frequent
coding sprints which are separately announced and often happen around Python
conferences such as EuroPython or PyCon. Upcoming events are usually announced
on `the blog`_.

.. _the blog: http://morepypy.blogspot.com
.. _pypy-dev mailing list: http://mail.python.org/mailman/listinfo/pypy-dev


.. _start-reading-sources:

Where to start reading the sources
----------------------------------

PyPy is made from parts that are relatively independent of each other.
You should start looking at the part that attracts you most (all paths are
relative to the PyPy top level directory).  You may look at our :doc:`directory reference <dir-reference>`
or start off at one of the following points:

*  :source:`pypy/interpreter` contains the bytecode interpreter: bytecode dispatcher
   in :source:`pypy/interpreter/pyopcode.py`, frame and code objects in
   :source:`pypy/interpreter/eval.py` and :source:`pypy/interpreter/pyframe.py`,
   function objects and argument passing in :source:`pypy/interpreter/function.py`
   and :source:`pypy/interpreter/argument.py`, the object space interface
   definition in :source:`pypy/interpreter/baseobjspace.py`, modules in
   :source:`pypy/interpreter/module.py` and :source:`pypy/interpreter/mixedmodule.py`.
   Core types supporting the bytecode interpreter are defined in :source:`pypy/interpreter/typedef.py`.

*  :source:`pypy/interpreter/pyparser` contains a recursive descent parser,
   and grammar files that allow it to parse the syntax of various Python
   versions. Once the grammar has been processed, the parser can be
   translated by the above machinery into efficient code.

*  :source:`pypy/interpreter/astcompiler` contains the compiler.  This
   contains a modified version of the compiler package from CPython
   that fixes some bugs and is translatable.

*  :source:`pypy/objspace/std` contains the :ref:`Standard object space <standard-object-space>`.  The main file
   is :source:`pypy/objspace/std/objspace.py`.  For each type, the file
   ``xxxobject.py`` contains the implementation for objects of type ``xxx``,
   as a first approximation.  (Some types have multiple implementations.)
