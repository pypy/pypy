==========================
Frequently Asked Questions
==========================

.. contents::


General
=======

-------------
What is PyPy?
-------------

PyPy is both:

 - a reimplementation of Python in Python, and

 - a framework for implementing interpreters and virtual machines for
   programming languages, especially dynamic languages.

PyPy tries to find new answers about ease of creation, flexibility,
maintainability and speed trade-offs for language implementations.
For further details see our `goal and architecture document`_ .

.. _`goal and architecture document`: architecture.html


.. _`drop in replacement`:

------------------------------------------
Is PyPy a drop in replacement for CPython?
------------------------------------------

Almost!

The mostly likely stumbling block for any given project is support for
`extension modules`_.  PyPy supports a continually growing
number of extension modules, but so far mostly only those found in the
standard library.

The language features (including builtin types and functions) are very
complete and well tested, so if your project does not use many
extension modules there is a good chance that it will work with PyPy.

We list the differences we know about in `cpython differences`_.

--------------------------------------------
Do CPython Extension modules work with PyPy?
--------------------------------------------

We have experimental support for CPython extension modules, so
they run with minor changes.  This has been a part of PyPy since
the 1.4 release, but support is still in beta phase.  CPython
extension modules in PyPy are often much slower than in CPython due to
the need to emulate refcounting.  It is often faster to take out your
CPython extension and replace it with a pure python version that the
JIT can see.

We fully support ctypes-based extensions.

For information on which third party extensions work (or do not work) 
with PyPy see the `compatibility wiki`_.


.. _`extension modules`: cpython_differences.html#extension-modules
.. _`cpython differences`: cpython_differences.html
.. _`compatibility wiki`: https://bitbucket.org/pypy/compatibility/wiki/Home

---------------------------------
On which platforms does PyPy run?
---------------------------------

PyPy is regularly and extensively tested on Linux machines and on Mac
OS X and mostly works under Windows too (but is tested there less
extensively). PyPy needs a CPython running on the target platform to
bootstrap, as cross compilation is not really meant to work yet.
At the moment you need CPython 2.5 - 2.7
for the translation process. PyPy's JIT requires an x86 or x86_64 CPU.

------------------------------------------------
Which Python version (2.x?) does PyPy implement?
------------------------------------------------

PyPy currently aims to be fully compatible with Python 2.7. That means that
it contains the standard library of Python 2.7 and that it supports 2.7
features (such as set comprehensions).  

.. _threading:

-------------------------------------------------
Does PyPy have a GIL?  Why?
-------------------------------------------------

Yes, PyPy has a GIL.  Removing the GIL is very hard.  The first problem
is that our garbage collectors are not re-entrant.

------------------------------------------
How do I write extension modules for PyPy?
------------------------------------------

See `Writing extension modules for PyPy`__.

.. __: extending.html

-----------------
How fast is PyPy?
-----------------
This really depends on your code.
For pure Python algorithmic code, it is very fast.  For more typical
Python programs we generally are 3 times the speed of Cpython 2.6 .
You might be interested in our `benchmarking site`_ and our 
`jit documentation`_.

.. _`benchmarking site`: http://speed.pypy.org

.. _`jit documentation`: jit/index.html


.. _`prolog and javascript`:

--------------------------------------------------------------------------
Can I use PyPy's translation toolchain for other languages besides Python?
--------------------------------------------------------------------------

Yes. The toolsuite that translates the PyPy interpreter is quite
general and can be used to create optimized versions of interpreters
for any language, not just Python.  Of course, these interpreters
can make use of the same features that PyPy brings to Python:
translation to various languages, stackless features,
garbage collection, implementation of various things like arbitrarily long
integers, etc. 

Currently, we have preliminary versions of a JavaScript interpreter
(Leonardo Santagada as his Summer of PyPy project), a `Prolog interpreter`_
(Carl Friedrich Bolz as his Bachelor thesis), and a `SmallTalk interpreter`_
(produced during a sprint).  On the `PyPy bitbucket page`_ there is also a
Scheme and an Io implementation; both of these are unfinished at the moment.

.. _`Prolog interpreter`: https://bitbucket.org/cfbolz/pyrolog/
.. _`SmallTalk interpreter`: http://dx.doi.org/10.1007/978-3-540-89275-5_7
.. _`PyPy bitbucket page`: https://bitbucket.org/pypy/


Development
===========

-----------------------------------------------------------
How do I get into PyPy development?  Can I come to sprints?
-----------------------------------------------------------

Certainly you can come to sprints! We always welcome newcomers and try
to help them as much as possible to get started with the project.  We
provide tutorials and pair them with experienced PyPy
developers. Newcomers should have some Python experience and read some
of the PyPy documentation before coming to a sprint.

Coming to a sprint is usually the best way to get into PyPy development.
If you get stuck or need advice, `contact us`_. IRC is
the most immediate way to get feedback (at least during some parts of the day;
most PyPy developers are in Europe) and the `mailing list`_ is better for long
discussions.

.. _`contact us`: index.html
.. _`mailing list`: http://python.org/mailman/listinfo/pypy-dev

-------------------------------------------------------------
OSError: ... cannot restore segment prot after reloc... Help?
-------------------------------------------------------------

On Linux, if SELinux is enabled, you may get errors along the lines of
"OSError: externmod.so: cannot restore segment prot after reloc: Permission
denied." This is caused by a slight abuse of the C compiler during
configuration, and can be disabled by running the following command with root
privileges::

    # setenforce 0

This will disable SELinux's protection and allow PyPy to configure correctly.
Be sure to enable it again if you need it!


The PyPy translation tool chain
===============================

---------------------------------------------
Can PyPy compile normal Python programs to C?
---------------------------------------------

No, PyPy is not a Python compiler.

In Python, it is mostly impossible to *prove* anything about the types
that a program will manipulate by doing a static analysis.  It should be
clear if you are familiar with Python, but if in doubt see [BRETT]_.

If you want a fast Python program, please use our JIT_ instead.

.. _JIT: jit/index.html

.. [BRETT] Brett Cannon,
           Localized Type Inference of Atomic Types in Python,
           http://citeseer.ist.psu.edu/viewdoc/summary?doi=10.1.1.90.3231

.. _`PyPy's RPython`: 

------------------------------
What is this RPython language?
------------------------------

RPython is a restricted subset of the Python language.   It is used for 
implementing dynamic language interpreters within the PyPy toolchain.  The
restrictions ensure that type inference (and so, ultimately, translation
to other languages) of RPython programs is possible. 

The property of "being RPython" always applies to a full program, not to single
functions or modules (the translation toolchain does a full program analysis).
The translation toolchain follows all calls
recursively and discovers what belongs to the program and what does not.

RPython program restrictions mostly limit the ability
to mix types in arbitrary ways. RPython does not allow the binding of two
different types in the same variable. In this respect (and in some others) it
feels a bit like Java. Other features not allowed in RPython are the use of
special methods (``__xxx__``) except ``__init__`` and ``__del__``, and the
use of reflection capabilities (e.g. ``__dict__``).

You cannot use most existing standard library modules from RPython.  The
exceptions are
some functions in ``os``, ``math`` and ``time`` that have native support.

To read more about the RPython limitations read the `RPython description`_.

.. _`RPython description`: coding-guide.html#restricted-python

---------------------------------------------------------------
Does RPython have anything to do with Zope's Restricted Python?
---------------------------------------------------------------

No.  `Zope's RestrictedPython`_ aims to provide a sandboxed 
execution environment for CPython.   `PyPy's RPython`_ is the implementation
language for dynamic language interpreters.  However, PyPy also provides 
a robust `sandboxed Python Interpreter`_. 

.. _`sandboxed Python Interpreter`: sandbox.html
.. _`Zope's RestrictedPython`: http://pypi.python.org/pypi/RestrictedPython

------------------------------------------------------
What's the ``"NOT_RPYTHON"`` I see in some docstrings?
------------------------------------------------------

If you put "NOT_RPYTHON" into the docstring of a function and that function is
found while trying to translate an RPython program, the translation process
stops and reports this as an error. You can therefore mark functions as
"NOT_RPYTHON" to make sure that they are never analyzed.


-------------------------------------------------------------------
Couldn't we simply take a Python syntax tree and turn it into Lisp?
-------------------------------------------------------------------

It's not necessarily nonsense, but it's not really The PyPy Way.  It's
pretty hard, without some kind of type inference, to translate this
Python::

    a + b

into anything significantly more efficient than this Common Lisp::

    (py:add a b)

And making type inference possible is what RPython is all about.

You could make ``#'py:add`` a generic function and see if a given CLOS
implementation is fast enough to give a useful speed (but I think the
coercion rules would probably drive you insane first).  -- mwh

--------------------------------------------
Do I have to rewrite my programs in RPython?
--------------------------------------------

No.  And you shouldn't try.  PyPy always runs your code in its own interpreter, which is a
full and compliant Python 2.7 interpreter.  RPython is only the
language in which parts of PyPy itself are written and extension
modules for it.  Not only is it not necessary for you to rewrite your
code in RPython, it probably won't give you any speed improvements if you 
try.

---------------------------------------------------
Which backends are there for the RPython toolchain?
---------------------------------------------------

Currently, there are backends for C_, the CLI_, and the JVM_.
All of these can translate the entire PyPy interpreter.
To learn more about backends take a look at the `translation document`_.

.. _C: translation.html#the-c-back-end
.. _CLI: cli-backend.html
.. _JVM: translation.html#genjvm
.. _`translation document`: translation.html

----------------------
How do I compile PyPy?
----------------------

See the `getting-started`_ guide.

.. _`getting-started`: getting-started-python.html

.. _`how do I compile my own interpreters`:

-------------------------------------
How do I compile my own interpreters?
-------------------------------------
Begin by reading `Andrew Brown's tutorial`_ .

.. _`Andrew Brown's tutorial`: http://morepypy.blogspot.com/2011/04/tutorial-writing-interpreter-with-pypy.html

---------------------------------------------------------
Can RPython modules for PyPy be translated independently?
---------------------------------------------------------

No, you have to rebuild the entire interpreter.  This means two things:

* It is imperative to use test-driven development.  You have to test
  exhaustively your module in pure Python, before even attempting to
  translate it.  Once you translate it, you should have only a few typing
  issues left to fix, but otherwise the result should work out of the box.

* Second, and perhaps most important: do you have a really good reason
  for writing the module in RPython in the first place?  Nowadays you
  should really look at alternatives, like writing it in pure Python,
  using ctypes if it needs to call C code.

In this context it is not that important to be able to translate
RPython modules independently of translating the complete interpreter.
(It could be done given enough efforts, but it's a really serious
undertaking.  Consider it as quite unlikely for now.)

----------------------------------------------------------
Why does PyPy draw a Mandelbrot fractal while translating?
----------------------------------------------------------

Because it's fun.

.. include:: _ref.txt

