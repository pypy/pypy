============================================
PyPy v7.3.17: release of python 2.7 and 3.10
============================================

..
     updated to 9dcfbc87e2bc23a24df3be4e9548c45581e8db21

.. note::
    This is a pre-release announcement. When the release actually happens, it
    will be announced on the PyPy blog_

The PyPy team is proud to release version 7.3.17 of PyPy.

This release includes a new RISC-V JIT backend and a refactor of the python-
based REPL based on the work done for CPython 3.13. A special shout-out to
`Logan Chien`_ for the `RISC-V backend work`_.

The release includes two different interpreters:

- PyPy2.7, which is an interpreter supporting the syntax and the features of
  Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
  backported security updates)

- PyPy3.10, which is an interpreter supporting the syntax and the features of
  Python 3.10, including the stdlib for CPython 3.10.14.

The interpreters are based on much the same codebase, thus the dual
release. This is a micro release, all APIs are compatible with the other 7.3
releases. It follows after 7.3.16 release on April 23, 2024. We have dropped
PyPy3.9.

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

What is PyPy?
=============

PyPy is a Python interpreter, a drop-in replacement for CPython
It's fast (`PyPy and CPython 3.7.4`_ performance
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

.. _`PyPy and CPython 3.7.4`: https://speed.pypy.org
.. _`dynamic languages`: https://rpython.readthedocs.io/en/latest/examples.html

Changelog
=========

For all versions
----------------

- DOCS: Fix source links in docs when moving from heptapod to github (:issue:`3216`)
- DOCS: Mention ``externals`` mercurial repo for windows build (:issue:`4921`)

Bugfixes
~~~~~~~~

- Don't crash on constfolding field reads from null pointers (:issue:`4941`)
- Fix ``const char`` declaration in cffi gdbm (:issue:`4931`)
- Restore error message (:issue:`4954`)
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
- optimize patterns in listobject.py
    
  - certain calling patterns with ``*args``
  - calling ``find`` or ``count`` doesn't need the list object itself, just the
    underlying storage
  - unroll in more situations when creating a list
  - make list multiplication use ``ll_alloc_and_set`` if the list has length 1
  - copy lists in multiplication with ``log2(n)`` arraycopys instead of just
    copying n times (string multiplication does it like this too)
  - save one copy of the ``lhs`` list when adding two list

- add a jit driver for ``dict.__eq__`` and an especially fast implementation
  for mapdict equality
- Optimize ``x * -1`` and ``x // -1`` to ``-x``
- Speed up binary search on the ``utf8`` index storage. We can pick much better
  min and max indexes when we start which saves a few lookups.
- Optimize tri-state integers (shout-out to nirit100_).


.. _nirit100: https://github.com/nirit100
.. _`Logan Chien`: https://github.com/loganchien

Python 3.10
-----------

Bugfixes
~~~~~~~~

- Fix leak of global named resources using multiprocessing spawn (:issue:`python/cpython#90549`)
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
- Make sure to call ``space.finish()`` after receiving ``sigint`` (:issue:`4995`)
- Make stack depth computation more precise. Stack depths of various
  instructions were off by one for historical reasons. the errors carefully
  balanced each other out. Now code that does exception handling has smaller
  maximum stack sizes.
- Do not try ``__int__`` in ``PyLong_AsLong`` and ``PyLong_AsInt`` (:issue:`4949`)
- Make ``math.isinf.__self__`` == ``math`` to follow CPython's behaviour (:issue:`4959`)
- Fix post-build in-place ``venv`` creation (:issue:`4958`)
- Fix converting python object to ``unsigned long`` (in C) object attribute
  (:issue:`4996`)
- Add missing sysconfig value ``LDCXXSHARED`` (:issue:`5004`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Move the ``import`` fast path from ``IMPORT_NAME`` to ``__import__``
- Update OpenSSL in the "embedded" builds to 3.3.1, addressing a performance
  regression in urllib3 tests (:issue:`4877`)
- Speed up unicode encode/decode errormessage handling (:issue:`4972`)
- Backport ``pyrepl`` and ``_colorize`` from CPython3.13

.. _bpo-29334: https://github.com/python/cpython/issues/73520
