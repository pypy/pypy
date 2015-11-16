==========
PyPy 4.0.1
==========

We have released PyPy 4.0.1, a bux-fix release after PyPy 4.0.1. We have fixed
a few critical bugs in the JIT compiled code, reported by users. We encourage
all users of PyPy to update to this version.


You can download the PyPy 4.0.1 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project.

We would also like to thank our contributors and 
encourage new people to join the project. PyPy has many
layers and we need help with all of them: `PyPy`_ and `RPython`_ documentation
improvements, tweaking popular `modules`_ to run on pypy, or general `help`_ 
with making RPython's JIT even better. 

CFFI
====

While not applicable only to PyPy, `cffi`_ is arguably our most significant
contribution to the python ecosystem. PyPy 4.0.1 ships with 
`cffi-1.3.1`_ with the improvements it brings.

.. _`PyPy`: http://doc.pypy.org 
.. _`RPython`: https://rpython.readthedocs.org
.. _`cffi`: https://cffi.readthedocs.org
.. _`cffi-1.3.1`: http://cffi.readthedocs.org/en/latest/whatsnew.html#v1-3-1
.. _`modules`: http://doc.pypy.org/en/latest/project-ideas.html#make-more-python-modules-pypy-friendly
.. _`help`: http://doc.pypy.org/en/latest/project-ideas.html
.. _`numpy`: https://bitbucket.org/pypy/numpy

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`pypy and cpython 2.7.x`_ performance comparison)
due to its integrated tracing JIT compiler.

We also welcome developers of other
`dynamic languages`_ to see what RPython can do for them.

This release supports **x86** machines on most common operating systems
(Linux 32/64, Mac OS X 64, Windows 32, OpenBSD_, freebsd_),
as well as newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux.

We also introduce `support for the 64 bit PowerPC`_ hardware, specifically 
Linux running the big- and little-endian variants of ppc64.

.. _`pypy and cpython 2.7.x`: http://speed.pypy.org
.. _OpenBSD: http://cvsweb.openbsd.org/cgi-bin/cvsweb/ports/lang/pypy
.. _freebsd: https://svnweb.freebsd.org/ports/head/lang/pypy/
.. _`dynamic languages`: http://pypyjs.org
.. _`support for the 64 bit PowerPC`: http://morepypy.blogspot.com/2015/10/powerpc-backend-for-jit.html
.. _`here`: http://morepypy.blogspot.com/2015/10/automatic-simd-vectorization-support-in.html

Other Highlights (since 4.0.0 released three weeks ago)
=======================================================

* Bug Fixes

  * Fix a bug when unrolling double loops in JITted code

  * Fix multiple memory leaks in the ssl module, one of which affected
    `cpython` as well (thanks to Alex Gaynor for pointing those out)

  * Use pkg-config to find ssl headers on OS-X

  * Issues reported with our previous release were resolved_ after reports from users on
    our issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
    #pypy

* New features:

  * Internal cleanup of RPython class handling

  * Support stackless and greenlets on PPC machines

  * Improve debug logging in subprocesses: use PYPYLOG=jit:log.%d
    for example to have all subprocesses write the JIT log to a file
    called 'log.%d', with '%d' replaced with the subprocess' PID.

  * Support PyOS_double_to_string in our cpyext capi compatibility layer

* Numpy:

  * Improve support for __array_interface__

  * Propogate NAN mantissas through float16-float32-float64 conversions


* Performance improvements and refactorings:

  * Improvements in slicing byte arrays

  * Improvements in enumerate()

  * Silence some warnings while translating

.. _resolved: http://doc.pypy.org/en/latest/whatsnew-4.0.1.html

Please update, and continue to help us make PyPy better.

Cheers

The PyPy Team

