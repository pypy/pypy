=================================================
PyPy v7.3.11: release of python 2.7, 3.8, and 3.9
=================================================

..
       Changelog up to commit 207858e40e63

.. note_::
  This is a pre-release announcement. When the release actually happens, it
  will be announced on the `PyPy blog`_

.. _`PyPy blog`: https://pypy.org/blog

The PyPy team is proud to release version 7.3.11 of PyPy. As could be expected,
the first release of macOS arm64 impacted the macOS x86-64 build, so this is
a bug release to restore the ability of macOS users to run PyPy on ``macOS <
11.0``. It also incorporates the latest CPython stdlib updates released the day
after 7.3.10 went out, and a few more bug fixes. The release includes three
different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
    backported security updates)

  - PyPy3.8, which is an interpreter supporting the syntax and the features of
    Python 3.8, including the stdlib for CPython 3.8.16. Note we intend to drop
    support for this version in an upcoming release as soon as we release
    Pyython 3.10.

  - PyPy3.9, which is an interpreter supporting the syntax and the features of
    Python 3.9, including the stdlib for CPython 3.9.16.

The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, all APIs are compatible with the other 7.3
releases and follows quickly on the heals of the 7.3.10 release on Dec 6.

We recommend updating. You can find links to download the v7.3.11 releases here:

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

PyPy is a Python interpreter, a drop-in replacement for CPython 2.7, 3.8 and
3.9. It's fast (`PyPy and CPython 3.7.4`_ performance
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

Bugfixes
~~~~~~~~
- Fix several JIT optimizer bugs `using SMT solvers and fuzzing`_. The bugs
  were around integer optimations (issue 3832_).
- Only use ``pthread_jit_write_protect_np`` on macOS arm64 (issue 3865_).
- Add ``sysconfig.get_config_var('CONFINCLUDEPY')`` needed in some
  cross-compilations
- Package tkinter for macOS. Previously the portable builds did not include it
  (issues 3760_, 3868_).
- Fix memory leak in certificate validation in ``_ssl`` (issue 3871_)
- Add ``__qualname__`` to some cpyext types (issue 3878_)
- Clean up some deprecated functions in OpenSSL wrapper ``_ssl``


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Add pinned object count to gc collection stats reported in the
  ``on_gc_collect hook``

Python 3.8+
-----------

- Update stdlib for PyPy3.8 to 3.8.16 and for PyPy3.9 to 3.9.16. This brings
  some security fixes, as documented in the `CPython release note`_
- Ensure that only valid values are passed from ``Py_UNICODE_*`` calls to
  unicodedb lookups (issue 3870_) 
- Fix ast ``lineno``, ``end_lineno``, ``end_col_number`` around decorators (issue 3876_)
- Re-apply fix for issue 3436_ since our ensurepip setuptools version is ``< 59.0``
- In ``_tkinter``, ``getboolean``, ``getint``, ``getdouble`` accepts a ``Tcl_Obj`` (bpo-23880_)
- Make builtin ``credits``, ``license()`` more like CPython
- Add docstrings to some builtin classes and methods

Python 3.9
----------
- Fix pure-python implementation of ``functools`` (issue 3869_). see also cpython GH-100242_
- Remove ``type.__ne__``, the inherited behaviour from ``object.__ne__`` is the
  correct one (issue 3879_)
- Fix invalid parsing rule for ``genexps`` as the non-singular argument in a call (issue 3873_)

.. _`using SMT solvers and fuzzing`: https://www.pypy.org/posts/2022/12/jit-bug-finding-smt-fuzzing.html
.. _`CPython release note`: https://www.python.org/downloads/release/python-3816
.. _bpo-23880: https://bugs.python.org/issue23880
.. _GH-100242: https://github.com/python/cpython/issues/100242
.. _3436: https://foss.heptapod.net/pypy/pypy/-/issues/3436
.. _3760: https://foss.heptapod.net/pypy/pypy/-/issues/3760
.. _3832: https://foss.heptapod.net/pypy/pypy/-/issues/3832
.. _3865: https://foss.heptapod.net/pypy/pypy/-/issues/3865
.. _3868: https://foss.heptapod.net/pypy/pypy/-/issues/3868
.. _3869: https://foss.heptapod.net/pypy/pypy/-/issues/3869
.. _3870: https://foss.heptapod.net/pypy/pypy/-/issues/3870
.. _3871: https://foss.heptapod.net/pypy/pypy/-/issues/3871
.. _3873: https://foss.heptapod.net/pypy/pypy/-/issues/3873
.. _3876: https://foss.heptapod.net/pypy/pypy/-/issues/3876
.. _3878: https://foss.heptapod.net/pypy/pypy/-/issues/3878
.. _3879: https://foss.heptapod.net/pypy/pypy/-/issues/3879
