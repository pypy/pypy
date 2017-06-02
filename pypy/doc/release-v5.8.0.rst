=====================================
PyPy2.7 and PyPy3.5 v5.8 dual release
=====================================

The PyPy team is proud to release both PyPy2.7 v5.8 (an interpreter supporting
Python v2.7 syntax), and a beta-quality PyPy3.5 v5.8 (an interpreter for Python
v3.5 syntax). The two releases are both based on much the same codebase, thus
the dual release.  Note that PyPy3.5 supports Linux 64bit only for now. 

This new PyPy2.7 release includes the upstream stdlib version 2.7.13, and
PyPy3.5 (our first in the 3.5 series) includes the upstream stdlib version
3.5.3.

We continue to make incremental improvements to our C-API
compatibility layer (cpyext). PyPy2 can now import and run many C-extension
packages, among the most notable are Numpy, Cython, and Pandas. Performance may
be slower than CPython, especially for frequently-called short C functions.
Please let us know if your use case is slow, we have ideas how to make things
faster but need real-world examples (not micro-benchmarks) of problematic code.

Work proceeds at a good pace on the PyPy3.5
version due to a grant_ from the Mozilla Foundation, hence our first 3.5.3 beta
release. Thanks Mozilla !!! While we do not pass all tests yet, asyncio works and
as `these benchmarks show`_ it already gives a nice speed bump.
We also backported the ``f""`` formatting from 3.6 (as an exception; otherwise
"PyPy3.5" supports the Python 3.5 language).

CFFI_ has been updated to 1.10, improving an already great package for
interfacing with C.

As always, this release fixed many issues and bugs raised by the
growing community of PyPy users. We strongly recommend updating.

You can download the v5.8 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project.

We would also like to thank our contributors and
encourage new people to join the project. PyPy has many
layers and we need help with all of them: `PyPy`_ and `RPython`_ documentation
improvements, tweaking popular `modules`_ to run on pypy, or general `help`_
with making RPython's JIT even better.

.. _CFFI: https://cffi.readthedocs.io/en/latest/whatsnew.html
.. _grant: https://morepypy.blogspot.com/2016/08/pypy-gets-funding-from-mozilla-for.html
.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`modules`: project-ideas.html#make-more-python-modules-pypy-friendly
.. _`help`: project-ideas.html
.. _`these benchmarks show`: https://morepypy.blogspot.com/2017/03/async-http-benchmarks-on-pypy3.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7 and CPython 3.5. It's fast (`PyPy and CPython 2.7.x`_ performance comparison)
due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

The PyPy 2.7 release supports: 

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 32 bits, OpenBSD, FreeBSD)
  
  * newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux,
  
  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://rpython.readthedocs.io/en/latest/examples.html

Highlights of the PyPy2.7, cpyext, and RPython changes (since 5.7 released March, 2017)
=======================================================================================

See also issues that were resolved_

* New features and cleanups

  * Implement PyModule_New, 
  * Fix for multiple inheritance in app-level for C-API defined classes
  * Revert a change that removed tp_getattr (Part of the 5.7.1 bugfix release)
  * Document more differences with CPython here_
  * Add native PyPy support to profile frames in vmprof
  * Fix an issue with Exception order on failed import
  * Fix for a corner case of __future__ imports

* Bug Fixes

  * Correctly handle dict.pop where the popping key is not the same type as the
    dict's and pop is called with a default (Part of the 5.7.1 bugfix release)
  * Improve our file's universal newline .readline implementation for
    ``\n``, ``\r`` confusion

* Performance improvements:

  * Tweaks made to improve performance by reducing the number of guards
    inserted in jitted code, based on feedback from users
  * Add garbage collector memory pressure to some c-level allocations

* RPython improvements

  * Improve the default shadowstack garbage collector, fixing a crash with
    multithreaded code and other issues
  * Make sure lstrip consumes the entire string
  * Support posix_fallocate and posix_fadvise, expose them on PyPy3.5
  * Test and fix for int_and() propagating wrong bounds
  * Improve the generated machine code by tracking the (constant) value of
    r11 across intructions.  This lets us avoid reloading r11 with another
    (apparently slowish) "movabs" instruction, replacing it with either
    nothing or a cheaper variant.
  * Performance tweaks in the x86 JIT-generated machine code: rarely taken
    blocks are moved off-line.  Also, the temporary register used to contain
    large constants is reused across instructions. This helps CPUs branch
    predictor

.. _here: http://rpython.readthedocs.io/en/latest/cpython_differences.html

Highlights of the PyPy3.5 release (since 5.7 beta released March 2017)
======================================================================

* New features

  * Implement main part of PEP 489 (multi-phase extension module initialization)
  * Add docstrings to various modules and functions

* Bug Fixes

  * Fix inconsistencies in the xml.etree.ElementTree.Element class, which on
    CPython is hidden by the C version from '_elementree'.
  * OSError(None,None) is different from OSError()
  * Get closer to supporting 32 bit windows, translation now succeeds and most
    lib-python/3/test runs

* Performance improvements:

  * Use "<python> -m test" to run the CPython test suite, as documented by CPython,
    instead of our outdated regrverbose.py script
  * Change _cffi_src/openssl/callbacks.py to stop relying on the CPython C API.

* The following features of Python 3.5 are not implemented yet in PyPy:

  * PEP 442: Safe object finalization

.. _resolved: whatsnew-pypy2-5.8.0.html

Please update, and continue to help us make PyPy better.

Cheers
