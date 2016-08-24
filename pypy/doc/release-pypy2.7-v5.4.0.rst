============
PyPy2.7 v5.4
============

We have released PyPy2.7 v5.4, a little under two months after PyPy2.7 v5.3.
This new PyPy2.7 release includes further improvements to our C-API compatability layer (cpyext), enabling us to pass over 99% of the upstream
numpy `test suite`_. We updated built-in cffi_ support to version 1.8,
and fixed many issues and bugs raised by the growing community of PyPy
users.

XXXXX MORE ???

You can download the PyPy2.7 v5.4 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project.

We would also like to thank our contributors and
encourage new people to join the project. PyPy has many
layers and we need help with all of them: `PyPy`_ and `RPython`_ documentation
improvements, tweaking popular `modules`_ to run on pypy, or general `help`_
with making RPython's JIT even better.

.. _`test suite`: https://bitbucket.org/pypy/pypy/wiki/Adventures%20in%20cpyext%20compatibility
.. _cffi: https://cffi.readthedocs.org
.. _`PyPy`: http://doc.pypy.org
.. _`RPython`: https://rpython.readthedocs.org
.. _`modules`: http://doc.pypy.org/en/latest/project-ideas.html#make-more-python-modules-pypy-friendly
.. _`help`: http://doc.pypy.org/en/latest/project-ideas.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`PyPy and CPython 2.7.x`_ performance comparison)
due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

This release supports: 

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 32 bits, OpenBSD, FreeBSD)
  
  * newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux,
  
  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://pypyjs.org

Other Highlights (since 5.3 released in June 2016)
=========================================================

* New features:

* Bug Fixes

  * Issues reported with our previous release were resolved_ after
    reports from users on our issue tracker at
    https://bitbucket.org/pypy/pypy/issues or on IRC at #pypy

* Performance improvements:

.. _resolved: http://doc.pypy.org/en/latest/whatsnew-5.3.0.html

Please update, and continue to help us make PyPy better.

Cheers
