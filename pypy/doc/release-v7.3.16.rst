==================================================
PyPy v7.3.16: release of python 2.7, 3.9, and 3.10
==================================================

The PyPy team is proud to release version 7.3.16 of PyPy.

This release includes security fixes from upstream CPython, and bugfixes to the
garbage collector, described in a `gc bug-hunt blog post`_.

The release includes three different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
    backported security updates)

  - PyPy3.9, which is an interpreter supporting the syntax and the features of
    Python 3.9, including the stdlib for CPython 3.9.19.

  - PyPy3.10, which is an interpreter supporting the syntax and the features of
    Python 3.10, including the stdlib for CPython 3.10.14.

The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, all APIs are compatible with the other 7.3
releases. It follows after 7.3.15 release on Jan 15, 2024

We recommend updating. You can find links to download the v7.3.16 releases here:

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
.. _was sponsored: https://www.pypy.org/posts/2022/07/m1-support-for-pypy.html
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html
.. _`gc bug-hunt blog post`: https://www.pypy.org/posts/2024/03/fixing-bug-incremental-gc.html

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

- Make some RPython code Python3 compatible, including supporting `print()`
- Make ``test_transformed_gc`` tests more stable
- Document the ``%d`` feature in ``PYPYLOG`` env var file name
- Update vendored ``pycparser`` for its 2.22 release
- Raise default gc nursery size to 4MB (:issue:`4939`)

Bugfixes
~~~~~~~~

- Fix the action dispatcher in garbage collector hooks (:issue:`4899`)
- Fix ``'const'`` in signature of ``gdbm_open`` (:issue:`4926`)
- Fix garbage collector incminimark ``arraycopy`` incrementality bug
  (:issue:`4925,3959`)
- Fix pinning/shadow interaction bugs in the incminimark GC (:issue:`4900`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Move ``uint_mul_high`` to ``rarithmetic`` and add support for it in the
  metainterp
- Add a ``setattr`` shortcut to ``StdObjspace`` like the existing ``getattr``,
  and implement a ``STOR_ATTR`` optimization, and extend it to work for adding
  attributes as well.
- Update CFFI to 1.17.0dev0
- Constant-fold typeptr getfields
- Update to stdlib 3.9.19 including changes to `_ssl` and vendoring ``expat``
  into the repo
- Implement ``dict.__ror__`` (:issue:`4934`)

Python 3.9+
-----------

Bugfixes
~~~~~~~~

- ``_putwch`` on windows accepts a chr not an int (:issue:`4881`)
- Properly create ppc64 import suffixes for c-extensions (:issue:`4878`)
- Backport cpython fix to prevent subclassing datetime.timezone (:issue:`python/cpython#112453`)
- Remove top level ``__init__.py`` from stdlib (:issue:`4885`)
- Replace ``handshake_done`` with ``SSL_is_init_finished`` (bpo-29334_ from CPython3.5)
- Fix some subtle ``_ssl`` incompatibilities in error handling (:issue:`4883`)
- Port cffi change to better parse repetitive pragmas
  (:issue:`python-cffi/cffi#46`)
- Port cffi change to better parse complex number semantics on windows
  (:issue:`python-cffi/cffi#57`)
- Set ``tp_doc`` when defined in ``PyGetSetDef`` (:issue:`4898`)
- Use ``Py_UCS4`` not ``PY_UNICODE`` in various ``PyUnicode`` function input
  (:issue:`4901`)
- Make ``str.expandtabs()`` do the right thing with unicode characters and
  speed it up (:issue:`4920`)
- Fix ``'const'`` in signature of ``Tcl_Merge`` (:issue:`4926`)
- Close connection to avoid resource leak in ``multiprocessing.managers``
- Fix ``str.__mul__(str)`` to raise rather than return ``NotImplemented``
- Sync pure-python ``stat.py`` with upstream CPython3.13 to match C ``_stat``
  implementation of filemode

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Add ``PyModule_GetFilenameObject`` and ``PyModule_GetNameObject``
- Speed up ``normalize_exception`` by reduced copying
- Update xz-utils to 5.4.6 when building `_lzma`
- Add ``sys._git``

Python 3.10
-----------

Enhancements
~~~~~~~~~~~~

- Make stack depth computation more precise. Stack depths of various
  instructions were off by one for historical reasons. The errors carefully
  balanced each other out. Now code that does exception handling has smaller
  maximum stack sizes.

.. _bpo-29334: https://github.com/python/cpython/issues/73520
