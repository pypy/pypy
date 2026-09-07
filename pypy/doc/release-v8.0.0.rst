======================================================================
PyPy v8.0.0: release of python 2.7, 3.11,3.12 beta released 2026-09-XX
======================================================================


..
  updated to ad87cbd9a6f27a94ae759905c171e87478490326

.. note
   This is a pre-release announcement. When the release actually happens, it
   will be announced on the https://pypy.org/blog

The PyPy team is proud to release version 8.0.0 of PyPy after the previous
release on May 26, 2026. This is a major new version, hence the bump to 8.0.0.
It is our first release of python 3.12, which may still have some bugs so we
are calling it "beta" quality. 

Why the move to 8.0.0
=====================

We have updated our linux buildbots (linux64, linux32, aarch64) to use
manylinux_2_28 images based on AlmaLinux 8 and glibc 2.28. These use gcc14
instead of the gcc5 previously used.  So our compiled tarballs will require at
least glibc2.28, which should be universally supported by now (Ubuntu 24.04
uses glibc2.39).

PyPy's python3.12 support comes with a new model for the way
we "hide" the PyPy-only extension to the C struct ``PyObject`` in a prefix before
the pointer we hand off to c-extension modules. This is described in-depth in :doc:`rawrefcount-and-the-gc`

What is new in codegen
======================

PyPy is written in RPython, and has code generation to translate RPython into
C. We have made some improvements to code generation in attempts to speed up the
base interpreter. While the speedups have not been that impressive, we have
made some steps forward:

- We now use `computed gotos`_ and more aggresively inline code. While this
  produces more compact sources, it does not boost performance as much as we
  wished.

- The source code includes comments mappng the source back to the RPython code
  that generated the block. This is very helpful to see exactly what is going on,
  and may enable further improvements.

Dropping HPy
============

We have dropped the internal `HPy`_ backend for PyPy. The HPy project's
understanding of how to use handles instead of pointers was a good prototype,
but the project did not attract enough supporters to become a new standard. The
code is still in the PyPy codebase, and can be toggled on with a `build option <pypy-python-interpreter-options>`_

Interpreters
============

The release includes three different interpreters:

- PyPy2.7, supporting the syntax and the features of
  Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
  backported security updates)

- PyPy3.11, supporting the syntax and the features of
  Python 3.11, including the stdlib for CPython 3.11.16. Barring security
  issues, this will be the last release to support 3.11.

- PyPy3.12, supporting the syntax and features of Python3.12, including the
  stdlib for CPython 3.12.14.

The interpreters are based on much the same codebase, thus the double
release. This is a micro release, all APIs are compatible with the other 7.3
releases.

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
making a CFFI_ version of your library that would be performant
on PyPy. Failing that, PyPy will soon support the cp312-abi3 tag for limited
ABI wheels supporting the CPython 3.12 ABI contract for 3.12 and above (which
makes ``Py_DECREF`` a function call, not a macro).  In any case,
`cibuildwheel`_ supports building wheels for PyPy.

.. rubric:: Footnotes

.. _`PyPy`: https://doc.pypy.org/
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: https://doc.pypy.org/project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _cppyy: https://cppyy.readthedocs.io
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _blog: https://pypy.org/blog
.. _HPy: https://hpyproject.org/
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html
.. _`computed gotos`: https://eli.thegreenplace.net/2012/07/12/computed-goto-for-efficient-dispatch-tables

What is PyPy?
=============

PyPy is a Python interpreter, a drop-in replacement for CPython.
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


Bugfixes
~~~~~~~~


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Use computed-goto on GCC/Clang instead of a big switch statement
- Explicitly inline stack checks at the beginning of each ``PyFrame``

Python 2.7
----------


Python 3.11
-----------

Bugfixes including missing compatibility with CPython 3.11
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~


