==============================================================
PyPy v7.3.22: release of python 2.7, 3.11, released 2026-04-26
==============================================================


..
  updated to 5004b7cdb0e8f5df956db691cc92157337cf30a0

The PyPy team is proud to release version 7.3.22 of PyPy after the previous
release on March 13, 2026. This is a bug-fix release that fixes several issues
in the JIT. Among them, a long-standing JIT bug that started appearing when
some instance optimizations exposed it. We also cleaned
up many of the remaining stdlib test suite failures, which improves CPython
compatibility around line numbers in dis.dis, signatures and objclass
attributes for builtins, and other quality of life features.

There is now an RPython ``_pickle`` module that mirrors
the CPython one, greatly speeding up pickling operations. Where before PyPy was
5.7x slower than CPython on the pickle benchmark from the pyperformance
benchmark suite, now it is only 1.6x slower [0]_. We also added pypy
pickler extensions to dump and load lists using list strategies, and enabled
them in the ``ForkingPickler`` used by multiprocessing, speeding up cases where
such objects are passed between PyPy multiprocessing instances.

We also added an RPython json encoder, speeding up json_bench from being 2.6x
slower than CPython to being 0.7x (meaning faster).

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

.. [0] Once `a PR to pyperformance`_ to use the _pickle module on PyPy is accepted

.. _`PyPy`: https://doc.pypy.org/
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: https://doc.pypy.org/project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _cppyy: https://cppyy.readthedocs.io
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _blog: https://pypy.org/blog
.. _HPy: https://hpyproject.org/
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html
.. _`a PR to pyperformance`: https://github.com/python/pyperformance/pull/461

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

 - Fix instance dictionary field reordering logic, which could lead to a
   failing internal assertion error under some circumstances (:issue:`5377`).
 - Fix JIT invalidation logic of array items at a variable index, which could
   lead to incorrect results for list accesses when also calling methods on
   list objects (:issue:`5389`)
 - Fix segfaults in the JIT where the JIT optimizer would confuse RPython
   instances and arrays, leading to segfaults during JIT compilation
   (:issue:`5400`).
 - Fix duplicate 'const' in C code generation for nested const pointer types

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

 - Improve the performance of left-shifts of large integers, ie those backed by
   RPython's ``rbigints`` (:issue:`5404`).
 - Fix ~10ms GIL wakeup latency on Windows (:issue:`5391`)
 - Improve performance of ``complex`` powers with small integers as exponents
 - `Document the fact`__ that in PyPy instance dictionaries are not always
   ordered by insertion (:issue:`5436`).

.. __: cpython_differences#order-of-dictionary-keys-in-instance-dicts

Python 2.7
----------

 - Remove unsafe pickle file handling from bundled ply in pycparser v2. PyPy3
   uses pycparser v3

Python 3.11
-----------

 - Cherry-pick upstream ``_pydecimal`` fix from CPython (:issue:`5256`).
 - Add ``sys._stdlib_dir``
 - Disallow whitespace after sign character in ``int``/``float`` string parsing
   (:issue:`3927`)

Bugfixes including missing compatibility with CPython 3.11
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

 - Make ``itertools.pairwise`` reentrant (:issue:`python/cpython#109788`)
 - Fix possessive repeat in ``rsre`` search and match, fixing possessive regex bugs
 - Fix crash in the bytecode compiler related to the line numbers of return
   statements (:issue:`5419`).
 - Fixed line number output for function definitions with multiple decorators,
   f-strings, and related edge cases in ``dis`` output
 - Fixed pyrepl and ``pdb`` compatibility
 - cpyext: fix exposing ``__self__`` attribute on cpyext methods (:issue:`5368`)
 - cpyext: fix ``getsetdescr_attach`` to avoid redundantly rebuilding
   descriptors (:issue:`5402`)
 - cpyext: when checking for ``tp_new``, ignore ``object.__new__``
   (:issue:`5418`)
 - cpyext: fix flag propagation via inheritance and add flags to type objects
 - cpyext: fix ``tp_basicsize`` computation for mixed python/c-extension MRO
   types (:issue:`5402`)
 - cpyext: fix type layouts for types with ``tp_dictoffset`` or
   ``tp_weaklistoffset`` (:issue:`5402`)
 - cpyext: fix ``PyGC_Collect`` to better mimic a full collection cycle
 - Fix ``TextIOWrapper.readline(None)`` (:issue:`5379`)
 - Fix ``PREP_RERAISE_STAR`` dropping the current traceback (:issue:`5338`)
 - Fix missing case in ``astcompiler`` for multiple trinary expressions (:issue:`5419`)
 - Fix ``function.__get__(None)`` to raise ``TypeError`` like CPython
 - Fix multiple decorators raising exceptions in reverse order (:issue:`5213`)
 - Fix ``normalize_exception`` when called inside generators
 - Fix edge cases in generator and coroutine execution
 - Fix ``raise`` ignoring user modifications to ``__traceback__``
 - Fix segfault in ``Parser.diagnose()`` called after a successful parse
 - Fix error message for empty f-strings
 - Fix error messages for ``range()`` argument parsing
 - Fix edge cases in ``__future__`` handling and ``eval``
 - Fix unparse edge cases: lambda positional-only args, ``await`` in annotations
 - Fix multiline UTF-8 error messages
 - Fix encoding failures in ``_tkinter``
 - Fix various ``ctypes`` edge cases
 - Fix hpy debug mode failures
 - signal: handle failed wakeup-fd so it can be polled
 - Add more ``check_valid()`` calls to ``mmap``
 - Raise `SyntaxError` for unterminated single-quoted strings ending in newline in the REPL
 - Fix missing ``__reduce__`` on cpyext methods, exposed by ``_pickle`` (:issue:`5445`)
 - Fix signatures of some math functions (:issue:`5368`)
 - Add ``__doc__`` and ``__text_signature__`` to more cpyext types (:issue:`5368`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

 - pyrepl: implement ``set_completion_display_matches_hook``, ``parse_and_bind``,
   and ``set_pre_input_hook``
 - Generate default docstring from ``__text_signature__`` at ``interp2app``
 - Emit ``($self ...)`` for method signatures, used by ``inspect``
 - Make the first build of lib_pypy cffi modules quieter (:issue:`5428`)
 - Implement shared tuples in app-level ``marshal``
 - Speed up the cffi implementation of the fast path for ``hashlib.new(name, data).hexdigest()``
 - Speed up the ``sqlitesynth`` benchmark in ``_cffi_sqlite3``
