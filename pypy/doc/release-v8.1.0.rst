===============================================================
PyPy v8.1.0: release of python 2.7 and 3.12 released 2026-XX-XX
===============================================================

..
  updated to 9775987f9c43ad2bbace1e2bf447af07e570b1a8

.. note::
   This is a pre-release announcement. When the release actually happens, it
   will be announced on the PyPy blog_

The PyPy team is proud to release version 8.1.0 of PyPy after the previous
release on Oct 14, 2026. We have dropped 3.11. Increased compatibility with
CPython's C API changed some of the structs exposed in the C headers, so we are
bumping the version to 8.1. The past month has seen a lot of activity: people
have been using various tools to fuzz and analyse the interpreter and this has
led to a lot of churn for edge case compatibility and crash protection. We have
also started passing many more tests on all platforms, and have removed the last
vestiges of RPython unicode from the interpreter, allowing us to simplify
RPython. This becomes important as the long-term effort to make RPython
compatible with python3 (rpython3_ )has move forward.

The release includes three different interpreters:

- PyPy2.7, supporting the syntax and the features of
  Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
  backported security updates)

- PyPy3.12, supporting the syntax and features of Python 3.12, including the
  stdlib for CPython 3.12.15.

The interpreters are based on much the same codebase, thus the triple
release.

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
ABI wheels.  In any case, `cibuildwheel`_ supports building wheels for PyPy.

.. _`PyPy`: https://doc.pypy.org/
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: https://doc.pypy.org/project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _blog: https://pypy.org/blog
.. _HPy: https://hpyproject.org/
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html
.. _rpython3: https://github.com/pypy/pypy/issues/5601

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

RPython3
--------



For all python versions
----------------

- Lazily import rpython.conftest (and hence pytest) during translation
  (:issue:`5654`)
- Make ruleopt generate more compact and faster code (:issue:`5655`)

Bugfixes
~~~~~~~~
- aarch64: load float constants with a PC-relative LDR from a literal pool
  (:issue:`5649`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

Python 3.12
-----------

- Fix failing tests for windows64: ``-A`` test were not running at all, others
  were crashing

C API
~~~~~

Testing
~~~~~~~

- ctypes tests: don't call a non-variadic function with partial argtypes (:issue:`5652`)
- cffi tests: port test_ffi_new_allocator_1 (:issue:`5651`)
- Remove tests that replicate lib-python tests (:issue:`5672`)
- rmmap: untranslated macOS arm64 JIT memory uses mprotect, not MAP_JIT (:issue:`5662`)

Other bugfixes including missing compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Improve ``_ssl`` error types and handling
- Normalize ``fsenc`` in ``get_special_char()`` so it does not return None
  (:issue:`5650`)
- ``_curses``: declare the wide-character functions on darwin (:issue:`5661`)
- always use utf-8/surrogateescape for fsencode/fsdecode, fixes darwin failures
  (:issue:`5659`)
- ``time.strftime``: only pass ASCII runs of the format to ``wcsftime()`` (:issue:`5665`)
- Add fcopyfile() on darwin (:issue:`5670`) that needed an rpython helper (:issue:`5671`)
- Skip the codec lookup when decoding empty input outside dev mode (:issue:`5669`)
- Read ``ZLIB_RUNTIME_VERSION`` at runtime startup, rather than at build
- Backport 3.16 ``bz2.version`` and ``bz2.version_info`` to report the runtime
  bz2 version (:issue:`5666`)
- Use zlib-ng on macos via the pypy/externals repo during translation
- decode_object: check for empty input after the ascii/utf-8 fast paths
  (:issue:`5673`)
- test_all_pathconf_defined: allow the OS to reject a name for this fd
  (:issue:`5674`)
- app_main: ``PYTHONOPTIMIZE=0`` and similar flags mean ``off`` (:issue:`5679`)
- Refactor ``is_python_function`` to report hidden applevel code as-if it is a
  builtin. Fixes ``_lsprof`` by insuring each ``CALL`` has a matching return
- Fix ``get_channel_binding`` in ``_ssl`` (:issue:`5676`)
- posix: count OS threads on darwin for the ``fork()`` warning, and include the
  ``pid`` in the warning (:issue:`5682`)
- array: add ``__class_getitem__`` (:issue:`5683`)
- pyrepl: rename ``append_history_file()`` to ``append_unsaved_history()`` and
  define ``append_history_file(nelements, filename=None, /)`` like readline
  (:issue:`5680`)
- test_mmap: collect leftover mmaps before removing the test file, important on
  windows (:issue:`5685`)
- ``_socket``: check that the ``fileno`` passed to ``socket()`` is a socket,
  important on macos (:issue:`5687`)
- Restore many PyPy-specific stdlib adaptations from 3.11 to 3.12 (:issue:`5684`)
- ``except*``: support ``BaseExceptions`` that are not ``Exceptions`` (:issue:`5689`)- pdb: port remote debugging support from CPython (:issue:`5667`)
- generators: warn about the 3-argument ``throw()`` (:issue:`5692`)
- Use different docstrings for coroutines and generators, even though they
  share common code (:issue:`5691`)
- Fix ``strftime`` on windows for a year before 1900
- Add missing _winapi and nt interfaces for windows (:issue:`5708`)
- Set ``__module__`` of ``operator.attrgetter``, ``itemgetter`` and
  ``methodcaller`` to ``'operator'`` (:issue:`5695`)
- Use ``__index__`` when doing ``__float__`` (:issue:`5696`)
- math.factorial: convert the argument with ``index()`` before checking its
  range (:issue:`5699`)
- Only accept an exact int in csv.field_size_limit() (:issue:`5703`)
- Validate the islice() arguments before calling iter() on the iterable (:issue:`5704`)
- Add ``__reduce__`` to ``_operators.*``
- add a ``ReopeningLookup`` subclass to read the central ``ZipFile`` directory
  once and close the archive, allowing windows to release the file
- update CFFI's pycparser to 3.12
- Fix start position in ``CALL_METHOD``
- Check ``global`` arg to ``warn_explicit``
- Remove ``f`` -> ``g`` formatting conversion for large floats (:issue:`5706`)
- Get rid of RPython unicode and use ``surrogatepass`` on windows (:issue:`5709`)
- Port CPython3.13 ``pytime.c`` to get ns resolution on windows (:issue:`5376`)
- Windows: fix ``os.stat`` for a file that cannot be opened
- Windows: fix and use winconsoleio by default
- Pickler: use DEFAULT_PROTOCOL not HIGHEST_PROTOCOL (:issue:`5710`)
