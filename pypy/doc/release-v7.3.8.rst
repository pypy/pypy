==========================================================
PyPy v7.3.8: release of python 2.7, 3.7, 3.8, and 3.9-beta
==========================================================

..
    Changelog up to commit 9c5e19c424af

.. note::
     This is a pre-release announcement. When the release actually happens, it
  will be announced on the `PyPy blog`_

.. _`PyPy blog`: https://pypy.org/blog

The PyPy team is proud to release version 7.3.8 of PyPy. It has been only a few
months since our last release, but we have some nice speedups and bugfixes we
wish to share. The release includes four different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
    backported security updates)

  - PyPy3.7,  which is an interpreter supporting the syntax and the features of
    Python 3.7, including the stdlib for CPython 3.7.12.

  - PyPy3.8, which is an interpreter supporting the syntax and the features of
    Python 3.8, including the stdlib for CPython 3.8.12. This is our third
    release of this interpreter, and we are removing the "beta" tag.

  - PyPy3.9, which is an interpreter supporting the syntax and the features of
    Python 3.9, including the stdlib for CPython 3.9.9. As this is our first
    release of this interpreter, we relate to this as "beta" quality. We
    welcome testing of this version, if you discover incompatibilites, please
    report them so we can gain confidence in the version.

The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, all APIs are compatible with the other 7.3
releases. Highlights of the release, since the release of 7.3.7 in late October 2021,
include:

  - Improvement in ssl


We recommend updating. You can find links to download the v7.3.8 releases here:

    https://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
direct consulting work. If PyPy is helping you out, we would love to hear about
it and encourage submissions to our blog_ via a pull request
to https://github.com/pypy/pypy.org

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: `PyPy`_
and `RPython`_ documentation improvements, tweaking popular modules to run
on PyPy, or general `help`_ with making RPython's JIT even better. Since the
previous release, we have accepted contributions from 7 new contributors,
thanks for pitching in, and welcome to the project!

If you are a python library maintainer and use C-extensions, please consider
making a CFFI_ / cppyy_ version of your library that would be performant on PyPy.
In any case both `cibuildwheel`_ and the `multibuild system`_ support
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

What is PyPy?
=============

PyPy is a Python interpreter, a drop-in replacement for CPython 2.7, 3.7, 3.8 and
3.9. It's fast (`PyPy and CPython 3.7.4`_ performance
comparison) due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

This PyPy release supports:

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 64 bits, OpenBSD, FreeBSD)

  * 64-bit **ARM** machines running Linux.

  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

PyPy support Windows 32-bit and ARM 32 bit processors, but does not
release binaries. Please reach out to us if you wish to sponsor releases for
those platforms. It also supports s390x, and big and little-endian variants of
PPC64 running Linux.

.. _`PyPy and CPython 3.7.4`: https://speed.pypy.org
.. _`dynamic languages`: https://rpython.readthedocs.io/en/latest/examples.html

Changelog
=========

Bugfixes shared across versions
-------------------------------

Speedups and enhancements shared across versions
------------------------------------------------

C-API (cpyext) and C-extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We are no longer backporting changes to the ``cpyext`` compatiblity layer to
PyPy2.7.


Python 3.7+ bugfixes
--------------------

- Fix various problems with the Windows ``_overlapped`` module (issue 3589_, )
- Fix error generation on ``_ssl`` in Windows
- Properly handle ``_PYTHON_SYSCONFIGDATA_NAME`` when importing ``_sysconfigdata``
- Restore broken revdb GC support

Python 3.7+ speedups and enhancements
-------------------------------------

- Use buffer pinning to improve CFFI-based ``_ssl`` performance
- Add a fast path in the parser for unicode literals with no ``\\`` escapes
- Prepare ``_ssl`` for OpenSSL3

Python 3.7 C-API
~~~~~~~~~~~~~~~~

- Added ``PyDescr_NewGetSet``,
- Fix segfault when using format strings in ``PyUnicode_FromFormat`` and ``PyErr_Format`` (issue 3593_)

Python 3.8+ bugfixes
--------------------

Python 3.8+ speedups and enhancements
-------------------------------------

Python 3.8 C-API
~~~~~~~~~~~~~~~~


.. _3589: https://foss.heptapod.net/pypy/pypy/-/issues/3589
.. _3593: https://foss.heptapod.net/pypy/pypy/-/issues/3593
