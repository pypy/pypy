============
PyPy 15.11.0
============

We're pleased and proud to unleash PyPy 15.11, a major update of the PyPy
python2.7.10 compatible interpreter with a Just In Time compiler.
We have improved `warmup time and memory overhead used for tracing`_, added
`vectorization`_ for numpy and general loops where possible on x86 hardware,
refactored rough edges in rpython, and increased functionality of numpy.

Vectorization
=============

Richard Plangger began work in March and continued over a Google Summer of Code
to add a optimization step to the trace optimizer. The step recognizes common
constructs and emits SIMD code where possible, much as any modern compiler does.
This vectorization happens while tracing running code,  so it is actually easier
at run-time to determine the
availability of possible vectorization than it is for ahead-of-time compilers.

Availability of SIMD hardware is detected at run time, without needing to
precompile various code paths into the executable.

Internal Refactoring and Warmup Time Improvement
================================================

Maciej Fijalkowski and Armin Rigo refactored internals of rpython that now allow
PyPy to more efficiently use `guards`_ in jitted code. They also rewrote unrolling,
leading to a warmup time improvement of 20% or so at the cost of a minor
regression in jitted code speed.

.. _`warmup time and memory overhead used for tracing`: http://morepypy.blogspot.com/2015/10
.. _`vectorization`: http://pypyvecopt.blogspot.co.at/
.. _`guards`: http://rpython.readthedocs.org/en/latest/glossary.html

You can download the PyPy 15.11 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project, and our volunteers and contributors.  

We would also like to thank our contributors (7 new ones since PyPy 2.6.0) and 
encourage new people to join the project. PyPy has many
layers and we need help with all of them: `PyPy`_ and `RPython`_ documentation
improvements, tweaking popular `modules`_ to run on pypy, or general `help`_ 
with making RPython's JIT even better. 

.. _`PyPy`: http://doc.pypy.org 
.. _`RPython`: https://rpython.readthedocs.org
.. _`modules`: http://doc.pypy.org/en/latest/project-ideas.html#make-more-python-modules-pypy-friendly
.. _`help`: http://doc.pypy.org/en/latest/project-ideas.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`pypy and cpython 2.7.x`_ performance comparison)
due to its integrated tracing JIT compiler.

This release supports **x86** machines on most common operating systems
(Linux 32/64, Mac OS X 64, Windows 32, OpenBSD_, freebsd_),
as well as newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux.

We also welcome developers of other
`dynamic languages`_ to see what RPython can do for them.

.. _`pypy and cpython 2.7.x`: http://speed.pypy.org
.. _OpenBSD: http://cvsweb.openbsd.org/cgi-bin/cvsweb/ports/lang/pypy
.. _freebsd: https://svnweb.freebsd.org/ports/head/lang/pypy/
.. _`dynamic languages`: http://pypyjs.org

Highlights (since 2.6.1 release two months ago)
===============================================

* Bug Fixes

  * Applied OPENBSD downstream fixes

  * Fix a crash on non-linux when running more than 20 threads

  * In cffi, ffi.new_handle() is more cpython compliant

  * Issues reported with our previous release were resolved_ after reports from users on
    our issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
    #pypy

* New features:

  * Add an optimization pass to vectorize loops using x86 SIMD intrinsics.

  * Support __stdcall on Windows in CFFI

* Numpy:

  * Add support for ndarray.ctypes

  * Fast path for mixing numpy scalars and floats

  * Add support for creating Fortran-ordered ndarrays

  * Fix casting failures in linalg (by extending ufunc casting)

* Performance improvements:

  * Reuse hashed keys across dictionaries and sets

  * Refactor JIT interals to improve warmup time by 20% or so at the cost of a
    minor regression in JIT speed

  * Recognize patterns of common sequences in the JIT backends and optimize them

  * Make the garbage collecter more intcremental over external_malloc() calls

  * Share guard resume data where possible which reduces memory usage

.. _`vmprof`: https://vmprof.readthedocs.org
.. _resolved: http://doc.pypy.org/en/latest/whatsnew-15.11.0.html

Please try it out and let us know what you think. We welcome feedback,
we know you are using PyPy, please tell us about it!

Cheers

The PyPy Team

