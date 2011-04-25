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

We list the differences we know about in `cpython_differences`_.

There is also an experimental support for CPython extension modules, so
they'll run without change (from current observation, rather with little
change) on trunk. It has been a part of 1.4 release, but support is still
in alpha phase.

.. _`extension modules`: cpython_differences.html#extension-modules
.. _`cpython_differences`: cpython_differences.html

--------------------------------
On what platforms does PyPy run?
--------------------------------

PyPy is regularly and extensively tested on Linux machines and on Mac
OS X and mostly works under Windows too (but is tested there less
extensively). PyPy needs a CPython running on the target platform to
bootstrap, as cross compilation is not really meant to work yet.
At the moment you need CPython 2.4 (with ctypes) or CPython 2.5 or 2.6
for the translation process. PyPy's JIT requires an x86 or x86_64 CPU.


------------------------------------------------
Which Python version (2.x?) does PyPy implement?
------------------------------------------------

PyPy currently aims to be fully compatible with Python 2.5. That means that
it contains the standard library of Python 2.5 and that it supports 2.5
features (such as the with statement).  

.. _threading:

-------------------------------------------------
Do threads work?  What are the modules that work?
-------------------------------------------------

Operating system-level threads basically work. If you enable the ``thread``
module then PyPy will get support for GIL based threading.
Note that PyPy also fully supports `stackless-like
microthreads`_ (although both cannot be mixed yet).

All pure-python modules should work, unless they rely on ugly
cpython implementation details, in which case it's their fault.
There is an increasing number of compatible CPython extensions working,
including things like wxPython or PIL. This is an ongoing development effort
to bring as many CPython extension modules working as possible.

.. _`stackless-like microthreads`: stackless.html


------------------------------------
Can I use CPython extension modules?
------------------------------------

Yes, but the feature is in alpha state and is available only on trunk
(not in the 1.2 release). However, we'll only ever support well-behaving
CPython extensions. Please consult PyPy developers on IRC or mailing list
for explanations if your favorite module works and how you can help to make
it happen in case it does not.

We fully support ctypes-based extensions, however.

------------------------------------------
How do I write extension modules for PyPy?
------------------------------------------

See `Writing extension modules for PyPy`__.

.. __: extending.html


.. _`slower than CPython`:
.. _`how fast is pypy`:

-----------------
How fast is PyPy?
-----------------

.. _whysoslow:

In three words, PyPy is "kind of fast".  In more than three
words, the answer to this question is hard to give as a single
number.  The fastest PyPy available so far is clearly PyPy
`with a JIT included`_, optimized and translated to C.  This
version of PyPy is "kind of fast" in the sense that there are
numerous examples of Python code that run *much faster* than
CPython, up to a large number of times faster.  And there are
also examples of code that are just as slow as without the
JIT.  A PyPy that does not include a JIT has performance that
is more predictable: it runs generally somewhere between 1 and
2 times slower than CPython, in the worst case up to 4 times
slower.

Obtaining good measurements for the performance when run on
the CLI or JVM is difficult, but the JIT on the CLI `seems to
work nicely`__ too.

.. __: http://codespeak.net/svn/user/antocuni/phd/thesis/thesis.pdf
.. _`with a JIT included`: jit/index.html


.. _`prolog and javascript`:

----------------------------------------------------------------
Can PyPy support interpreters for other languages beyond Python?
----------------------------------------------------------------

The toolsuite that translates the PyPy interpreter is quite
general and can be used to create optimized versions of interpreters
for any language, not just Python.  Of course, these interpreters
can make use of the same features that PyPy brings to Python:
translation to various languages, stackless features,
garbage collection, implementation of various things like arbitrarily long
integers, etc. 

Currently, we have preliminary versions of a JavaScript interpreter
(Leonardo Santagada as his Summer of PyPy project), a `Prolog interpreter`_
(Carl Friedrich Bolz as his Bachelor thesis), and a `SmallTalk interpreter`_
(produced during a sprint).  On the `PyPy "user" main page`_ there are also a
Scheme and Io implementation, all of these are unfinished at the moment.

.. _`Prolog interpreter`: https://bitbucket.org/cfbolz/pyrolog/
.. _`SmallTalk interpreter`: http://dx.doi.org/10.1007/978-3-540-89275-5_7
.. _`PyPy "user" main page`: https://bitbucket.org/pypy/


Development
===========

-----------------------------------------------------------
How do I get into PyPy development?  Can I come to sprints?
-----------------------------------------------------------

Sure you can come to sprints! We always welcome newcomers and try to help them
get started in the project as much as possible (e.g. by providing tutorials and
pairing them with experienced PyPy developers). Newcomers should have some
Python experience and read some of the PyPy documentation before coming to a
sprint.

Coming to a sprint is usually also the best way to get into PyPy development.
If you get stuck or need advice, `contact us`_. Usually IRC is
the most immediate way to get feedback (at least during some parts of the day;
many PyPy developers are in Europe) and the `mailing list`_ is better for long
discussions.

.. _`contact us`: index.html
.. _`mailing list`: http://codespeak.net/mailman/listinfo/pypy-dev

----------------------------------------------------------------------
I am getting strange errors while playing with PyPy, what should I do?
----------------------------------------------------------------------

It seems that a lot of strange, unexplainable problems can be magically
solved by removing all the \*.pyc files from the PyPy source tree
(the script `py.cleanup`_ from py/bin will do that for you).
Another thing you can do is removing the directory pypy/_cache
completely. If the error is persistent and still annoys you after this
treatment please send us a bug report (or even better, a fix :-)

.. _`py.cleanup`: http://codespeak.net/py/current/doc/bin.html

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


PyPy translation tool chain
===========================

----------------------------------------
Can PyPy compile normal Python programs?
----------------------------------------

No, PyPy is not a Python compiler.

In Python, it is mostly impossible to *prove* anything about the types
that a program will manipulate by doing a static analysis.  It should be
clear if you are familiar with Python, but if in doubt see [BRETT]_.

What could be attempted is static "soft typing", where you would use a
whole bunch of heuristics to guess what types are probably going to show
up where.  In this way, you could compile the program into two copies of
itself: a "fast" version and a "slow" version.  The former would contain
many guards that allow it to fall back to the latter if needed.  That
would be a wholly different project than PyPy, though.  (As far as we
understand it, this is the approach that the LLVM__ group would like to
see LLVM used for, so if you feel like working very hard and attempting
something like this, check with them.)

.. __: http://llvm.org/

What PyPy contains is, on the one hand, an non-soft static type
inferencer for RPython, which is a sublanguage that we defined just so
that it's possible and not too hard to do that; and on the other hand,
for the full Python language, we have an interpreter, and a JIT
generator which can produce a Just-In-Time Compiler from the
interpreter.  The resulting JIT works for the full Python language in a
way that doesn't need type inference at all.

For more motivation and details about our approach see also [D05.1]_,
section 3.

.. [BRETT] Brett Cannon,
           Localized Type Inference of Atomic Types in Python,
           http://www.ocf.berkeley.edu/~bac/thesis.pdf

.. [D05.1] Compiling Dynamic Language Implementations,
           Report from the PyPy project to the E.U.,
           https://bitbucket.org/pypy/extradoc/raw/tip/eu-report/D05.1_Publish_on_translating_a_very-high-level_description.pdf

.. _`PyPy's RPython`: 

------------------------------
What is this RPython language?
------------------------------

RPython is a restricted subset of the Python language.   It is used for 
implementing dynamic language interpreters within the PyPy framework.  The
restrictions are to ensure that type inference (and so, ultimately, translation
to other languages) of RPython programs is possible. These restrictions only
apply after the full import happens, so at import time arbitrary Python code can
be executed. 

The property of "being RPython" always applies to a full program, not to single
functions or modules (the translation tool chain does a full program analysis).
"Full program" in the context of "being RPython" is all the code reachable from
an "entry point" function. The translation toolchain follows all calls
recursively and discovers what belongs to the program and what not.

The restrictions that apply to programs to be RPython mostly limit the ability
of mixing types in arbitrary ways. RPython does not allow the usage of two
different types in the same variable. In this respect (and in some others) it
feels a bit like Java. Other features not allowed in RPython are the usage of
special methods (``__xxx__``) except ``__init__`` and ``__del__``, and the
usage of reflection capabilities (e.g. ``__dict__``).

Most existing standard library modules are not RPython, except for
some functions in ``os``, ``math`` and ``time`` that are natively
supported. In general it is quite unlikely that an existing Python
program is by chance RPython; it is most likely that it would have to be
heavily rewritten.
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

-------------------------------------------------------------------------
Can I use PyPy and RPython to compile smaller parts of my Python program?
-------------------------------------------------------------------------

No.  That would be possible, and we played with early attempts in that
direction, but there are many delicate issues: for example, how the
compiled and the non-compiled parts exchange data.  Supporting this in a
nice way would be a lot of work.

PyPy is certainly a good starting point for someone that would like to
work in that direction.  Early attempts were dropped because they
conflicted with refactorings that we needed in order to progress on the
rest of PyPy; the currently active developers of PyPy have different
priorities.  If someone wants to start working in that direction I
imagine that he might get a (very little) bit of support from us,
though.

Alternatively, it's possible to write a mixed-module, i.e. an extension
module for PyPy in RPython, which you can then import from your Python
program when it runs on top of PyPy.  This is similar to writing a C
extension module for CPython in term of investment of effort (without
all the INCREF/DECREF mess, though).

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
pretty hard, without some kind of type inference, to translate, say this
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

No.  PyPy always runs your code in its own interpreter, which is a
full and compliant Python 2.5 interpreter.  RPython_ is only the
language in which parts of PyPy itself are written and extension
modules for it.  The answer to whether something needs to be written as
an extension module, apart from the "gluing to external libraries" reason, will
change over time as speed for normal Python code improves.

-------------------------
Which backends are there?
-------------------------

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

.. _`how do I compile my own interpreters`:

-------------------------------------
How do I compile my own interpreters?
-------------------------------------

Start from the example of
`pypy/translator/goal/targetnopstandalone.py`_, which you compile by
typing::

    python translate.py targetnopstandalone

You can have a look at intermediate C source code, which is (at the
moment) put in ``/tmp/usession-*/testing_1/testing_1.c``.  Of course,
all the functions and stuff used directly and indirectly by your
``entry_point()`` function has to be RPython_.


.. _`RPython`: coding-guide.html#rpython
.. _`getting-started`: getting-started.html

.. include:: _ref.rst

----------------------------------------------------------
Why does PyPy draw a Mandelbrot fractal while translating?
----------------------------------------------------------

Because it's fun.
