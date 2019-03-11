=========================================
PyPy v7.1.0: release of 2.7, and 3.6-beta
=========================================

The PyPy team is proud to release the version 7.1.0 of PyPy, which includes
two different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7

  - PyPy3.6-beta: this is the second official release of PyPy to support 3.6
    features, although it is still considered beta quality.
    
The interpreters are based on much the same codebase, thus the double
release.

Until we can work with downstream providers to distribute builds with PyPy, we
have made packages for some common packages `available as wheels`_.

As always, this release is 100% compatible with the previous one and fixed
several issues and bugs raised by the growing community of PyPy users.
We strongly recommend updating.

The PyPy3.6 release is still not production quality so your mileage may vary.
There are open issues with incomplete compatibility and c-extension support.

You can download the v7.0 releases here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
direct consulting work.

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: `PyPy`_
and `RPython`_ documentation improvements, tweaking popular modules to run
on pypy, or general `help`_ with making RPython's JIT even better.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _`cffi`: http://cffi.readthedocs.io
.. _`cppyy`: https://cppyy.readthedocs.io
.. _`available as wheels`: https://github.com/antocuni/pypy-wheels

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7, 3.6. It's fast (`PyPy and CPython 2.7.x`_ performance
comparison) due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

The PyPy release supports:

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 32 bits, OpenBSD, FreeBSD)

  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

Unfortunately at the moment of writing our ARM buildbots are out of service,
so for now we are **not** releasing any binary for the ARM architecture.

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://rpython.readthedocs.io/en/latest/examples.html


Changelog
=========

If not specified, the changes are shared across versions

