==================================================
PyPy v7.3.14: release of python 2.7, 3.9, and 3.10
==================================================

The PyPy team is proud to release version 7.3.14 of PyPy.

Hightlights of this release are compatibility with HPy-0.9_, additional C-API
interfaces, 

The release includes three different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
    backported security updates)

  - PyPy3.9, which is an interpreter supporting the syntax and the features of
    Python 3.9, including the stdlib for CPython 3.9.18.

  - PyPy3.10, which is an interpreter supporting the syntax and the features of
    Python 3.10, including the stdlib for CPython 3.10.13.

The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, all APIs are compatible with the other 7.3
releases. It follows after 7.3.13 release on Sept 29, 2023.

We recommend updating. You can find links to download the v7.3.14 releases here:

    https://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
`direct consulting`_ work. If PyPy is helping you out, we would love to hear about
it and encourage submissions to our blog_ via a pull request
to https://github.com/pypy/pypy.org

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: bug fixes,
`PyPy`_ and `RPython`_ documentation improvements, or general `help`_ with making
RPython's JIT even better.

If you are a python library maintainer and use C-extensions, please consider
making a HPy_ / CFFI_ / cppyy_ version of your library that would be performant
on PyPy. In any case, both `cibuildwheel`_ and the `multibuild system`_ support
building wheels for PyPy.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _cppyy: https://cppyy.readthedocs.io
.. _HPy-0.9: https://hpyproject.org/blog/posts/2023/10/hpy-0.9.0-fourth-public-release/
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
- Use OpenSSL 3.0.12 when embedding libraries for a portable build

Bugfixes
~~~~~~~~
- xxx

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- xxx

Python 3.9+
-----------

- Improve ``os.scandir()`` handling of symlinks on Windows

Bugfixes
~~~~~~~~
- xxx

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Follow upstream performance patch for datetime.py (:issue:`4008`)

Python 3.10
-----------

Bugfixes
~~~~~~~~
- xxx

.. _bpo-41832: https://bugs.python.org/issue41832
.. _2742: https://foss.heptapod.net/pypy/pypy/-/issues/2742

