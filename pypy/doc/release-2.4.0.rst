=================================================
PyPy 2.4 - ????????
=================================================

We're pleased to announce PyPy 2.4, a significant milestone on it's own right
and the proud parent of our recent PyPy3 and STM releases.

This release contains several improvements and bugfixes.

You can download the PyPy 2.4 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project, and for those who donate to our three sub-projects.
We've shown quite a bit of progress 
but we're slowly running out of funds.
Please consider donating more, or even better convince your employer to donate,
so we can finish those projects!  The three sub-projects are:

* `Py3k`_ (supporting Python 3.x): We have released a Python 3.2.5 compatable version
   we call PyPy3 2.3.1, and are working toward a Python 3.3 compatable version

* `STM`_ (software transactional memory): We have release a first working version, and
continue to try out new promising paths of acheiving a fast multithreaded python

* `NumPy`_ which requires installation of our fork of upstream numpy, available `on bitbucket`_

.. _`Py3k`: http://pypy.org/py3donate.html
.. _`STM`: http://pypy.org/tmdonate2.html
.. _`NumPy`: http://pypy.org/numpydonate.html
.. _`on bitbucket`: https://www.bitbucket.org/pypy/numpy   

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`pypy 2.3 and cpython 2.7.x`_ performance comparison;
note that cpython's speed has not changed since 2.7.2)
due to its integrated tracing JIT compiler.

This release supports x86 machines running Linux 32/64, Mac OS X 64, Windows,
and OpenBSD,
as well as newer ARM hardware (ARMv6 or ARMv7, with VFPv3) running Linux. 

While we support 32 bit python on Windows, work on the native Windows 64
bit python is still stalling, we would welcome a volunteer
to `handle that`_.

.. _`pypy 2.3 and cpython 2.7.x`: http://speed.pypy.org
.. _`handle that`: http://doc.pypy.org/en/latest/windows.html#what-is-missing-for-a-full-64-bit-translation

Highlights
==========

Benchmarks improved after internal improvements in string and bytearray handling,
and a major rewrite of the GIL handling. Many of these improvements are offshoots
of the STM work.

We merged in Python's 2.7.8 stdlib in a record time of one week, proving the
maturity of our underlying RPython code base and PyPy interpreter.

We welcomed more than 12 new contributors, and conducted two Google Summer of Code
projects XXX details?

Issues reported with our previous release were fixed after reports from users on
our new issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
#pypy. Here is a summary of the user-facing changes;
for more information see `whats-new`_:

* Reduced internal copying of bytearray operations

* Tweak the internal structure of StringBuilder to speed up large string
handling, which becomes advantageous on large programs at the cost of slightly
slower small *benchmark* type programs.

* Boost performance of thread-local variables in both unjitted and jitted code

* Move to a mixed polling and mutex GIL model that make mutli-threaded jitted
  code run *much* faster

* Optimize errno handling in linux

* Remove ctypes pythonapi and ctypes.PyDLL, which never worked on PyPy

* Fix performance regression on ufunc(<scalar>, <scalar>) in numpy

* Classes in the ast module are now distinct from structures used by the compiler,
  which simplifies and speeds up translation of our source code to the PyPy binary
  interpreter

* Upgrade stdlib from 2.7.5 to 2.7.8

* 

* Many issues were resolved_ since the 2.3.1 release on June 8

.. _`whats-new`: http://doc.pypy.org/en/latest/whatsnew-2.3.1.html
.. _resolved: https://bitbucket.org/pypy/pypy/issues?status=resolved

Please try it out and let us know what you think. We especially welcome
success stories, we know you are using PyPy, please tell us about it!

Cheers

The PyPy Team

