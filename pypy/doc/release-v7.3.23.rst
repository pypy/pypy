==============================================================
PyPy v7.3.23: release of python 2.7, 3.11, released 2026-05-26
==============================================================


..
  updated to ad87cbd9a6f27a94ae759905c171e87478490326

The PyPy team is proud to release version 7.3.23 of PyPy after the previous
release on April 26, 2026. This is a bug-fix release that fixes an overeager
warning about unused coroutines, and some problems around multiple inheritance
in c-extensions. 

This version includes a change to the bytecode interpreter to use `exception tables`_
instead of dedicated opcodes. Now the PyPy disassembly will be closer to
CPython format. So far it does not impact performance.

.. reverted
    We also include changes to code generation to use `computed
    gotos`_ and to more aggressively inline the stack checks when entering a
    ``PyFrame``. These do not yet show up as improvements in speed.pypy.org
    benchmarks, Our venerable benchmarker machine is using gcc5.4.1 (it was set up
    10 years ago when that was standard, like our manylinux 2014 buildbot machines)
    so we are hopeful an update to infrastructure will show the same improvements
    that we see when running benchmarks on more modern compilers.

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
.. _`exception tables`: https://github.com/python/cpython/blob/main/InternalDocs/exception_handling.md

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

- Fix a ``SystemError`` when ``OSError`` is raised in ``gc.dump_rpy_heap`` (:issue:`5118`)
- Fix bug in ``inline_short_preamble`` in the JIT (:issue:`5462`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Speed up ``int << int -> long`` shifts and leave the exponent of ``long **
  int`` as an int. This happens both on PyPy 2, where those types both still
  exist and on PyPy 3, where the distinction is a purely internal one, not
  observable to the programs.
- Detect performance-cluster L2 cache sizes instead of those of efficiency
  cores on Apple Silicon. This means that the GC nursery is now larger, because
  the size is chosen by looking at the L2 CPU cache.

.. reverted
    - Use computed-goto on GCC/Clang instead of a big switch statement
    - Explicitly inline stack checks at the beginning of each ``PyFrame``

Python 2.7
----------


Python 3.11
-----------

Bugfixes including missing compatibility with CPython 3.11
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Fix module and name for builtin classes with deeper hierarchies (:issue:`5296`)
- Remove over-eager warning emitted when ``cr_frame`` is accessed on a not
  started coroutine (:issue:`5454`)
- Fix ``typedef.doc`` to reject setting it to a ``getset`` (:issue:`5458`)
- Fix more ``__text_signature__`` incompatibilities (:issue:`5458`)
- Fix module name of ``_sqlite3`` exceptions to ``sqlite3`` like CPython
- ``datetime:fromisoformat`` raises without setting a context in
  ``_datetime.c``, do the same in datetime.py
- Use ``exceptiontable`` in the bytecode interpreter like CPython does
- Add ``_Py_NO_RETURN`` to ``_Py_FatalErrorFunc``
- Fix ``_pypyjson`` encoding of int subclasses (:issue:`5478`)
- Fixing a bug in computation of ``tp_basicsize`` for mixed python/c-extension
  types caused a bug in multiple inheritance with c-extension types used in
  pybind11. More closely follow the logic of CPython (:issue:`5481`)
- initialize ``MultibyteIncrementalDecoder.state`` to 0
- detect incomplete decorator input in the parser (:issue:`5484`)


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Improve the performance of ``str.splitlines``
- Restore lost ``heapq.merge()`` using a linked tournament tree which is slower
  in CPython but faster in PyPy. The code was lost in an stdlib update and
  reverted to the CPython version (:issue:`5466`)

