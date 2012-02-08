============================
PyPy 1.8 - business as usual
============================

We're pleased to announce the 1.8 release of PyPy. As became a habit, this
release brings a lot of bugfixes, performance and memory improvements over
the 1.7 release. The main highlight of the release is the introduction of
list strategies which makes homogenous lists more efficient both in terms
of performance and memory. Otherwise it's "business as usual" in the sense
that performance improved roughly 10% on average since the previous release.
You can download the PyPy 1.8 release here:

    http://pypy.org/download.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`pypy 1.8 and cpython 2.7.1`_ performance comparison)
due to its integrated tracing JIT compiler.

This release supports x86 machines running Linux 32/64, Mac OS X 32/64 or
Windows 32. Windows 64 work is ongoing, but not yet natively supported.

.. _`pypy 1.8 and cpython 2.7.1`: http://speed.pypy.org


Highlights
==========

* List strategies. Now lists that contain only ints or only floats should
  be as efficient as storing them in a binary-packed array. It also improves
  the JIT performance in places that use such lists. There are also special
  strategies for unicode and string lists.

* As usual, numerous performance improvements. There are many examples
  of python constructs that now should behave faster; too many to list them.

* Bugfixes and compatibility fixes with CPython.

* Windows fixes.

* NumPy effort progress; for the exact list of things that have been done,
  consult the `numpy status page`_. A tentative list of things that has
  been done:

  * multi dimensional arrays

  * various sizes of dtypes

  * a lot of ufuncs

  * a lot of other minor changes

* Since the last release there was a significant breakthrough in PyPy's
  fundraising. We now have enough funds to work on first stages of `numpypy`_
  and `py3k`_

.. _`numpy status page`: http://buildbot.pypy.org/numpy-status/latest.html
.. _`numpy status update blog report`: http://morepypy.blogspot.com/2012/01/numpypy-status-update.html
.. _`numpypy`: http://pypy.org/numpydonate.html
.. _`py3k`: http://pypy.org/py3donate.html
