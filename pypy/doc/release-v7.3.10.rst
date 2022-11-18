=================================================
PyPy v7.3.10: release of python 2.7, 3.8, and 3.9
=================================================

..
       Changelog up to commit e5129727dbe6

.. note::
  This is a pre-release announcement. When the release actually happens, it
  will be announced on the `PyPy blog`_

.. _`PyPy blog`: https://pypy.org/blog

The PyPy team is proud to release version 7.3.10 of PyPy. We have some nice
speedups and bugfixes we wish to share. The release includes three different
interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
    backported security updates)

  - PyPy3.8, which is an interpreter supporting the syntax and the features of
    Python 3.8, including the stdlib for CPython 3.8.15.

  - PyPy3.9, which is an interpreter supporting the syntax and the features of
    Python 3.9, including the stdlib for CPython 3.9.15. We have gained
    confidence in the stability of this version, and are removing the "beta"
    label.

The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, all APIs are compatible with the other 7.3
releases. Highlights of the release, since the release of 7.3.9 in March 2022
include:

  - A release of Apple Silicon M1 arm64 versions. This work `was sponsored`_ by
    an anonymous donor and is tested on our buildbots.
  - Update the packaged OpenSSL to 1.1.1s

We recommend updating. You can find links to download the v7.3.10 releases here:

    https://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
`direct consulting`_ work. If PyPy is helping you out, we would love to hear about
it and encourage submissions to our blog_ via a pull request
to https://github.com/pypy/pypy.org

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: `PyPy`_
and `RPython`_ documentation improvements, tweaking popular modules to run
on PyPy, or general `help`_ with making RPython's JIT even better. Since the
previous release, we have accepted contributions from XXX new contributors,
thanks for pitching in, and welcome to the project!

If you are a python library maintainer and use C-extensions, please consider
making a HPy_ / CFFI_ / cppyy_ version of your library that would be performant
on PyPy.
In any case both `cibuildwheel`_ and the `multibuild system`_ support
building wheels for PyPy.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _cppyy: https://cppyy.readthedocs.io
.. _`multibuild system`: https://github.com/matthew-brett/multibuild
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _blog: https://pypy.org/blog
.. _HPy: https://hpyproject.org/
.. _was sponsored: https://www.pypy.org/posts/2022/07/m1-support-for-pypy.html
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html

What is PyPy?
=============

PyPy is a Python interpreter, a drop-in replacement for CPython 2.7, 3.8 and
3.9. It's fast (`PyPy and CPython 3.7.4`_ performance
comparison) due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

This PyPy release supports:

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS 64 bits, Windows 64 bits, OpenBSD, FreeBSD)

  * 64-bit **ARM** machines running Linux. A shoutout to Huawei for sponsoring
    the VM running the tests.

  * Apple **M1 arm64** machines. 

  * **s390x** running Linux

  * big- and little-endian variants of **PPC64** running Linux,

PyPy support Windows 32-bit, PPC64 big- and little-endian, and ARM 32 bit, but
does not release binaries. Please reach out to us if you wish to sponsor
releases for those platforms.

.. _`PyPy and CPython 3.7.4`: https://speed.pypy.org
.. _`dynamic languages`: https://rpython.readthedocs.io/en/latest/examples.html

Changelog
=========

Default version (2.7+)
----------------------

Bugfixes shared across versions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fix zlib ``ustart`` handling for zlib v1.2.12 (issue 3717_)
- Backport security fixes to Python2.7
- Structseq improvements: hide ``structseqfield.__get__``, ignore any extra
  keys in the dict, preserve MapDict as the ``__dict__``, make fields immutable
  and more
- Fix embedding startup code in CFFI (issue 3619_)

Speedups and enhancements shared across versions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Update the HPy backend to 0.0.4
- Update CFFI to the latest HEAD (no new verson was released)
- Speed up ``dict.copy`` and ``emptydict.update(dict)``
- Optimization list sorting to allocate memory a bit less aggressively. seems
  to give ~10% on sorting non-tiny lists of ``ints``
- Speed up the python interpreter (jitted code is unchanged): auto-generate
  rpython-level shortcut methods for many special methods. This speeds up the
  interpreter greatly because we don't need to lookup the special method and
  don't need to go through the general call machinery at all. The effect is
  comparable to CPython's type slots, but all autogenerated from TypeDefs. it
  only works for built-in types at this point.
- Use structs to unpack ``longlong`` instead of casting to lltype Arrays
- Speed up the interpreter by caching global and builtin lookups on the code
  object
- Fix caching of reference constants in JitCodes
- Make the exception transformer not introduce calls to ``ll_issubclass``,
  instead emit the correct ``int_between`` for the type check directly
- Instead of encoding the liveness of local registers in each jitcode as a dict
  mapping pc to a (shared) instance of a class with three strings, do the
  following: add a live instruction in the jitcode that that has as its argument
  an offset into a string that compactly encodes liveness.
- Fast path for ``string[0]`` to convert a ``str`` to a ``char`` for when
  ``string`` is already a char
- Clean up a few single-use speciailized dictionaries
- Make ``list.count`` use the same fast paths as ``list.index`` (issue 3744_)
- Improve `int.bit_length`` for the jit: expose unwrapping and rewrapping to
  tracing
- Add a fast path for ``getrandbits(n)`` where ``n <= 31`` (issue 3733_)
- Remove useless ``cvt = converters.get(type(param))`` from sqlite3: it was
  wrong and slowed things down
- Add two new hints to ``rlib.jit``:

  - ``record_exact_value(var, const)`` tells the JIT that the box var must
    contain the value const.

  - ``record_known_result(result, func, *args)`` is a way to encode knowledge
    about the result of elidable functions. the hint means that the JIT can
    assume that if ``func(*args)`` will be called later, the outcome is
    ``result``

  Typical usecases of this are: you can express this way that functions are
  inverses of each other, or that a function is idempotent. Both hints need to
  be used very carefully, because getting them wrong can really lead to
  miscompilation and crashes.
- Add support for Apple Silicon M1 (arm64)
- Speed up ``posix.stat`` calls by directly constructing the output, avoiding a
  structseq

C-API (cpyext) and C-extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We are no longer backporting changes to the ``cpyext`` compatibility layer to
PyPy2.7.

Python 3.8+
-----------

Python 3.8+ bugfixes
~~~~~~~~~~~~~~~~~~~~
- Fix bug in the disassembler of py3 opcodes (issue 3700_)
- Raise ModuleNotFoundError instead of ImportError in some cases
- Fix lineno, col_offset for decorated functions and classes
- Add a ``name`` to ``sys.hash_info``
- Fix concurrency problem in buffered io reading (issue 3729_)
- Make it possible to multiple-inherit from KeyError again (issue 3728_)
- Check results from _openssl's ``EVP_DigestInit_ex`` and ``EVP_DigestUpdate``,
  and fix some failing tests (issue 3741_)
- Fix pickling of filters

Python 3.8+ speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Speed up ``fstrings`` by making the parentstack a resizable list of chars
- Better error message when the ``__iter__`` of a class is set to ``None`` (issue 3716_)
- Refactor the package.py script for better compatibility with conda-forge
- Add a jit driver for filter (issue 3745_)
- Improve opcode handling: ``jump_absolute``, ``int_xor``, and others

Python 3.8+ C-API
~~~~~~~~~~~~~~~~~
- Add ``PyReversed_Type``, ``PyUnicode_EncodeCodePage``, ``PyInterpreterState_GetID``,
- Map user defined python ``__init__`` to ``tp_init`` (issue 2806_)
- Fix PyDict_Contains (issue 3742_)

Python 3.8+
-----------

Python 3.9+ bugfixes
~~~~~~~~~~~~~~~~~~~~
- Fix ``f-string`` bug where the recursive tokenization was done incorrectly (issue 3751_)
- Fixes to repr and slots of nested GenericAliases (issue 3720_)

Python 3.9+ speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Adopt CPython changes to speed up fractions (issue 3746_, cpython-91851_)


Python 3.9+ C-API
~~~~~~~~~~~~~~~~~

.. _3716: https://foss.heptapod.net/pypy/pypy/-/issues/3716
.. _3720: https://foss.heptapod.net/pypy/pypy/-/issues/3720
.. _3751: https://foss.heptapod.net/pypy/pypy/-/issues/3751
.. _3700: https://foss.heptapod.net/pypy/pypy/-/issues/3700
.. _3728: https://foss.heptapod.net/pypy/pypy/-/issues/3728
.. _3729: https://foss.heptapod.net/pypy/pypy/-/issues/3729
.. _3733: https://foss.heptapod.net/pypy/pypy/-/issues/3733
.. _3742: https://foss.heptapod.net/pypy/pypy/-/issues/3742
.. _3741: https://foss.heptapod.net/pypy/pypy/-/issues/3741
.. _3744: https://foss.heptapod.net/pypy/pypy/-/issues/3744
.. _3745: https://foss.heptapod.net/pypy/pypy/-/issues/3745
.. _2806: https://foss.heptapod.net/pypy/pypy/-/issues/2806
.. _bpo34953: https://bugs.python.org/issue34953
.. _cpython-91851: https://github.com/python/cpython/issues/91851
