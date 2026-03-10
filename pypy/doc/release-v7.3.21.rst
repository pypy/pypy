==============================================================
PyPy v7.3.21: release of python 2.7, 3.11, released 2025-xx-xx
==============================================================


..
  updated to a601e091cc58457740528ac4e19a78ac8c498243

.. note::
       This is a pre-release announcement. When the release actually happens, it
    will be announced on the PyPy blog_.

.. note::
      Need to add release date

The PyPy team is proud to release version 7.3.21 of PyPy after the previous
release on July 4, 2025. This is a bug-fix release that also updates to Python
3.11.15.

The release includes two different interpreters:

- PyPy2.7, which is an interpreter supporting the syntax and the features of
  Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
  backported security updates)

- PyPy3.11, which is an interpreter supporting the syntax and the features of
  Python 3.11, including the stdlib for CPython 3.11.15.

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
making a HPy_ / CFFI_ / cppyy_ version of your library that would be performant
on PyPy. In any case, `cibuildwheel`_ supports building wheels for PyPy.

.. _`PyPy`: https://doc.pypy.org/
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: https://doc.pypy.org/en/latest/project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _cppyy: https://cppyy.readthedocs.io
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _blog: https://pypy.org/blog
.. _HPy: https://hpyproject.org/
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html


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

- update to pycparser v2.23
- bundle ``libz`` and ``libbz2`` into portable builds, for systems without them.

Bugfixes
~~~~~~~~

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Speed up ``int.bit_length`` (issue 5314)
- Refactor the ``rregister`` allocator in the Jit backends to store longevity
  without using a dict. This make the JIT backend quite a bit faster (roughly
  50%) by using a lot fewer dictionary lookups.
- const-fold ``x == x`` and ``x != x`` in ``backendopt``
- remove impossible code in ``_bitcount64``
- use one less instruction for regex character set membership testing
- make ``map`` on pypy2 faster
- add ``or`` constant reassociation and `and/or`` combination jit rules
- ``storesink`` and ``jtransform`` need to deal with invalid cast_pointer on
  constants, which happens when optimizing unreachable code.
- optimize ``xor`` constant reassociation

Python 3.11
-----------

- Update vendored ``libexpat`` to 2.7.4
- Update ``stdlib`` and version to 3.11.15
- update to pycparser v3.0.0, which does not support python2

Bugfixes including missing compatibility with CPython 3.11
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- percolate unicode locale numeric separators int formatting (:issue: `5311`)
- add newline to end of generated headers (issue 5312)
- allow ``'%lli'`` formatting code in ``PyUnicode_FromFormat*`` (issue 5313)
- set ``__new__`` to disallow instantiation when
  ``Py_TPFLAGS_DISALLOW_INSTANTIATION`` is set
- fix ``ht_qualname`` on ``TypeFromSpec`` (issue 5319)
- add macros needed for compilation of ``pytime.c`` in ``module/time`` on macOS
- allow str subclasses as argument of ``bytes/bytearray.fromhex`` (issue 5327)
- fix ``def func(): if a: f() or g()`` which crashed the byte compiler (issue 5328)
- change ``self.write_buffer`` to accept bytes in ``_overlapped`` (issue 5335)
- add license header to ``_lzma.py`` and ``_lzma_build.py`` (issue 5337)
- require ``vsnprintf`` in ``pyerrors.h`` (issue 5343) (:issue:`python/cpython#20899`)
- add ``Py_RETURN_RICHCOMPARE`` macro (issue 5350)
- make ``str`` methods ``split``, ``rsplit`` use the current unicode db version
  (issue 5370)
- Add ``_varname_from_oparg`` method to code objects
- set ``save_err=rffi.RFFI_SAVE_ERRNO`` for ``c_memfd_create()``.

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- make ``TextIOWrapper.write`` be inlined again by the JIT (issue 5375)
