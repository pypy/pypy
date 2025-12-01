==============================================================
PyPy v7.3.20: release of python 2.7, 3.11, released 2025-07-04
==============================================================

..
  updated to f956bdbc2bdaf680

The PyPy team is proud to release version 7.3.20 of PyPy after the previous
release on Feb 26, 2025. The release fixes some subtle bugs in ``ctypes`` and
``OrderedDict`` and makes PyPy3.11 compatible with an upcoming release of
Cython.

The release includes two different interpreters:

- PyPy2.7, which is an interpreter supporting the syntax and the features of
  Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
  backported security updates)

- PyPy3.11, which is an interpreter supporting the syntax and the features of
  Python 3.11, including the stdlib for CPython 3.11.13.

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
- Allow building with ``--withoutmod-cpyext``

Bugfixes
~~~~~~~~

- Fix crash when the JIT copies an empty virtual dict (:issue:`5245`)
- Fix ``re.fullmatch`` in the presence of atomic groups (:issue:`5232`) and
  possessive repeats (:issue:`5049`)
- Cleanup duplicate ``errcode`` var in ``pyssl_error()`` and duplicate
  ``get_socket_or_None()`` call in ``_SSLSocket.shutdown()`` (:issue:`5261`)
- Define ``_FILE_OFFSET_BITS`` and ``_LARGEFILE_SOURCE`` when building on
  32-bit ARM (on older platforms)
- Fix bug in ``OrderedDict.move_to_first`` (:issue:`5257`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Use ``wWinMain`` on Windows to remove the need for hand-written command line
  argument processing
- Optimize ``add(x, x)``
- Optimize ``getarrayitem(p, i)`` and ``getarrayitem(p, i)`` sequences again
  (which got lost in some refactoring)
- Add a Z3 memory model for heap accesses to be able to check the correctness
  of tests, and to find bugs in the optimizer with random traces.
- Make alias checking in the optimizer slightly smarter. in particular, two
  applevel instances of different classes are now known not to alias.
- Allow the annotator to const-fold ``len``
- Optimize ``list.__eq__`` with a jit driver (:issue:`5300`)

Python 3.11
-----------

- Update vendored ``libexpat`` to 2.7.1
- Update ``stdlib`` and version to 3.11.13 (:issue:`5290`)

Bugfixes
~~~~~~~~

- Raise ``SyntaxError`` rather than ``ValueError`` when parsing null bytes in
  source code (:issue: `5234`)
- Fix ``LOAD_GLOBAL`` disassembly (:issue:`5238`)
- Fix pure python ``datetime.*.fromisoformat()`` to reject spaces in fraction
  part. Backported to CPython. (:issue:`5240`), (:issue:`python/cpython#130959`)
- Fix ``LDLIBRARY`` in ``sysconfig`` (:issue:`5249`)
- Add ``IO_REPARSE_TAG_MOUNT_POINT`` to ``stat`` for windows
- Fix ``PyContextVar_Reset`` return type (:issue:`5252`)
- Add python3.8+ versions of ``Py_TRASHCAN`` macros (:issue:`3958`)
- Fix macos sysconfig ``LD*`` values (:issue:`pypa/distutils#283`)
- Add missing ``LIB_ERR_SYS`` handling to ``pyssl_error()``
  (:issue:`python-trio/trio#3253`)
- Return bytes for emptystring in ``re.findall()`` (:issue:`5265`)
- Handle single base class in ``PyType_FromModuleAndSpec`` (:issue:`5267`)
- Fix keepalive problems with ``ctypes._cast_addr`` (:issue:`5247`)
- Remove special-case for weakrefs in ``ctypes`` ``GlobalPyobjContainer``
- Allow deepcopying of some ctypes structs and fix pickling (:issue:`3022`)
- Fix declaration of ``PyLong_As*`` functions (:issue:`5272`)
- Fix ``EINTR`` handling in ``time.sleep()`` on macos
- Fix segfault when passing invalid closure to ``exec()``
- Fix ``*attr()`` type errors to match CPython
- Fix ``TypeError`` handling in ``map()`` and ``zip()`` to match CPython
- Add some missing invalid syntax cases for lambdas
- Add more ``zlib`` constants (:issue:`5289`)
- Fix obscure case when a unicodeescape error handler changes the string
- Add ``PyRange_Check`` (needed for newer cython)
- Implement ``PyModule_FromDefAndSpec2``, ``PyModule_FromDefAndSpec``
- Add PyGILState_GetThisThreadState (:issue:`5302`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Make ``int + long`` and ``int * long`` use ``rbigint.int_add`` and
  ``.int_mul``. This always worked on pypy2 but somehow never made it to 3.
- Add missing audit event in ``sys._getframe()``
- Speed up HPy object allocation by optimizing ``_finish_create_instance``
