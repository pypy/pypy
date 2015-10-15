============
PyPy 15.11.0
============

We're pleased and proud to unleash PyPy 15.11, a major update of the PyPy python2.7.10
compatible interpreter with a Just In Time compiler.
We have improved warmup time and memory overhead used for tracing, added vectorization
for numpy and general loops where possible on x86 hardware, ...
and increased functionality of numpy.

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

Highlights 
===========

* Bug Fixes

  * ...

  * Issues reported with our previous release were resolved_ after reports from users on
    our issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
    #pypy.

* New features:

  * ...

* Numpy:

  * ...

* Performance improvements:

  * ...

.. _`vmprof`: https://vmprof.readthedocs.org
.. _resolved: http://doc.pypy.org/en/latest/whatsnew-15.11.0.html

Please try it out and let us know what you think. We welcome feedback,
we know you are using PyPy, please tell us about it!

Cheers

The PyPy Team

