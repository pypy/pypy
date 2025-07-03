============================================================================
PyPy v7.3.19: release of python 2.7, 3.10 and 3.11 beta, released 2025-02-26
============================================================================

The PyPy team is proud to release version 7.3.19 of PyPy. This is primarily a
bug-fix release fixing JIT-related problems and follows quickly on the heels of
the previous release on Feb 6, 2025.


This release includes a python 3.11 interpreter. There were bugs in the first
beta that could prevent its wider use, so we are continuing to call this
release "beta". In the next release we will drop 3.10 and remove the "beta"
label. 

The release includes three different interpreters:

- PyPy2.7, which is an interpreter supporting the syntax and the features of
  Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
  backported security updates)

- PyPy3.10, which is an interpreter supporting the syntax and the features of
  Python 3.10, including the stdlib for CPython 3.10.16.

- PyPy3.11, which is an interpreter supporting the syntax and the features of
  Python 3.11, including the stdlib for CPython 3.11.11.

The interpreters are based on much the same codebase, thus the triple
release. This is a micro release, all APIs are compatible with the other 7.3
releases. It follows after 7.3.17 release on August 28, 2024.

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

.. _`PyPy`: https://doc.pypy.org/
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: https://doc.pypy.org/en/latest/project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _cppyy: https://cppyy.readthedocs.io
.. _`multibuild system`: https://github.com/matthew-brett/multibuild
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
- Improve the performance of rbigint formatting

Bugfixes
~~~~~~~~

- Fix compilation warnings and errors for latest gcc and latest clang (:issue:`5194`, :issue: `5195`, :issue:`5199`, :issue:`5201`, )
- Fix JIT segfault caused by ``BoxArrayIter`` improperly decoding the varsized length
- Fix corner case in unroll jit optimization (:issue:`5212`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

Python 3.10
-----------
- Remove distinfo around vendored ``readline`` module, to be more compatible
  with CPython.

Bugfixes
~~~~~~~~
- Match statements did not match ``None`` as a dictionary value (:issue:`5209`)
- Remove the extension suffix hack for ppc64le to fix using ``.pypy39*``
  suffix for PyPy3.10. This is a longstanding bug that should have been removed
  in the first PyPy3.10 release (:issue:`5196`).
- Use ``BIO_new_file`` not ``BIO_new_fp`` in ``_ssl`` since the later does not
  work on windows.
- Assign ``ht_qualname`` on builtin python types (:issue:`5217`)
- Ternary ``pow`` behaves differently with respect to calling ``__rpow__`` in
  the interpreter and via the C-API's ``tp_as_number.nb_power`` (:issue:`5207`)
- ``len(_weakset)`` could fail due to garbage collection while iterating,
  iterate over a copy instead (:issue:`5193`)
- Fix the tokenizer for combinations of line-continuations (back-slash) and
  indentation, fixes from an earlier fix were slightly wrong (:issue:`5221`)


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Make ``itertools.islice`` faster if no step is given, following
  https://discuss.python.org/t/python-3-13-0-speed/79547
- Add missing ``PyUnicode_DecodeRawUnicodeEscape``, ``PyUnicode_AsRawUnicodeEscapeString`` which are tested in cython, apparently not used elsewhere.

Python 3.11
-----------

Bugfixes
~~~~~~~~
- Add missing ``co_qualname`` to code objects, also fix ``PyCode_*`` signatures (:issue:`5203`)
- Fix printing traceback when the error line has trailing whitespace (:issue:`5219`)
- Fix segfault when ``__getattr__`` raises ``AttributeError`` (:issue:`5222`)
- Port missed PyPy3.10 fix for ``inspect.isbuiltin`` when ``obj`` is a
  C-extension function type. Fixes build of SciPy (:issue:`5227`)
