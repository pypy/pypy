==========
PyPy 2.6.1 
==========

We're pleased to announce PyPy 2.6.1, an update to PyPy 2.6.0 released June 1.
We have updated stdlib to 2.7.10, `cffi`_ to version 1.2, extended support for
the new vmprof_ statistical profiler for multiple threads, partially
implemented unicode dtypes in numpy, added support for the axis keyword to
many numpy methods, and in general improved numpy compatability.

You can download the PyPy 2.6.1 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project, and for those who donate to our three sub-projects, as well as our
volunteers and contributors.  

We've shown quite a bit of progress, but we're slowly running out of funds.
Please consider donating more, or even better convince your employer to donate,
so we can finish those projects! The three sub-projects are:

* `Py3k`_ (supporting Python 3.x): We have released a Python 3.2.5 compatible version
  we call PyPy3 2.4.0, and are working toward a Python 3.3 compatible version

* `STM`_ (software transactional memory): We have released a first working version,
  and continue to try out new promising paths of achieving a fast multithreaded Python

* `NumPy`_ which requires installation of our fork of upstream numpy,
  available `on bitbucket`_

.. _`cffi`: https://cffi.readthedocs.org
.. _`Py3k`: http://pypy.org/py3donate.html
.. _`STM`: http://pypy.org/tmdonate2.html
.. _`NumPy`: http://pypy.org/numpydonate.html
.. _`on bitbucket`: https://www.bitbucket.org/pypy/numpy

We would also like to encourage new people to join the project. PyPy has many
layers and we need help with all of them: `PyPy`_ and `RPython`_ documentation
improvements, tweaking popular `modules`_ to run on pypy, or general `help`_ with making
RPython's JIT even better. 

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
(Linux 32/64, Mac OS X 64, Windows, OpenBSD_, freebsd_),
as well as newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux.

While we support 32 bit python on Windows, work on the native Windows 64
bit python is still stalling, we would welcome a volunteer 
to `handle that`_. We also welcome developers with other operating systems or
`dynamic languages`_ to see what RPython can do for them.

.. _`pypy and cpython 2.7.x`: http://speed.pypy.org
.. _OpenBSD: http://cvsweb.openbsd.org/cgi-bin/cvsweb/ports/lang/pypy
.. _freebsd: https://svnweb.freebsd.org/ports/head/lang/pypy/
.. _`handle that`: http://doc.pypy.org/en/latest/windows.html#what-is-missing-for-a-full-64-bit-translation
.. _`dynamic languages`: http://pypyjs.org

Highlights 
===========

* Bug Fixes

  * 

  * 

  * Issues reported with our previous release were resolved_ after reports from users on
    our issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
    #pypy.

* New features:

  * 

* Numpy:

  * 

  * 

* Performance improvements:

  * 

  * 

  * 

  * 

.. _`vmprof`: https://vmprof.readthedocs.org
.. _resolved: http://doc.pypy.org/en/latest/whatsnew-2.6.0.html

Please try it out and let us know what you think. We welcome
success stories, `experiments`_,  or `benchmarks`_, we know you are using PyPy, please tell us about it!

Cheers

The PyPy Team

.. _`experiments`: https://morepypy.blogspot.com/2015/02/experiments-in-pyrlang-with-rpython.html
.. _`benchmarks`: https://mithrandi.net/blog/2015/03/axiom-benchmark-results-on-pypy-2-5-0
