============================================
PyPy v7.3.17: release of python 2.7 and 3.10
============================================

The PyPy team is proud to release version 7.3.17 of PyPy.

This release includes a new `RISC-V JIT backend`_, an `improved REPL`_ based on
work by the CPython team, and `better JIT optimizations`_ of integer
operations. Special shout-outs to `Logan Chien`_ for the `RISC-V backend
work`_, to `Nico Rittinghaus`_ for better integer optimization in the JIT, and
the CPython team that has worked on the repl.

The release includes two different interpreters:

- PyPy2.7, which is an interpreter supporting the syntax and the features of
  Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
  backported security updates)

- PyPy3.10, which is an interpreter supporting the syntax and the features of
  Python 3.10, including the stdlib for CPython 3.10.14.

The interpreters are based on much the same codebase, thus the dual
release. This is a micro release, all APIs are compatible with the other 7.3
releases. It follows after 7.3.16 release on April 23, 2024. 

We recommend updating. You can find links to download the releases here:

    https://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
`direct consulting`_ work. If PyPy is helping you out, we would love to hear
about it and encourage submissions to our blog_ via a pull request
to https://github.com/pypy/pypy.org

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: bug fixes,
`PyPy`_ and `RPython`_ documentation improvements, or general `help`_ with
making RPython's JIT even better.

If you are a python library maintainer and use C-extensions, please consider
making a HPy_ / CFFI_ / cppyy_ version of your library that would be performant
on PyPy. In any case, both `cibuildwheel`_ and the `multibuild system`_ support
building wheels for PyPy.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _cppyy: https://cppyy.readthedocs.io
.. _`multibuild system`: https://github.com/matthew-brett/multibuild
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _blog: https://pypy.org/blog
.. _HPy: https://hpyproject.org/
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html
.. _`RISC-V backend work`: https://github.com/pypy/pypy/pull/5002


.. _`RISC-V JIT backend`:

RISC-V backend for the JIT
===========================

PyPy's JIT has added support for generating 64-bit RISC-V machine code at
runtime (RV64-IMAD, specifically). So far we are not releasing binaries for any
RISC-V platforms, but there are instructions_ on how to cross-compile binaries.

.. _instructions: https://rpython.readthedocs.io/en/latest/riscv.html


.. _`improved REPL`:

REPL Improvements
==================

The biggest user-visible change of the release is new features in the repl of
PyPy3.10. CPython 3.13 has adopted and extended PyPy's pure-Python repl, adding
a number of features and fixing a number or bugs in the process. We have
backported and added the following features:

- Prompts and tracebacks use terminal colors, as well as `terminal hyperlinks`_
  for file names.
- `Bracketed paste`_ enable pasting several lines of input into the terminal
  without auto-indentation getting in the way.
- A special interactive help browser (F1), history browser (F2), explicit paste
  mode (F3).
- Support for Ctrl-<left/right> to jump over whole words at a time.

See the `CPython documentation for further details`_. Thanks to Łukasz Langa,
Pablo Galindo Salgado and the other CPython devs involved in this work.

.. _`terminal hyperlinks`: https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda
.. _`Bracketed paste`: https://en.wikipedia.org/wiki/Bracketed-paste
.. _`CPython documentation for further details`: https://docs.python.org/3.13/whatsnew/3.13.html#a-better-interactive-interpreter


.. _`better JIT optimizations`:

Better JIT optimizations of integer operations
==============================================

The optimizers of PyPy's JIT have become much better at reasoning about and
optimizing integer operations. This is done with a new `"knownbits" abstract
domain`_. In many programs that do bit-manipulation of integers, some of the
bits of the integer variables of the program can be statically known. Here's a
simple example:

.. _`"knownbits" abstract domain`: https://pypy.org/posts/2024/08/toy-knownbits.html

.. code:: python

    x = a | 1
    ...
    if x & 1:
        ...
    else:
        ...

With the new abstract domain, the JIT can optimize the ``if``-condition to
``True``, because it already knows that the lowest bit of ``x`` must be set.
This optimization applies to all Python-integers that fit into a machine word
(PyPy optimistically picks between two different representations for ``int``,
depending on the size of the value). Unfortunately there is very little impact
of this change on almost all Python code, because intensive bit-manipulation is
rare in Python. However, the change leads to significant performance
improvements in `Pydrofoil`_ (the RPython-based RISC-V/ARM emulators that are
automatically generated from high-level Sail_ specifications of the respective
ISAs, and that use the RPython JIT to improve performance).

.. _`Pydrofoil`: https://docs.pydrofoil.org/en/latest/
.. _Sail: https://github.com/rems-project/sail/

PyPy versions and speed.pypy.org
================================

The keen-eyed will have noticed no mention of Python version 3.9 in the
releases above. Typically we will maintain only one version of Python3, but due
to PyPy3.9 support on conda-forge we maintained multiple versions from the
first release of PyPy3.10 in PyPy v7.3.12 (Dec 2022). Conda-forge is
`sunsetting its PyPy support`_, which means we can drop PyPy3.9. Since that was
the major driver of benchmarks at https://speed.pypy.org, we revamped the site
to showcase PyPy3.9, PyPy3.10, and various versions of cpython on the home
page. For historical reasons, the "baseline" for comparison is still cpython
3.7.19.

We will keep the buildbots building PyPY3.9 until the end of August, these
builds will still be available on the `nightly builds`_ tab of the buildbot.

.. _`sunsetting its PyPy support`: https://pypy.org/posts/2024/08/conda-forge-proposes-dropping-support-for-pypy.html
.. _`nightly builds`: https://buildbot.pypy.org/nightly/

What is PyPy?
=============

PyPy is a Python interpreter, a drop-in replacement for CPython
It's fast (`PyPy and CPython`_ performance
comparison) due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

We provide binary builds for:

* **x86** machines on most common operating systems
  (Linux 32/64 bits, Mac OS 64 bits, Windows 64 bits)

* 64-bit **ARM** machines running Linux (``aarch64``) and macos (``macos_arm64``).

PyPy supports Windows 32-bit, Linux PPC64 big- and little-endian, Linux ARM
32 bit, RISC-V RV64IMAFD Linux, and s390x Linux but does not release binaries.
Please reach out to us if you wish to sponsor binary releases for those
platforms. Downstream packagers provide binary builds for debian, Fedora,
conda, OpenBSD, FreeBSD, Gentoo, and more.

.. _`PyPy and CPython`: https://speed.pypy.org
.. _`dynamic languages`: https://rpython.readthedocs.io/en/latest/examples.html

Changelog
=========

For all versions
----------------

- DOCS: Fix source links in docs when moving from heptapod to github (:issue:`3216`)
- DOCS: Mention ``externals`` mercurial repo for windows build (:issue:`4921`)

Bugfixes
~~~~~~~~

- Don't crash on constfolding field reads from null pointers in the RPython
  translator (:issue:`4941`)
- Fix ``const char`` declaration in cffi gdbm (:issue:`4931`)
- Restore error message of ``TypeError`` generated when calling
  ``tuple.__getitem__`` with invalid types (:issue:`4954`)
- ``id(obj)`` should really be an ``int``, not a ``long``
- Bump ``MACOSX_DEPLOYMENT_TARGET`` to 10.15 on x86_64 and 11.0 on arm64
  (:issue:`4975`)
- Ignore whitespace when parsing complex numbers (:issue:`4980`)
- Add ``mmap.MAP_POPULATE`` on linux (:issue:`4991`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Optimize for array length from ``new_array`` for non-virtual arrays 
- Add ``look_inside_iff`` for ``W_TupleObject._getslice``
- Allow implicit string literal concatenation as docstring (:issue:`4973`)
- Improve trace of adding a new attribute to an already big instance and to a
  list of unboxed fields
- Improve the code generated by some ``list`` methods in the JIT and the
  RPython support code:
    
  - calling ``find`` or ``count`` doesn't need the list object itself, just the
    underlying storage
  - unroll in more situations when creating a list
  - make list multiplication use ``ll_alloc_and_set`` if the list has length 1
  - copy lists in multiplication with ``log2(n)`` arraycopys instead of just
    copying n times (string multiplication does it like this too)
  - save one copy of the ``lhs`` list when adding two list

- Add a jit driver for ``dict.__eq__`` and an especially fast implementation
  for mapdict equality
- Make the JIT generate better code for certain function calling patterns with ``*args``
- Optimize ``x * -1`` and ``x // -1`` to ``-x`` in the JIT.
- Speed up binary search on the ``utf8`` index storage. This slightly speeds up
  ``unicode/str.find`` on very large strings.
- Optimize integers using the knownbits abstract domain (shout-out to `Nico Rittinghaus`).


.. _`Nico Rittinghaus`: https://github.com/nirit100
.. _`Logan Chien`: https://github.com/loganchien

Python 3.10
-----------

Bugfixes
~~~~~~~~

- Fix leak of global named resources when using multiprocessing spawn
  (:issue:`python/cpython#90549`)
- Include ``pyexpatns.h`` when building ``pyexpat``
- Add ``IO_REPARSE_TAG*`` constants to ``stats.py`` (:issue:`4953`)
- Add some missing sqlite3 symbols and defines.
- ``getindex_w`` works differently between py2 and py3, leading to error
  message confusion
- Fix typo ``HAVE_MS_WINDOWS``-> ``MS_WINDOWS`` which impacted the ``stats``
  module (:issue:`4952`)
- Compare lower case exe names when creating a virtual environment (:issue:`4958`)
- Add missing ``typecodes`` attribute to ``array``
- Add ``cmath.tau``, using ``math.pi * 2.0`` to define it.
- Remove dead code, make ``stats`` logic like CPython (:issue:`4976`)
- Add ``Py_UNREACHABLE`` to ``pymacro.h`` (:issue:`4982`)
- Don't segfault trying to generate a better SyntaxError msg. Also follow CPython's
  logic about ``RAISE_SYNTAX_ERROR_INVALID_TARGET`` more closely, to get the
  correct locations (:issue:`4897`)
- Fix long-standing bugs in pyrepl (from the CPython port of PyPy's pyrepl)

  - Support ``ctrl-left`` and ``ctrl-right`` in the console (:issue:`906`)
  - Implement bracketed paste (:issue:`2880`)
- Update bundled setuptools to `65.5.0`
- Fix value of readonly flag in ``PyMemoryView_FromMemory`` (:issue:`4993`)
- Make sure to call the ``atexit`` handlers after receiving ``sigint``
  (:issue:`4995`). This is done by calling ``space.finish()``.
- Make stack depth computation in the bytecode compiler more precise. Stack
  depths of various instructions were off by one for historical reasons. the
  errors carefully balanced each other out. Now code that does exception
  handling has smaller maximum bytecode stack sizes.
- Do not try ``__int__`` in ``PyLong_AsLong`` and ``PyLong_AsInt`` (:issue:`4949`)
- Make ``math.isinf.__self__`` == ``math`` to follow CPython's behaviour (:issue:`4959`)
- Fix post-build in-place ``venv`` creation (:issue:`4958`)
- Fix converting python object to ``unsigned long`` (in C) object attribute
  (:issue:`4996`)
- Add missing sysconfig value ``LDCXXSHARED`` (:issue:`5004`)
- Add missing ``token.SOFT_KEYWORD`` (:issue:`4962`)
- Update vendored CFFI version to 1.17.0 from 1.17.0dev1. No real changes, this
  will ensure ``pip install cffi`` does nothing.
- Implement more of ``asyncio``'s ``_overlap`` module on windows (:issue:`4008`)
- Disallow ``HAVE_LCHMOD`` like CPython on linux, since glibc has a dummy
  implementation that always errors out.


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Move the ``import`` fast path from ``IMPORT_NAME`` to ``__import__``, which
  speeds up explicitly calling the latter.
- Update OpenSSL in the "embedded" builds to 3.3.1, addressing a performance
  regression in urllib3 tests (:issue:`4877`)
- Speed up unicode encode/decode errormessage handling (:issue:`4972`). Before
  this fix, the ``surrogateescape`` codec was quadratic in some corner cases.
- Backport ``pyrepl`` and ``_colorize`` from CPython3.13
- Make ``TextIOWrapper.tell()`` about 100x faster (:issue:`5009`). Also fix
  some problems with ``seek`` and ``_multibytecodecs``.

.. _bpo-29334: https://github.com/python/cpython/issues/73520
