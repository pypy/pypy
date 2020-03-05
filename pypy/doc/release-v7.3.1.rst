===================================================
WIP: PyPy v7.3.1: release of 2.7, 3.6, and 3.7alpha
===================================================

The PyPy team is proud to release the version 7.3.1 of PyPy, which includes
three different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.13

  - PyPy3.6: which is an interpreter supporting the syntax and the features of
    Python 3.6, including the stdlib for CPython 3.6.9.
    
  - PyPy3.7: which is an interpreter supporting the syntax and the features of
    Python 3.7, including the stdlib for CPython 3.7.x. This is the first
    public release of the version, so we would like to get feedback on its
    performance, stability, and compatibility.
    
The interpreters are based on much the same codebase, thus the multiple
release. This is a micro release, no APIs have changed, but read on to find
out what is new.

We have worked with the python packaging group to support tooling around
building third party packages for python, so this release updates the pip and
setuptools installed when executing `pypy -mensurepip` to `pip>=20`. This
completes the work done to update the PEP 425 "python tag". This means that
wheels specfically built for the previous tag format will not be discovered
by pip, so library authors should update their PyPY-specific wheels on PyPI.

Development of PyPy is transitioning to https://foss.heptapod.net/pypy/pypy.
This move was covered more extensively in the `blog post`_ from last month.

The `CFFI`_ backend has been updated to version XXXX. We recommend using CFFI
rather than c-extensions to interact with C, and using cppyy_ for performant
wrapping of C++ code for Python.

We have improved warmup time by up to 20%, performance of `io.StringIO` to
match if not be faster than CPython, and improved JIT code generation for
generators (and generator expressions in particual) when passing them to
functions like ``sum``, ``map``, and ``map`` that consume them.

As always, this release fixed several issues and bugs raised by the growing
community of PyPy users.  We strongly recommend updating. Many of the fixes are
the direct result of end-user bug reports, so please continue reporting issues
as they crop up.

You can find links to download the v7.3.1 releases here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
direct consulting work.

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: `PyPy`_
and `RPython`_ documentation improvements, tweaking popular modules to run
on pypy, or general `help`_ with making RPython's JIT even better. Since the
previous release, we have accepted contributions from 3 new contributors,
thanks for pitching in.

If you are a python library maintainer and use c-extensions, please consider
making a cffi / cppyy version of your library that would be performant on PyPy.
In any case both `cibuildwheel`_ and the `multibuild system`_ support
building wheels for PyPy wheels.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _`CFFI`: http://cffi.readthedocs.io
.. _`cppyy`: https://cppyy.readthedocs.io
.. _`available as wheels`: https://github.com/antocuni/pypy-wheels
.. _`portable-pypy`: https://github.com/squeaky-pl/portable-pypy
.. _`docker images`: https://github.com/pypy/manylinux
.. _`multibuild system`: https://github.com/matthew-brett/multibuild
.. _`cibuildwheel`: https://github.com/joerick/cibuildwheel
.. _`manylinux2010`: https://github.com/pypa/manylinux
.. _`blog post`: https://morepypy.blogspot.com/2020/02/pypy-and-cffi-have-moved-to-heptapod.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7, 3.6, and now 3.7. It's fast (`PyPy and CPython 2.7.x`_ performance
comparison) due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

This PyPy release supports:

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 32 bits, OpenBSD, FreeBSD)

  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

  * 64-bit **ARM** machines running Linux.

Unfortunately at the moment of writing our ARM buildbots are out of service,
so for now we are **not** releasing any binaries for the ARM architecture (32
bit), although PyPy does support ARM 32 bit processors. 

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://rpython.readthedocs.io/en/latest/examples.html


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

.. _`issue 3128`: https://bitbucket.com/pypy/pypy/issues/3120

.. _13312: https://bugs.python.org/issue13312


