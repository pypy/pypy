========
PyPy 5.1
========

We have released PyPy 5.1, about two months after PyPy 5.0.1.
We encourage all users of PyPy to update to this version. Apart from the usual
bug fixes, there is an ongoing effort to improve the warmup time and memory
usage of JIT-related metadata. 

We now fully support the IBM s390x architecture.

You can download the PyPy 5.1 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project.

We would also like to thank our contributors and
encourage new people to join the project. PyPy has many
layers and we need help with all of them: `PyPy`_ and `RPython`_ documentation
improvements, tweaking popular `modules`_ to run on pypy, or general `help`_
with making RPython's JIT even better.

.. _`PyPy`: http://doc.pypy.org
.. _`RPython`: https://rpython.readthedocs.org
.. _`modules`: http://doc.pypy.org/en/latest/project-ideas.html#make-more-python-modules-pypy-friendly
.. _`help`: http://doc.pypy.org/en/latest/project-ideas.html
.. _`numpy`: https://bitbucket.org/pypy/numpy

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`PyPy and CPython 2.7.x`_ performance comparison)
due to its integrated tracing JIT compiler.

We also welcome developers of other
`dynamic languages`_ to see what RPython can do for them.

This release supports: 

  * **x86** machines on most common operating systems
    (Linux 32/64, Mac OS X 64, Windows 32, OpenBSD, FreeBSD),
  
  * newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux,
  
  * big- and little-endian variants of **PPC64** running Linux,

  * **s960x** running Linux

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://pypyjs.org

Other Highlights (since 5.0.1 released in Febuary 2015)
=========================================================

* New features:

  * 

  * 

  * 

* Bug Fixes

  * 

  * 

  * Issues reported with our previous release were resolved_ after reports from users on
    our issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
    #pypy

* Numpy:

  * 

  * 

* Performance improvements:

  * 

  * 

* Internal refactorings:

  * 

  * 

.. _resolved: http://doc.pypy.org/en/latest/whatsnew-5.0.0.html
.. _`blog post`: http://morepypy.blogspot.com/2016/02/c-api-support-update.html

Please update, and continue to help us make PyPy better.

Cheers

The PyPy Team

