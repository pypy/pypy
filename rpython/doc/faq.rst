==========================
Frequently Asked Questions
==========================

.. contents::

----------------
What is RPython?
----------------

RPython is a framework for implementing interpreters and virtual machines for
programming languages, especially dynamic languages.

------------------------------------------------
Can RPython compile normal Python programs to C?
------------------------------------------------

No, RPython is not a Python compiler.

In Python, it is mostly impossible to *prove* anything about the types
that a program will manipulate by doing a static analysis.  It should be
clear if you are familiar with Python, but if in doubt see [BRETT]_.

If you want a fast Python program, please use the PyPy JIT_ instead.

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

No, and you shouldn't try.  First and foremost, RPython is a language
designed for writing interpreters. It is a restricted subset of
Python.  If you program is not an interpreter but tries to do "real
things", like use *any* part of the standard Python library or *any*
3rd-party library, then it is not RPython to start with.  You should
only look at RPython if you try to `write your own interpreter`__.

.. __: `how do I compile my own interpreters`_

If your goal is to speed up Python code, then look at the regular PyPy,
which is a full and compliant Python 2.7 interpreter (which happens to
be written in RPython).  Not only is it not necessary for you to rewrite
your code in RPython, it might not give you any speed improvements even
if you manage to.

Yes, it is possible with enough effort to compile small self-contained
pieces of RPython code doing a few performance-sensitive things.  But
this case is not interesting for us.  If you needed to rewrite the code
in RPython, you could as well have rewritten it in C for example.  The
latter is a much more supported, much more documented language `:-)`

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

------------------
Could we use LLVM?
------------------

In theory yes.  But we tried to use it 5 or 6 times already, as a
translation backend or as a JIT backend --- and failed each time.

In more details: using LLVM as a (static) translation backend is
pointless nowadays because you can generate C code and compile it with
clang.  (Note that compiling PyPy with clang gives a result that is not
faster than compiling it with gcc.)  We might in theory get extra
benefits from LLVM's GC integration, but this requires more work on the
LLVM side before it would be remotely useful.  Anyway, it could be
interfaced via a custom primitive in the C code.

On the other hand, using LLVM as our JIT backend looks interesting as
well --- but again we made an attempt, and it failed: LLVM has no way to
patch the generated machine code.

So the position of the core PyPy developers is that if anyone wants to
make an N+1'th attempt with LLVM, he is welcome, and he will receive a
bit of help on the IRC channel, but he is left with the burden of proof
that it works.

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

* It is imperative to use test-driven development.  You have to exhaustively
  test your module in pure Python, before even attempting to
  translate it.  Once you translate it, you should have only a few typing
  issues left to fix, but otherwise the result should work out of the box.

* Second, and perhaps most important: do you have a really good reason
  for writing the module in RPython in the first place?  Nowadays you
  should really look at alternatives, like writing it in pure Python,
  using ctypes if it needs to call C code.  Other alternatives are being
  developed too (as of summer 2011), like a Cython binding.

In this context it is not that important to be able to translate
RPython modules independently of translating the complete interpreter.
(It could be done given enough efforts, but it's a really serious
undertaking.  Consider it as quite unlikely for now.)

--------------------------------------------------------------------
Why does the translator draw a Mandelbrot fractal while translating?
--------------------------------------------------------------------

Because it's fun.
