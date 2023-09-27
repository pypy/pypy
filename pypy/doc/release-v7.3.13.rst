==================================================
PyPy v7.3.13: release of python 2.7, 3.9, and 3.10
==================================================

.. note::
     This is a pre-release announcement. When the release actually happens, it
  will be announced on the PyPy blog_


The PyPy team is proud to release version 7.3.13 of PyPy.
This is primarily a security/bug-fix release. CPython released security
patches, and this release also improves the ability to use multi-phase module
initialization from the C-API. There are also some small speed-ups.

The release includes three different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
    backported security updates)

  - PyPy3.9, which is an interpreter supporting the syntax and the features of
    Python 3.9, including the stdlib for CPython 3.9.18.

  - PyPy3.10, which is an interpreter supporting the syntax and the features of
    Python 3.10, including the stdlib for CPython 3.10.13. Note it requires at
    least cython 0.29.35 or cython 3.0.0b3.

The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, all APIs are compatible with the other 7.3
releases. It follows after 7.3.12 release on June 16, 2023.

We recommend updating. You can find links to download the v7.3.13 releases here:

    https://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
`direct consulting`_ work. If PyPy is helping you out, we would love to hear about
it and encourage submissions to our blog_ via a pull request
to https://github.com/pypy/pypy.org

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: bug fixes,
`PyPy`_ and `RPython`_ documentation improvements, or general `help`_ with making
RPython's JIT even better.

If you are a python library maintainer and use C-extensions, please consider
making a HPy_ / CFFI_ / cppyy_ version of your library that would be performant
on PyPy. In any case, both `cibuildwheel`_ and the `multibuild system`_ support
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
- Update to ssl 1.1.1w, or 3.0.10 when embedding libraries for a portable build

Bugfixes
~~~~~~~~
- Report exceptions that are created when forcing an oefmt as unraisable (issue
  _3978)

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Do type-erasure for rpython dicts and lists more generally, unifying all gced
  pointer types into one implementation (as opposed to just unifying all
  *instances* together, but not eg strings). This makes pypy-c ~700KiB smaller.
- Stop allocating three lists of length 256 for the registers in the MIFrames
  and the blackhole frames. Almost all jitcodes have much smaller frame sizes.
  Seems to make tracing a little bit faster.
- Improve ``strip()`` to not force the object
- Make sure that ``sys.flags`` are not in a cell in the sys module to speed up
  access (especially important on py3.x, where every bytes.decode call checks
  sys.flags.utf8_mode)
- Speed up the flowspace a lot for huge functions
- Make ``UnicodeIO`` store its data in a list of ``r_int32``, as opposed to
  using the rpython (Python2.7) unicode type. we want to get rid of the unicode
  type and also it requires an extra copy all the time.
- Make every ``rbigint`` one word smaller by storing the sign in the size field

Python 3.9+
-----------
- Create c-extension modules used in tests as part of the build (in
  package.py), not as part of testing

Bugfixes
~~~~~~~~
- More selectively clear ``StopIteration`` exceptions on ``tp_iternext`` (issue
  _3956)
- Copy less when creating a venv by using a ``PYPY_PORTABLE_DEPS.txt`` file to
  state which dlls to copy in a portable build (issue _3611)
- On macos ``sendifle`` can return an error while sending part of the file
  (issue _3964)
- Fixes on both app-level and C level for ``Py_TPFLAGS_BASETYPE=0`` (issue
  _2742). Also set ``PyType_Type.tp_itemsize`` to ``sizeof(PyMemberDef)`` like
  on CPython
- Fix ``PyType_FromSpecWithBases`` to correctly use ``Py_tp_doc``,
  ``Py_tp_members`` in spec, fix ``__module__`` assignment, better handle
  ``__name__`` and ``tp_name``
- Hide ``functools`` wrappers from the stack when reporting warnings (issue
  _3988)
- Fix edge case of datetime isoformat parsing (issue _3989)
- Accept NULL ``tp_doc`` (_bpo-41832)
- Align ``nb_int`` with ``PyNumber_Long`` (to get consistent error messages)
- Handle ``pathlib.Path`` objects in ``_ssl`` (issue _4002)
- Implement ``_PyLong_AsInt`` which is not part of the stable API but used in
  testing

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Avoid compiling a new regex where not needed (in email, csv,  and
  elsewhere) (issue _3961)

Python 3.10
-----------

Bugfixes
~~~~~~~~
- Fix, test locking in HMAC update (issue _3962)
- When re-assigning to ``type.__bases__``, rebuild the cpyext type struct
  (issue _3976)
- Add missing slot macro ``Py_am_send`` (issue _3990)

.. _bpo-41832: https://bugs.python.org/issue41832
.. _GH-100242: https://github.com/python/cpython/issues/100242
.. _2742: https://foss.heptapod.net/pypy/pypy/-/issues/2742
.. _3611: https://foss.heptapod.net/pypy/pypy/-/issues/3611
.. _3956: https://foss.heptapod.net/pypy/pypy/-/issues/3956
.. _3961: https://foss.heptapod.net/pypy/pypy/-/issues/3961
.. _3962: https://foss.heptapod.net/pypy/pypy/-/issues/3962
.. _3964: https://foss.heptapod.net/pypy/pypy/-/issues/3964
.. _3976: https://foss.heptapod.net/pypy/pypy/-/issues/3976
.. _3978: https://foss.heptapod.net/pypy/pypy/-/issues/3978
.. _3988: https://foss.heptapod.net/pypy/pypy/-/issues/3988
.. _3989: https://foss.heptapod.net/pypy/pypy/-/issues/3989
.. _3990: https://foss.heptapod.net/pypy/pypy/-/issues/3990
.. _4002: https://foss.heptapod.net/pypy/pypy/-/issues/4002

