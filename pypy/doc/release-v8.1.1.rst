===============================================================
PyPy v8.1.1: release of python 2.7 and 3.12 released 2026-XX-XX
===============================================================

..
  updated to 3cc8dde36581e48a6d0b21ebc0ffabe10476c399

.. note::
   This is a pre-release announcement. When the release actually happens, it
   will be announced on the PyPy blog_

The PyPy team is proud to release version 8.1.1 of PyPy after the previous
release on Oct 14, 2026. We have dropped 3.11. Increased compatibility with
CPython's C API changed some of the structs exposed in the C headers, so we are
bumping the version to 8.1. We have seen a lot of activity: people
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

- Refactor backticks, has_key, ``ur""``, and bare tuples in comprehensions
  (:issue:`5740`)
- ``print()`` instead of the ``print`` statement (:issue:`5741`, :issue:`5744`)
- extregistry: build FlexibleWeakDict on object instead of DictMixin (:issue:`5749`)
- alias ``__bool__`` and ``__next__`` to the Python 2 names (:issue:`5747`)
- ``sorted()`` and Python 3 style iteration in host code (:issue:`5745`)
- flow space looks up host built-ins through ``twothree.builtins`` (:issue:`5751`)
- ``sys.maxsize`` instead of ``sys.maxint`` (:issue:`5746`)
- rename stdlib modules, via Python 2.7 spellings or twothree (:issue:`5753`)
- flowspace: decode bytecode into an instruction list before flowing (:issue:`5763`)


For all python versions
----------------

- Lazily import rpython.conftest (and hence pytest) during translation
  (:issue:`5654`)
- macos: sign dylibs with an ad-hoc signature in packaging to allow using the
  dylib (:issue:'5758`)
- Windows: cache msvc compiler env when running heavy compilation tests,
  massively speeds up test times
- remove rpython unicode from pypy, rpython/rlib, and associated tests (:issue:`5759`)
- packaging: speed up openssl ``'make install'``, extend macos gha translate timeout
- Add proofs for missing cases in knownbits shrinking (:issue:`5809`)

Bugfixes
~~~~~~~~
- aarch64: load float constants with a PC-relative LDR from a literal pool
  (:issue:`5649`)
- aarch64: add missing ``finish_once`` in assembler's runner
- aarch64: build ``+0.0`` and ``FMOV``-encodable float constants without a load (:issue:`5657`)
- rordereddict: don't leave GC pointers in entries emptied in place (:issue:`5686`)
- Windows: fix ``_ssl`` errors on 2.7
- prevent race in cffi codegen
- Move ``PYPY_JIT_DETECT_REENTRANCY``, used to print out a stack trace when
  testing PyPy and an imminent crash is detected, to an env variable
- Catch the reentrancy problem: defer asmmemmgr frees that reenter during a gc
- macos: Delay async exception handling tripped during running finalizers until
  the run is complete
- Windows: fix ``signal`` error handling
- Windows: wrap more system calls that can abort with ``SuppressIPH``
- Windows: resolve symlinks in ``resolvedirof``
- Windows: use ``wchr`` entry points for ``os.spawnv*`` (:issue:`5738`)
- Windows: better error reporting of waitstatus_to_exitcode (:issue:`5738`)
- fix set corruption when ``__eq__`` mutates the set in ``difference_update``
  and ``difference`` (:issue:`5765`)
- change ppc-64 to powerpc64le (python2.7 only)
- Don't rely on signed overflow when overallocating RPython lists
  (:issue:`5773`, :issue:`5799`)
- rsre: apply the zero-width protection of MIN_UNTIL to backtracked items
  (:issue:`5773`, :issue:`5798`)
- Windows: speed up GIL handoffs between threads (:issue:`5797`)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- rbigint: make shift loops vectorizable, no carry between iterations (:issue:`5707`)
- rbigint: improve arithmetic, shifts, and float conversion (:issue:`5750`)
- rbigint: vectorize bitwise operations (and/or/xor) (:issue:`5754`)
- Make ruleopt generate more compact and faster code (:issue:`5655`)
- Add integer simplifications for subtraction zero tests and left-shift
  overflow checks (:issue:`5633`)
- ruleopt IntBounds method contracts (:issue:`5732`)
- port the integer comparison optimizations to the rule DSL (:issue:`5722`)

Python 3.12
-----------

- Fix failing tests for windows64: ``-A`` test were not running at all, others
  were crashing
- Windows: add enough of rvmprof to get faulthandler working (:issue:`5725`)
- unicode.splitlines: add an ASCII fast path that scans bytes without decoding (:issue:`5719`)
- Allow importing cp312-abi3 c-extension modules, including building a
  python3.dll mapping library on windows and hacking at wheel tags supported by
  pip et.al to allow cp312-abi3 (:issue:`5578`)

C API
~~~~~

- Respect ``Py_TPFLAGS_SEQUENCE`` and ``Py_TPFLAGS_MAPPING`` in static types
  (:issue:`5736`)
- Fix type objects' refcount handling for subtypes of builtin types
  (:issue:`5736`)
- Copy all slots from the base ``pto`` (:issue:`5736`)
- Properly handle all the different ways to hit ``tp_dealloc`` (:issue:`5756`)
- Run ``tp_finalize`` and track it in the prefix like ``PyGC_HEAD``
  (:issue:`5743`)
- Run finalizers again after another collect to run both ``tp_dealloc`` and
  ``tp_finalize`` (:issue:`5803`)
- Refactor cdatetime to be compatible with cpython structs and headers (:issue:`5764`)
- remove unused ``PyBytesObject.ob_sstate`` (:issue:`5764`)
- Make len(bytesarray) and PyByteArray.ob_size match (:issue:`5764`)
- Add ``Py_LIMITED_API`` to headers and hide functions when it is defined (:issue:`5764`)
- Give interp-level builtins a ``PyCFunctionObject`` layout with a valid
  ``m_ml``, so the ``PyCFunction_GET_*`` macros work (:issue:`5803`)
- ``getsetdescr_attach``: fall back to the owning class when unbound (:issue:`5803`)
- Decrement tick counter on c-extension callbacks to allow GIL release (:issue:`5803`)
- testing: fix emulated GIL and untranslated GIL test in cpyext (:issue:`5803`)
- make strides, shape on Py_Buffer be pointers to view-owned data for
  compatibility with CPython for ABI3 (:issue:`5802`)
- Add a fast path through ``wrap_call`` for vectorcall (:issue:`5802`)
- Prefer running cpyext deallocators in the main thread (:issue:`5802`)
- cdatetime: use internal attributes instead of public setters for W_Datetime* attach (:issue:`5805`)
- Handle StackOverflow better in wrapped cpyext calls (:issue:`5810`, :issue:`5811`)


Testing
~~~~~~~

- ctypes tests: don't call a non-variadic function with partial argtypes
  (:issue:`5652`)
- cffi tests: port test_ffi_new_allocator_1 (:issue:`5651`)
- Remove tests that replicate lib-python tests (:issue:`5672`)
- rmmap: untranslated macOS arm64 JIT memory uses mprotect, not MAP_JIT
  (:issue:`5662`)
- PyPY's ``switchinterval`` is much higher than CPython's, causing races in some
  tests. Add explicit waits to improve reproducibility
- Backport ``_pytest`` changes to main (:issue:`5767`)
- Add a delay after starting the first test worker thread to prevent cache races (:issue:`5800`)
- Convert some app-level tests to new-style apptests (i.e. moving from test_abc.py to apptest_abc.py) (:issue:`5812`).

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
- Refactor LZMACompressor, LZMADecompressor to define ``__new__`` rather than
  ``__init__``
- posix: raise rather than return errno (:issue:`5711`)
- peepholer tests: turn jump + return into a return
- Windows: fix unicode conversions in array module (:issue:`5715`)
- Windows: simplify rpython unsetenv/delenv
- pathlib: cache ``pathlib._str`` early to reduce recursion frames
- Windows: make utime more precise via GetSystemTimePreciseAsFileTime
- fix pickle/unpickle of range-iterators
- Windows: modernize socket: use enums not macros, add a SIO_LOOPBACK_FAST_PATH
  to ioctl_w, fix dup, drop TCP_KEEPALIVE
- Rebuild exception subgroups exactly like CPython (:issue:`5713`)
- math.log: improve the robustness of the algorithm and special-case 2 and 10.
  (:issue:`5700`)
- implement more precise sum of floats following :issue:`python/cpython#100426`
  (:issue:`5720`)
- fix crash when trying to pass a non-dict object to a __dict__ descriptor's
  methods (:issue:`5733`)
- Windows: fix ``_sqlite3`` error reporting
- test_posix2: check major()/minor() of ``NODEV`` only on Linux, not macos
  (:issue:`5724`)
- Windows: fix exit code when trapping KeyboardInterrupt
- Windows: improve ``mmap`` error handling
- Windows: fill in more details of ``_overlapped`` for error states
- Windows: add listmounts (:issue:`5738`)
- Accept arguments in ``Pickler.__new__`` (:issue:`5727`)
- Add unused ``gc.callback`` for dask benchmark compatibility
- Make a venv-of-venv climb through the ``pyvenv.cfg`` chain to find the base
  pypy
- pickler: break reducer cycles for cloudpickle compatibility
- select: invalidate kqueue objects in a forked child (:issue:`5730`)
- Fix ``__reduce__`` of exhausted dict and set iterators (:issue:`5733`,
  :issue:`5735`)
- Fix ``__reduce__`` of enumerate over a list and of exhausted tee iterators
  (:issue:`5733`, :issue:`5737`)
- pickle: fix unpickling of missing memo entries and non-UTF-8 text lines
  (:issue:`5733`, :issue:`5780`)
- Fix BytesIO and StringIO crashes on huge positions and on closing in
  ``__index__`` (:issue:`5733`, :issue:`5739`)
- Raise MemoryError when an array's byte size overflows
  (:issue:`5733`, :issue:`5752`)
- Raise ValueError when a buffered stream is detached during an operation
  (:issue:`5733`, :issue:`5793`)
- Convert the size before checking that a buffered stream is open
  (:issue:`5733`, :issue:`5793`)
- Keep using the same iterator in ``islice.__next__`` during reentrant calls
  (:issue:`5733`, :issue:`5792`)
- Clamp start and end in the built-in codec error handlers
  (:issue:`5733`, :issue:`5796`)
- tee: call ``iter()`` twice, ignore ``__copy__``, and call nothing for n == 0.
  Also  objects for start or step that only define ``__index__``
  (:issue:`5705`, :issue:`5702`)
- itertools.count(): allow objects for start or step that only define ``__index__``
  (:issue:`5705`, :issue:`5702`)
- bytearray: Convert the item before reading the data in append/insert
  (:issue:`5768`, :issue:`5702`)
- sqlite3: read the backup error string with ``ffi.string()`` before decoding
  it (:issue:`5731`)
- Fix fatal AssertionError on multi-line fields in triple-quoted f-strings
  (:issue:`5776`)
- Build the nested f-string in ``test_fstring_nesting_limits`` without
  recursion (:issue:`5790`)
- tokenizer: Raise "invalid decimal literal" for bad float exponents in
  Tokenizer and remove old tokenizer (:issue:`5777`)
- tokenizer: Make DFA.recognize return the longest match (:issue:`5778`)
- tokenizer: Prove the whitespace match is non-negative (:issue:`5778`)
- Return the left operand's type from ``^`` when the left set is empty
  (:issue:`5774`, :issue:`5729`)
- Do not order equal steps in ``slice.__lt__``, add ``slice.__le__``,
  ``__gt__`` and ``__ge__`` (:issue:`5773`, :issue:`5729`)
- Check for a mapping before scanning a ``%(key)`` format (:issue:`5772`,
  :issue:`5729`)
- Check that the first argument of ``super()`` is a type whenever it is given
  (:issue:`5770`, :issue:`5729`)
- Return an ASCII repr unchanged from ``ascii()``
  (:issue:`5771`, :issue:`5729`)
- Accept and ignore arguments in ``_thread.RLock()``
  (:issue:`5786`, :issue:`5729`)
- Compute ``math.degrees()`` as ``x * (180 / pi)`` to improve accuracy
  (:issue:`5784`, :issue:`5729`)
- Take ``abs()`` of the converted value in one-argument ``math.gcd()``
  (:issue:`5783`, :issue:`5729`)
- Convert math.remainder() arguments like the other math functions
  (:issue:`5782`, :issue:`5729`)
- Store an exact int in itertools.count() for an int start with step 1
  (:issue:`5785`, :issue:`5729`)
- packaging: call ``build_cffi_imports`` with the target interpreter not the
  host interpreter, add a cc -arch flag for macos x86-64 (:issue:`5791`)
- marshal: pass the text of `TYPE_FLOAT`` and ``TYPE_COMPLEX`` to float() as
  bytes not str (:issue:`5795`)
- Check the length of the state in ``itertools.product.__setstate__`` (:issue:`5794`)
- Fix compiler crash on break/continue/return out of try/except*/finally
  (:issue:`5801`, :issue:`5806`)
- Fix ``readinto()`` of BufferedRandom reading buffered data twice
  (:issue:`5801`, :issue:`5813`)

Speedups
~~~~~~~~

- Use a proxy for unicode dict keys that does not require wrapping them into
  W_Unicode objects
