Frequently Asked Questions
==========================

.. contents::

See also: `Frequently ask questions about RPython.`__

.. __: http://rpython.readthedocs.org/en/latest/faq.html

---------------------------


What is PyPy?
-------------

PyPy is a reimplementation of Python in Python, using the RPython translation
toolchain.

PyPy tries to find new answers about ease of creation, flexibility,
maintainability and speed trade-offs for language implementations.
For further details see our :doc:`goal and architecture document <architecture>`.


Is PyPy a drop in replacement for CPython?
------------------------------------------

Almost!

The mostly likely stumbling block for any given project is support for
:ref:`extension modules <extension-modules>`.  PyPy supports a continually growing
number of extension modules, but so far mostly only those found in the
standard library.

The language features (including builtin types and functions) are very
complete and well tested, so if your project does not use many
extension modules there is a good chance that it will work with PyPy.

We list the differences we know about in :doc:`cpython differences <cpython_differences>`.


Module xyz does not work with PyPy: ImportError
-----------------------------------------------

A module installed for CPython is not automatically available for PyPy
--- just like a module installed for CPython 2.6 is not automatically
available for CPython 2.7 if you installed both.  In other words, you
need to install the module xyz specifically for PyPy.

On Linux, this means that you cannot use ``apt-get`` or some similar
package manager: these tools are only meant *for the version of CPython
provided by the same package manager.*  So forget about them for now
and read on.

It is quite common nowadays that xyz is available on PyPI_ and
installable with ``pip install xyz``.  The simplest solution is to `use
virtualenv (as documented here)`_.  Then enter (activate) the virtualenv
and type: ``pip install xyz``.  If you don't know or don't want virtualenv,
you can also install ``pip`` globally by saying ``pypy -m ensurepip``.

If you get errors from the C compiler, the module is a CPython C
Extension module using unsupported features.  `See below.`_

Alternatively, if either the module xyz is not available on PyPI or you
don't want to use virtualenv, then download the source code of xyz,
decompress the zip/tarball, and run the standard command: ``pypy
setup.py install``.  (Note: `pypy` here instead of `python`.)  As usual
you may need to run the command with `sudo` for a global installation.
The other commands of ``setup.py`` are available too, like ``build``.

.. _PyPI: https://pypi.python.org/pypi
.. _`use virtualenv (as documented here)`: install.html#installing-using-virtualenv


Module xyz does not work in the sandboxed PyPy?
-----------------------------------------------

You cannot import *any* extension module in a `sandboxed PyPy`_,
sorry.  Even the built-in modules available are very limited.
Sandboxing in PyPy is a good proof of concept, really safe IMHO, but
it is only a proof of concept.  It seriously requires someone working
on it.  Before this occurs, it can only be used it for "pure Python"
examples: programs that import mostly nothing (or only pure Python
modules, recursively).

.. _`sandboxed PyPy`: sandbox.html


.. _`See below.`:

Do CPython Extension modules work with PyPy?
--------------------------------------------

We have experimental support for CPython extension modules, so
they run with minor changes.  This has been a part of PyPy since
the 1.4 release, but support is still in beta phase.  CPython
extension modules in PyPy are often much slower than in CPython due to
the need to emulate refcounting.  It is often faster to take out your
CPython extension and replace it with a pure python version that the
JIT can see.  If trying to install module xyz, and the module has both
a C and a Python version of the same code, try first to disable the C
version; this is usually easily done by changing some line in ``setup.py``.

We fully support ctypes-based extensions. But for best performance, we
recommend that you use the cffi_ module to interface with C code.

For information on which third party extensions work (or do not work)
with PyPy see the `compatibility wiki`_.

For more information about how we manage refcounting semamtics see 
rawrefcount_

.. _compatibility wiki: https://bitbucket.org/pypy/compatibility/wiki/Home
.. _cffi: http://cffi.readthedocs.org/
.. _rawrefcount: discussion/rawrefcount.html   


On which platforms does PyPy run?
---------------------------------

PyPy currently supports:

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 32 bits, OpenBSD, FreeBSD),
  
  * newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux,
  
  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

PyPy is regularly and extensively tested on Linux machines. It
works on Mac and Windows: it is tested there, but most of us are running
Linux so fixes may depend on 3rd-party contributions.

To bootstrap from sources, PyPy can use either CPython 2.7 or
another (e.g. older) PyPy.  Cross-translation is not really supported:
e.g. to build a 32-bit PyPy, you need to have a 32-bit environment.
Cross-translation is only explicitly supported between a 32-bit Intel
Linux and ARM Linux (see :ref:`here <rpython:arm>`).


Which Python version (2.x?) does PyPy implement?
------------------------------------------------

PyPy currently aims to be fully compatible with Python 2.7. That means that
it contains the standard library of Python 2.7 and that it supports 2.7
features (such as set comprehensions).


.. _threading:

Does PyPy have a GIL?  Why?
-------------------------------------------------

Yes, PyPy has a GIL.  Removing the GIL is very hard.  The problems are
essentially the same as with CPython (including the fact that our
garbage collectors are not thread-safe so far).  Fixing it is possible,
as shown by Jython and IronPython, but difficult.  It would require
adapting the whole source code of PyPy, including subtle decisions about
whether some effects are ok or not for the user (i.e. the Python
programmer).

Instead, since 2012, there is work going on on a still very experimental
:doc:`Software Transactional Memory <stm>` (STM) version of PyPy.  This should give
an alternative PyPy which works without a GIL, while at the same time
continuing to give the Python programmer the complete illusion of having
one.


Is PyPy more clever than CPython about Tail Calls?
--------------------------------------------------

No.  PyPy follows the Python language design, including the built-in
debugger features.  This prevents tail calls, as summarized by Guido
van Rossum in two__ blog__ posts.  Moreover, neither the JIT nor
Stackless__ change anything to that.

.. __: http://neopythonic.blogspot.com/2009/04/tail-recursion-elimination.html
.. __: http://neopythonic.blogspot.com/2009/04/final-words-on-tail-calls.html
.. __: stackless.html


How do I write extension modules for PyPy?
------------------------------------------

See :doc:`extending`.


.. _how-fast-is-pypy:

How fast is PyPy?
-----------------
This really depends on your code.
For pure Python algorithmic code, it is very fast.  For more typical
Python programs we generally are 3 times the speed of CPython 2.7.
You might be interested in our `benchmarking site`_ and our
:ref:`jit documentation <rpython:jit>`.

`Your tests are not a benchmark`_: tests tend to be slow under PyPy
because they run exactly once; if they are good tests, they exercise
various corner cases in your code.  This is a bad case for JIT
compilers.  Note also that our JIT has a very high warm-up cost, meaning
that any program is slow at the beginning.  If you want to compare the
timings with CPython, even relatively simple programs need to run *at
least* one second, preferrably at least a few seconds.  Large,
complicated programs need even more time to warm-up the JIT.

.. _benchmarking site: http://speed.pypy.org

.. _your tests are not a benchmark: http://alexgaynor.net/2013/jul/15/your-tests-are-not-benchmark/

Couldn't the JIT dump and reload already-compiled machine code?
---------------------------------------------------------------

No, we found no way of doing that.  The JIT generates machine code
containing a large number of constant addresses --- constant at the time
the machine code is generated.  The vast majority is probably not at all
constants that you find in the executable, with a nice link name.  E.g.
the addresses of Python classes are used all the time, but Python
classes don't come statically from the executable; they are created anew
every time you restart your program.  This makes saving and reloading
machine code completely impossible without some very advanced way of
mapping addresses in the old (now-dead) process to addresses in the new
process, including checking that all the previous assumptions about the
(now-dead) object are still true about the new object.



Would type annotations help PyPy's performance?
-----------------------------------------------

Two examples of type annotations that are being proposed for improved
performance are `Cython types`__ and `PEP 484 - Type Hints`__.

.. __: http://docs.cython.org/src/reference/language_basics.html#declaring-data-types
.. __: https://www.python.org/dev/peps/pep-0484/

**Cython types** are, by construction, similar to C declarations.  For
example, a local variable or an instance attribute can be declared
``"cdef int"`` to force a machine word to be used.  This changes the
usual Python semantics (e.g. no overflow checks, and errors when
trying to write other types of objects there).  It gives some extra
performance, but the exact benefits are unclear: right now
(January 2015) for example we are investigating a technique that would
store machine-word integers directly on instances, giving part of the
benefits without the user-supplied ``"cdef int"``.

**PEP 484 - Type Hints,** on the other hand, is almost entirely
useless if you're looking at performance.  First, as the name implies,
they are *hints:* they must still be checked at runtime, like PEP 484
says.  Or maybe you're fine with a mode in which you get very obscure
crashes when the type annotations are wrong; but even in that case the
speed benefits would be extremely minor.

There are several reasons for why.  One of them is that annotations
are at the wrong level (e.g. a PEP 484 "int" corresponds to Python 3's
int type, which does not necessarily fits inside one machine word;
even worse, an "int" annotation allows arbitrary int subclasses).
Another is that a lot more information is needed to produce good code
(e.g. "this ``f()`` called here really means this function there, and
will never be monkey-patched" -- same with ``len()`` or ``list()``,
btw).  The third reason is that some "guards" in PyPy's JIT traces
don't really have an obvious corresponding type (e.g. "this dict is so
far using keys which don't override ``__hash__`` so a more efficient
implementation was used").  Many guards don't even have any correspondence
with types at all ("this class attribute was not modified"; "the loop
counter did not reach zero so we don't need to release the GIL"; and
so on).

As PyPy works right now, it is able to derive far more useful
information than can ever be given by PEP 484, and it works
automatically.  As far as we know, this is true even if we would add
other techniques to PyPy, like a fast first-pass JIT.



.. _`prolog and javascript`:

Can I use PyPy's translation toolchain for other languages besides Python?
--------------------------------------------------------------------------

Yes. The toolsuite that translates the PyPy interpreter is quite
general and can be used to create optimized versions of interpreters
for any language, not just Python.  Of course, these interpreters
can make use of the same features that PyPy brings to Python:
translation to various languages, stackless features,
garbage collection, implementation of various things like arbitrarily long
integers, etc.

Currently, we have `Topaz`_, a Ruby interpreter; `Hippy`_, a PHP
interpreter; preliminary versions of a `JavaScript interpreter`_
(Leonardo Santagada as his Summer of PyPy project); a `Prolog interpreter`_
(Carl Friedrich Bolz as his Bachelor thesis); and a `SmallTalk interpreter`_
(produced during a sprint).  On the `PyPy bitbucket page`_ there is also a
Scheme and an Io implementation; both of these are unfinished at the moment.

.. _Topaz: http://topazruby.com/
.. _Hippy: http://morepypy.blogspot.ch/2012/07/hello-everyone.html
.. _JavaScript interpreter: https://bitbucket.org/pypy/lang-js/
.. _Prolog interpreter: https://bitbucket.org/cfbolz/pyrolog/
.. _SmallTalk interpreter: http://dx.doi.org/10.1007/978-3-540-89275-5_7
.. _PyPy bitbucket page: https://bitbucket.org/pypy/


How do I get into PyPy development?  Can I come to sprints?
-----------------------------------------------------------

Certainly you can come to sprints! We always welcome newcomers and try
to help them as much as possible to get started with the project.  We
provide tutorials and pair them with experienced PyPy
developers. Newcomers should have some Python experience and read some
of the PyPy documentation before coming to a sprint.

Coming to a sprint is usually the best way to get into PyPy development.
If you get stuck or need advice, :doc:`contact us <index>`. IRC is
the most immediate way to get feedback (at least during some parts of the day;
most PyPy developers are in Europe) and the `mailing list`_ is better for long
discussions.

.. _mailing list: http://mail.python.org/mailman/listinfo/pypy-dev


OSError: ... cannot restore segment prot after reloc... Help?
-------------------------------------------------------------

On Linux, if SELinux is enabled, you may get errors along the lines of
"OSError: externmod.so: cannot restore segment prot after reloc: Permission
denied." This is caused by a slight abuse of the C compiler during
configuration, and can be disabled by running the following command with root
privileges:

.. code-block:: console

    # setenforce 0

This will disable SELinux's protection and allow PyPy to configure correctly.
Be sure to enable it again if you need it!


How should I report a bug?
--------------------------

Our bug tracker is here: https://bitbucket.org/pypy/pypy/issues/

Missing features or incompatibilities with CPython are considered
bugs, and they are welcome.  (See also our list of `known
incompatibilities`__.)

.. __: http://pypy.org/compat.html

For bugs of the kind "I'm getting a PyPy crash or a strange
exception", please note that: **We can't do anything without
reproducing the bug ourselves**.  We cannot do anything with
tracebacks from gdb, or core dumps.  This is not only because the
standard PyPy is compiled without debug symbols.  The real reason is
that a C-level traceback is usually of no help at all in PyPy.
Debugging PyPy can be annoying.

`This is a clear and useful bug report.`__  (Admittedly, sometimes
the problem is really hard to reproduce, but please try to.)

.. __: https://bitbucket.org/pypy/pypy/issues/2363/segfault-in-gc-pinned-object-in

In more details:

* First, please give the exact PyPy version, and the OS.

* It might help focus our search if we know if the bug can be
  reproduced on a "``pypy --jit off``" or not.  If "``pypy --jit
  off``" always works, then the problem might be in the JIT.
  Otherwise, we know we can ignore that part.

* If you got the bug using only Open Source components, please give a
  step-by-step guide that we can follow to reproduce the problem
  ourselves.  Don't assume we know anything about any program other
  than PyPy.  We would like a guide that we can follow point by point
  (without guessing or having to figure things out)
  on a machine similar to yours, starting from a bare PyPy, until we
  see the same problem.  (If you can, you can try to reduce the number
  of steps and the time it needs to run, but that is not mandatory.)

* If the bug involves Closed Source components, or just too many Open
  Source components to install them all ourselves, then maybe you can
  give us some temporary ssh access to a machine where the bug can be
  reproduced.  Or, maybe we can download a VirtualBox or VMWare
  virtual machine where the problem occurs.

* If giving us access would require us to use tools other than ssh,
  make appointments, or sign a NDA, then we can consider a commerical
  support contract for a small sum of money.

* If even that is not possible for you, then sorry, we can't help.

Of course, you can try to debug the problem yourself, and we can help
you get started if you ask on the #pypy IRC channel, but be prepared:
debugging an annoying PyPy problem usually involves quite a lot of gdb
in auto-generated C code, and at least some knowledge about the
various components involved, from PyPy's own RPython source code to
the GC and possibly the JIT.
