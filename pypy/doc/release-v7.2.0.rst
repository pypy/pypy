====================================
PyPy v7.2.0: release of 2.7, and 3.6
====================================

The PyPy team is proud to release the version 7.2.0 of PyPy, which includes
two different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.13

  - PyPy3.6: which is an interpreter supporting the syntax and the features of
    Python 3.6, including the stdlib for CPython 3.6.9.
    
The interpreters are based on much the same codebase, thus the double
release.

This release removes the "beta" tag from PyPy3.6. While there may still be some
small corner-case incompatibilities (around the exact error messages in
exceptions and the handling of faulty codec errorhandlers) we are happy with
the quality of the 3.6 series and are looking forward to working on a Python
3.7 interpreter.

With the support of the ARM foundation, this release supports the 64-bit
``aarch64`` ARM architecture.

We updated our benchmark runner at https://speed.pypy.org to a more modern
machine and updated the baseline python to CPython 2.7.11. Thanks to `Baroque
Software` for maintaining the benchmark runner.

Until we can work with downstream providers to distribute builds with PyPy, we
have made packages for some common packages `available as wheels`_.

The `CFFI`_ backend has been updated to version 1.13.0. We recommend using CFFI
rather than c-extensions to interact with C, and `cppyy`_ for interacting with
C++ code.

As always, this release is 100% compatible with the previous one and fixed
several issues and bugs raised by the growing community of PyPy users.
We strongly recommend updating.

You can download the v7.2 releases here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
direct consulting work.

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: `PyPy`_
and `RPython`_ documentation improvements, tweaking popular modules to run
on pypy, or general `help`_ with making RPython's JIT even better. Since the
previous release, we have accepted contributions from 27 new contributors,
thanks for pitching in.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _`CFFI`: http://cffi.readthedocs.io
.. _`cppyy`: https://cppyy.readthedocs.io
.. _`available as wheels`: https://github.com/antocuni/pypy-wheels
.. _`Baroque Software`: https://baroquesoftware.com

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7, 3.6. It's fast (`PyPy and CPython 2.7.x`_ performance
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
so for now we are **not** releasing any binary for the ARM architecture (32
bit), although PyPy does support ARM 32 bit processors. 

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://rpython.readthedocs.io/en/latest/examples.html


Changelog
=========

Changes shared across versions

* Update ``cffi`` to 1.13.0

C-API (cpyext) improvements shared across versions

Python 3.6 only


