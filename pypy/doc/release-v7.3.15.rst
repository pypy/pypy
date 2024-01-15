==================================================
PyPy v7.3.15: release of python 2.7, 3.9, and 3.10
==================================================

The PyPy team is proud to release version 7.3.15 of PyPy.

This is primarily a bug-fix release, and includes work done to migrate PyPy to
Git and Github.

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
releases. It follows after 7.3.14 release on Dec 25, 2023

We recommend updating. You can find links to download the v7.3.15 releases here:

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
- Add github workflows to add branch names to git notes, translate, and run
  some tests.
- Activate the integration with readthedocs.io to generate documentation
  previews
- Change references to foss.heptapod.net to github.com
- Add a ``flaky`` test decorator and use it in CI to keep tests green
- Change IRC links to libera.chat, we moved a few years ago.

Bugfixes
~~~~~~~~
- Change ``PyBUF_MAX_NDIM`` back to 36 for ABI consistency (:issue:`4816`)
- Init ``sys.executable`` from ``GetModuleFileName`` on Windows (:issue:`4003`)


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Remove dead RPython code
- Improve the ability to run untranslated tests on top of PyPy2.7 (instead of
  CPython2.7)
- Speed up tracing function calls (both on the Python level as well as on the
  implementation level) by doing tail call optimization in the tracing
  interpreter. This might improve JIT warmup times and JIT memory usage a small
  amount for specific kinds of programs.

Python 3.9+
-----------

Bugfixes
~~~~~~~~

- Fix ``cffi*.dist-info`` directory name
- Fix for ``pypy -m venv --copies <target>`` where the source is a symlinked
  venv (:issue:`4838`)
- When updating a ``PyTypeObject``, do not assign c-level slots when the python
  type has no function to assign (:issue:`4826`). This showed up in a
  ``pybind11``-based project. The fix was to backport a change from Py3.10.

Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Generate shorter bytecode for ``namedtuple._replace``

Python 3.10
-----------

Bugfixes
~~~~~~~~
- Fix limited API guard for ``METH_FASTCALL`` to match CPython (:issue:`4050`)
- Implement ``Py_Is`` in terms of ``space.is_w`` (:issue:`4044`)
