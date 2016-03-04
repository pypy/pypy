==========
PyPy 5.0.0
==========

We have released PyPy 5.0.0, about three months after PyPy 4.0.0. 
We encourage all users of PyPy to update to this version. There are 
bug fixes and a major upgrade to our c-api layer (cpyext)

You can download the PyPy 5.0.0 release here:

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
contribution to the python ecosystem. PyPy 5.0.0 ships with 
`cffi-1.5.2`_ which now allows embedding PyPy (or cpython) in a c program.

.. _`PyPy`: http://doc.pypy.org 
.. _`RPython`: https://rpython.readthedocs.org
.. _`cffi`: https://cffi.readthedocs.org
.. _`cffi-1.5.2`: http://cffi.readthedocs.org/en/latest/whatsnew.html#v1-5-2
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
(Linux 32/64, Mac OS X 64, Windows 32, OpenBSD, freebsd),
newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux, and the
big- and little-endian variants of **ppc64** running Linux.

.. _`pypy and cpython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://pypyjs.org

Other Highlights (since 4.0.1 released in November 2015)
=======================================================

* Bug Fixes

  * 

  * 

  * 

  * Issues reported with our previous release were resolved_ after reports from users on
    our issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
    #pypy

* New features:

  * 

  * 

  * 

* Numpy:

  * 

  * 


* Performance improvements and refactorings:

  * 

  * 

  * 

.. _resolved: http://doc.pypy.org/en/latest/whatsnew-5.0.0.html

Please update, and continue to help us make PyPy better.

Cheers

The PyPy Team

