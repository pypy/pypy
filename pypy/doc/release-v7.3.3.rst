===============================================
PyPy v7.3.3: release of 2.7, 3.6, and 3.7 alpha
===============================================

.. note
  This is a draft, the version is not released yet

The PyPy team is proud to release the version 7.3.3 of PyPy, which includes
three different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.18

  - PyPy3.6: which is an interpreter supporting the syntax and the features of
    Python 3.6, including the stdlib for CPython 3.6.12.
    
  - PyPy3.7 beta: which is our second release of an interpreter supporting the
    syntax and the features of Python 3.7, including the stdlib for CPython
    3.7.9. We call this beta quality software, there may be issues about
    compatibility with new and changed features in CPython 3.7.
    Please let us know what is broken or missing. We have not implemented the
    `documented changes`_ in the ``re`` module, and a few other pieces are also
    missing. For more information, see the `PyPy 3.7 wiki`_ page
    
The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, all APIs are compatible with the 7.3
releases, but read on to find out what is new.

..
  The major new feature is prelminary support for the Universal mode of HPy: a
  new way of writing c-extension modules to totally encapsulate the `PyObject*`.
  The goal, as laid out in the `HPy blog post`_, is to enable a migration path
  for c-extension authors who wish their code to be performant on alternative
  interpreters like GraalPython_ (written on top of the Java virtual machine),
  RustPython_, and PyPy. Thanks to Oracle for sponsoring work on HPy.

Conda Forge now `supports PyPy`_ as a python interpreter. The support is quite
complete for linux and macOS. This is the result of a lot of
hard work and goodwill on the part of the Conda Forge team.  A big shout out
to them for taking this on.

Development of PyPy has moved to https://foss.heptapod.net/pypy/pypy.
This was covered more extensively in this `blog post`_. We have seen an
increase in the number of drive-by contributors who are able to use gitlab +
mercurial to create merge requests.

The `CFFI`_ backend has been updated to version 1.14.3. We recommend using CFFI
rather than c-extensions to interact with C, and using cppyy_ for performant
wrapping of C++ code for Python.

A new contributor took us up on the challenge to get `windows 64-bit`` support.
The work is proceeding on the ``win64`` branch, more help in coding or
sponsorship is welcome.

As always, this release fixed several issues and bugs.  We strongly recommend
updating. Many of the fixes are the direct result of end-user bug reports, so
please continue reporting issues as they crop up.

You can find links to download the v7.3.3 releases here:

    https://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
direct consulting work.

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: `PyPy`_
and `RPython`_ documentation improvements, tweaking popular modules to run
on pypy, or general `help`_ with making RPython's JIT even better. Since the
previous release, we have accepted contributions from XXX new contributors,
thanks for pitching in.

If you are a python library maintainer and use c-extensions, please consider
making a cffi / cppyy version of your library that would be performant on PyPy.
In any case both `cibuildwheel`_ and the `multibuild system`_ support
building wheels for PyPy.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _`CFFI`: https://cffi.readthedocs.io
.. _`cppyy`: https://cppyy.readthedocs.io
.. _`multibuild system`: https://github.com/matthew-brett/multibuild
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _`blog post`: https://morepypy.blogspot.com/2020/02/pypy-and-cffi-have-moved-to-heptapod.html
.. _`supports PyPy`: https://conda-forge.org/blog//2020/03/10/pypy
.. _`documented changes`: https://docs.python.org/3/whatsnew/3.7.html#re
.. _`PyPy 3.7 wiki`: https://foss.heptapod.net/pypy/pypy/-/wikis/py3.7%20status
.. _`wheels on PyPI`: https://pypi.org/project/numpy/#files
.. _`windows 64-bit`: https://foss.heptapod.net/pypy/pypy/-/issues/2073#note_141389
.. _`HPy blog post`: https://morepypy.blogspot.com/2019/12/hpy-kick-off-sprint-report.html
.. _`GraalPython`: https://github.com/graalvm/graalpython
.. _`RustPython`: https://github.com/RustPython/RustPython


What is PyPy?
=============

PyPy is a Python interpreter, a drop-in replacement for CPython 2.7, 3.6, and
3.7. It's fast (`PyPy and CPython 3.7.4`_ performance
comparison) due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

This PyPy release supports:

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 32 bits, OpenBSD, FreeBSD)

  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

  * 64-bit **ARM** machines running Linux.

PyPy does support ARM 32 bit processors, but does not release binaries.

.. _`PyPy and CPython 3.7.4`: https://speed.pypy.org
.. _`dynamic languages`: https://rpython.readthedocs.io/en/latest/examples.html

Changelog
=========

Changes shared across versions
------------------------------

C-API (cpyext) and c-extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python 3.6 only
---------------

Python 3.6 C-API
~~~~~~~~~~~~~~~~

.. _`issue 3187`: https://foss.heptapod.net/pypy/pypy/-/issues/3187
.. _`merge request 723`: https://foss.heptapod.net/pypy/pypy/-/merge_request/723
.. _31976: https://bugs.python.org/issue31976
