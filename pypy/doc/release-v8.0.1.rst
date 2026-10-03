===================================================================================
PyPy v8.0.1: bug-fix release of python 2.7, 3.11, and 3.12 beta released 2026-10-XX
===================================================================================

.. note::
   This is a pre-release announcement. When the release actually happens, it
   will be announced on the PyPy blog_

..
  updated to 71e2dba58c4

The PyPy team is proud to release version 8.0.1 of PyPy after the previous
release on Sept 25, 2026. This is a bugfix release. Some problems with buffer
memory leaks were fixed, and problems around the new strategy to tie RPython
objects to non-managed C ``PyObject`` objects were also fixed.

The release includes three different interpreters:

- PyPy2.7, supporting the syntax and the features of
  Python 2.7 including the stdlib for CPython 2.7.18+ (the ``+`` is for
  backported security updates)

- PyPy3.11, supporting the syntax and the features of
  Python 3.11, including the stdlib for CPython 3.11.16. Barring security
  issues, this will be the last release to support 3.11.

- PyPy3.12, supporting the syntax and features of Python 3.12, including the
  stdlib for CPython 3.12.14.

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

.. rubric:: Footnotes

.. _`PyPy`: https://doc.pypy.org/
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: https://doc.pypy.org/project-ideas.html
.. _CFFI: https://cffi.readthedocs.io
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _blog: https://pypy.org/blog
.. _HPy: https://hpyproject.org/
.. _direct consulting: https://www.pypy.org/pypy-sponsors.html
.. _`computed gotos`: https://eli.thegreenplace.net/2012/07/12/computed-goto-for-efficient-dispatch-tables
.. _`the README`: https://github.com/pypy/pypy/tree/py3.12/pypy/tool/pyhdrdump#pyhdrdump

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

- Fix translation when using CPython2.7 (:issue:`5586`)
- Fix dict reverse iteration when a iterator clears and refills the dict contents (:issue:`5596`)
- Update embedded OpenSSL to version 3.5.9

Python 3.11
-----------

- Change the order of arguments to CodeType() to match CPython and PyPy3.12 (:issue:`uqfoundation/dill#781`)

Python 3.11 and 3.12
--------------------

- cpyext: guard two more paths with ``pyobj_has_w_obj`` to avoid reviving dead
  ``w_obj`` during deallocation
- Any use of ``_ffi.from_buffer`` in lib_pypy needs to release the buffer (:issue:`5589`)
- Fix ``HMAC_CTX`` leak in ``_hashlib.hmac_new`` (:issue:`5599`)
- Make ``Lock`` and ``RLock`` 's 'lock' field mutable instead of quasi-immutable (:issue:`5602`)
- Avoid consulting ``__len__`` when creating a str, use ``len(value)`` instead (:issue:`5609`)
- Propagate lookup error in ``match_class_attr`` (:issue:`5611`)

Python 3.12
-----------

- cpyext: Label ``PyUnicode_EncodeCodePage`` with ``abi3=True``
- post-translation: Improve the distutils-replacement script (:issue:`5585`)
- cpyext: Refactor handling of out-of-band malloced objects with no room for a
  ``ob_pypy_link`` prefix
- cpyext: When handling a memoryviewobject, copy strides/shape instead of aliasing them
- cpyext: Implement PY_VECTORCALL_ARGUMENTS_OFFSET protocol in PyObject_VectorcallDict
- Make ``ElementTree::ParseError`` messages strings (:issue:`5605`)

