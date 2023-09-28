==================================================
PyPy v7.3.12: release of python 2.7, 3.9, and 3.10
==================================================

..
       Changelog up to commit ba2e9a6c433e

The PyPy team is proud to release version 7.3.12 of PyPy. 
This release includes a new string-to-int algorithm (also appearing in CPython
3.12) that is faster than the older one; support for symlinks in Windows; and
our first Python3.10 version.

The release includes three different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
    backported security updates)

  - PyPy3.9, which is an interpreter supporting the syntax and the features of
    Python 3.9, including the stdlib for CPython 3.9.17.

  - PyPy3.10, which is an interpreter supporting the syntax and the features of
    Python 3.10, including the stdlib for CPython 3.10.12. This is our first
    release of 3.10, but based on past experience we are quite confident in
    its compatibility with upstream. Of course, we recommend testing your code
    with this new version before putting it into production. Note it does
    require at least cython 0.29.35 or cython 3.0.0b3

The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, all APIs are compatible with the other 7.3
releases. It follows after 7.3.11 release on Dec 29, 2022

We recommend updating. You can find links to download the v7.3.12 releases here:

    https://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
`direct consulting`_ work. If PyPy is helping you out, we would love to hear about
it and encourage submissions to our blog_ via a pull request
to https://github.com/pypy/pypy.org

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: bug fixes,
`PyPy`_ and `RPython`_ documentation improvements, or general `help`_ with making
RPython's JIT even better. Since the previous release, we have accepted
contributions from one new contributor, thanks for pitching in, and welcome
to the project!

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
.. _was sponsored: https://www.pypy.org/posts/2022/07/m1-support-for-pypy.html
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html
.. _has built: https://www.pypy.org/posts/2022/11/pypy-and-conda-forge.html

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

  * 64-bit **ARM** machines running Linux (``aarch64``).

  * Apple **M1 arm64** machines (``macos_arm64``). 

  * **s390x** running Linux

PyPy support Windows 32-bit, Linux PPC64 big- and little-endian, and Linux ARM
32 bit, but does not release binaries. Please reach out to us if you wish to
sponsor binary releases for those platforms. Downstream packagers provide
binary builds for debian, Fedora, conda, OpenBSD, FreeBSD, Gentoo, and more.

.. _`PyPy and CPython 3.7.4`: https://speed.pypy.org
.. _`dynamic languages`: https://rpython.readthedocs.io/en/latest/examples.html

Changelog
=========

For all versions
----------------
- Update vendored version of pycparser
- Update to ssl 1.1.1u, 3.0.9; lzma 5.2.10; and gdbm 1.23 when embedding
  libraries for a portable build

Bugfixes
~~~~~~~~
- Allow creating ``ctypes.py_object()`` on a ``weakref`` (issue 3883_)
- Add memory pressure for malloc allocations in ``_ssl``, fix OpenSSL context use
- Pair OpenSSL allocation calls better with free calls in ``_ssl`` (issue 3887_)
- Only define ``SO`` in ``sysconfig`` if ``imp.get_suffixes()`` has
  ``imp.C_EXTENSION``
- Fix wrong assert in ``intutils``, it should be an ``InvalidLoop`` instead
  (issue 3892:_)
- export ``PyDescr_NewGetSet`` and define ``PyDescr_TYPE``, ``PyDescr_NAME``
- ``space.index(W_Bool)`` should return an ``int``, not a ``bool`` (issue 3906_)
- Skip cpython pickling of ``range``
- Support loading c-extension modules with both ``powerpc64le-linux-gnu`` and
  ``ppc_64-linux-gnu`` platform tags (issue 3834_)
- Fix various cases where a mutating ``__index__`` method could crash the
  interpreter (issue 3917_)
- Use C99 ``NAN`` for ``Py_NAN``


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Do less string copies in the bytecode compiler
- Add missing CJK range in unicodedata version 13
- Implement the base 10 ``string-to-int`` conversion using a divide an conquer
  algorithm with complexity ``O(n**1.58)``. The algorithm is due to Bjorn
  Martinsson and is part of CPython 3.12.
- Small refactoring in the JIT History class. It can now use the proper
  opencoder encoding of a trace immediately, not only after the inputargs are
  known
- Inline ``get_field_updater`` in JITted code to allow ``FieldUpdater`` to be
  alloc-removed everywhere
- Improve warmup a little bit:
  - directly put the two most common opcodes into the loop
  - add a special case for the int_add variant with a constant argument 

- Use the ``rbigint.add_int`` (etc) shortcuts for the ``int+int`` overflowing
  operations
- Optimize the ``goto_if_not_*`` code:
  - don't call replace_box for fresh boxes that can't be stored anywhere yet
  - make the "same box" shortcut faster


Python 3.9+
-----------

Bugfixes
~~~~~~~~
- Fix corner case when computing ``__main__.__file__`` (issue 3881_)
- Fix misnamed function (issue 3874_)
- Disallow pickle of ``staticmethod``, ``classmethod``, and ``DirEntry``
- Make sure that the max stackdepth is observed in method calls
- Fix ``utf-16`` and ``utf-32`` errorhandler replacement logic: if the
  replacement is bytes. those are just copied to the output
- Fix the problems of https://bugs.python.org/issue36819
- Fix ``str_decode_raw_unicode_escape`` for the case of ``\\``, which was
  incorrectly special-cased.
- Forbid null bytes in ``pwd.getpwnam``
- Use ``r_longlong`` math in nanosecond time for ``perf_counter`` on windows
  (issue 3890_)
- Fix for ``tuple.contains(obj)`` using ``item == obj`` (bpo-37648_)
- Allow indexing with a class with a ``__index__`` method
- Implement ``__copy__`` and ``__deepcopy__`` for ``zlib`` (de)compressors
- Fix weirdness about combining annotations and a global declaration of a
  name in some random function (issue 3925_)
- Fix wrong implementation of ``_copy_base`` for slices of n-dimensional
  buffers (issue 3520_)
- Trim the scope ID from IPV6 addresses (issue 3938_, reversing the decision in
  issue 3628_)
- Add ``_hashlib.scrypt`` (issue 3921_)
- Properly create a C-level wrapper that calls ``tp_finalize`` when ``__del__``
  is called, which allows us to use ``CYTHON_USE_TP_FINALIZE`` in cython
- Move ``hpy.dist-info`` to ``hpy-0.0.4.dist-info`` (issue 3579_)
- Fix edged cases in ``__rpow__`` and ``pow()`` (issues 3912_ and 3944_)
- Remove ``PyInt_FromLong`` which was leftover from Python2

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Speed up ``nametuple _replace`` by code generation (issue 3884_)
- Correct exception on positional arguments, while supporting empty namedtuple
  (?) at the same time
- Implement ``os.symlink`` and ``os.readlink`` on windows
- Fix ``os.mkdir`` for unicode handling via teaching rposix about utf-8 paths,
  which could lead to removing the last vestiges of unicode from rpython.
- Refactor ``os.remove``/``os.unlink`` to take symlink into account on windows
- Increment ``macosx-version-min`` to 10.9
- ``space.newlong`` returns a ``W_LongObject`` on pypy3, where there is no
  observable applevel difference between ``W_IntObject`` and ``W_LongObject``
- Provide ``_PyEval_GetAsyncGenFirstiter`` and ``_PyEval_GetAsyncGenFinalizer``
  for use by cython, towards fixing issue 3280_
- Squeeze a little more accuracy out of windows ``time.time()``, to make a
  cython test pass
- Use posonly args for ``list.__init__`` and ``set.__init__``, simplifying code
- Use ``rbigint.*_int`` fast paths for comparisons between ints

.. _bpo-37648: https://bugs.python.org/issue37648
.. _GH-100242: https://github.com/python/cpython/issues/100242
.. _3280: https://foss.heptapod.net/pypy/pypy/-/issues/3280
.. _3520: https://foss.heptapod.net/pypy/pypy/-/issues/3520
.. _3579: https://foss.heptapod.net/pypy/pypy/-/issues/3579
.. _3628: https://foss.heptapod.net/pypy/pypy/-/issues/3628
.. _3834: https://foss.heptapod.net/pypy/pypy/-/issues/3834
.. _3874: https://foss.heptapod.net/pypy/pypy/-/issues/3874
.. _3881: https://foss.heptapod.net/pypy/pypy/-/issues/3881
.. _3883: https://foss.heptapod.net/pypy/pypy/-/issues/3883
.. _3884: https://foss.heptapod.net/pypy/pypy/-/issues/3884
.. _3887: https://foss.heptapod.net/pypy/pypy/-/issues/3887
.. _3890: https://foss.heptapod.net/pypy/pypy/-/issues/3890
.. _3892: https://foss.heptapod.net/pypy/pypy/-/issues/3892
.. _3906: https://foss.heptapod.net/pypy/pypy/-/issues/3906
.. _3912: https://foss.heptapod.net/pypy/pypy/-/issues/3912
.. _3917: https://foss.heptapod.net/pypy/pypy/-/issues/3917
.. _3921: https://foss.heptapod.net/pypy/pypy/-/issues/3921
.. _3925: https://foss.heptapod.net/pypy/pypy/-/issues/3925
.. _3938: https://foss.heptapod.net/pypy/pypy/-/issues/3938
.. _3944: https://foss.heptapod.net/pypy/pypy/-/issues/3944
