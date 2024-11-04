==================================================
PyPy v7.3.14: release of python 2.7, 3.9, and 3.10
==================================================

The PyPy team is proud to release version 7.3.14 of PyPy.

Highlights of this release are compatibility with HPy-0.9_, cffi 1.16,
additional C-API interfaces, and more python3.10 fixes.

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
the project. Since the last release we have contributions from three new
contributors.  PyPy has many layers and we need help with all of them: bug
fixes, `PyPy`_ and `RPython`_ documentation improvements, or general `help`_
with making RPython's JIT even better.

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
- Add a part of CFFI 1.17. When in ABI mode, you can now use ``lib.funcname`` in
  many places where a ``<cdata>`` object was required. For instance, it can be
  used in a callback to a C function call, or written to a C structure field of
  the correct pointer-to-function type. You can also use ``ffi.cast()`` or
  `ffi.typeof()`` on it.
- Convert all usages of ``stat64`` to ``stat``, which fixes compilation on
  ``>=musl-1.2.4 libc`` (:issue:`4047`)

Bugfixes
~~~~~~~~
- Fix constfolding of ``str()`` without arguments (used to crash)
  (:issue:`4017`)
- Windows: remove wrong c-level define, use standard ``include`` instead
  (:issue:`4023`)
- Fix universal newline but non-translating ``text-io``: in this mode, two
  ``\r`` at the end of the file were combined into a single line by
  ``.readline()`` (:issue:`4037`)
- Fix segfault when JITting code which skips short preamble setup (:issue:`4030`)
- Align memoryview use of ``PyBUF_MAX_NDIM`` with python3 (:issue:`4040`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Fixes for compilation with gcc 14 and clang which enforce more strict C
  behaviour (:issue:`4041`)
- Avoid calling ``codepoints_in_utf8`` on the original input string again and
  again (:issue:`4027`)

Python 3.9+
-----------

- Improve ``os.scandir()`` handling of symlinks on Windows
- Remove extraneous debug print from ``_ssl`` (:issue:`4009`)
- Update cffi backend to 1.16.0, add HPy backend to 0.9
- When creating a venv from a symlinked venv, force symlinks. Portable builds
  need too many shared objects to allow copying only the executables
- Refactor calling finalizers in cpyext to make sure they are called

Bugfixes
~~~~~~~~
- If object does not have ``__len__``, default to ``pyobj.itemcount=0``
  (:issue:`4012`)
- Fix ``small_int.__rpow__(large_int)`` (:issue:`4015`)
- Make ``mmap.mmap.__setitem__`` accept a buffer (:issue:`4006`)
- In cpyext, when re-assigning to ``type.__bases__``, rebuild the type
  struct (:issue:`3975`)
- Remove newline in line read from ``PYPY_PORTABLE_DEPS.txt`` (:issue:`4018`)
- Fix astcompiler bug where sometimes a return with a value wasn't being
  caught inside an async generator (:issue:`4022`)
- Start implementing the ``ag_running`` logic of asynchronous generators
  (:issue:`3995`)
- Handle ``pathlib.path`` in ``PyUnicode_FSDecoder``, ``PyUnicode_FSDecoder``
  (:issue:`3168`)
- Raise ``OSError`` in ``gmtime`` like in ``localtime``
- Make the construction arguments of builtin types more introspectable
  (:issue:`4033`)
- Make sure an encoding in ``str.decode(encoding=xxx)`` does not have invalid
  surrogates

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Follow upstream performance patch for datetime.py (:issue:`4007`)
- Add ``os.getppid``, ``os.getlogin`` on windows (:issue:`4024`)
- Proactively call ``bufferview.releasebuffer`` when exiting a context manager
  and don't wait for ``gc`` to release it.
- Always initialize threads at startup, like in ``Py_Initialize`` for Cpython3.9
- Add a ``NULL`` byte to ``bytearray`` data, like CPython. (:issue:`4029`)
- Add ``hidden_applevel`` to ``_contextvars.Context.run``. Discovered in django
  PR 17500 to revive PyPy support in django
- Add window API functions ``PyErr_SetFromWindowsErrWithFilename``,
  ``PyErr_SetExcFromWindowsErrWithFilenameObject``,
  ``PyErr_SetExcFromWindowsErrWithFilenameObjects`` (:issue:`4034`)

Python 3.10
-----------

Bugfixes
~~~~~~~~
- ``LIST_EXTEND`` bytecode should just let all exceptions through if the second
  argument is iterable (:issue:`4031`)
- Pattern matching classes now use the full ``isinstance`` machinery, calling
  ``__instancecheck__`` too. (:issue:`4035`)

.. _bpo-41832: https://bugs.python.org/issue41832

