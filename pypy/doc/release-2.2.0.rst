=======================================
PyPy 2.2 - Incrementalism
=======================================

We're pleased to announce PyPy 2.2, which targets version 2.7.3 of the Python
language. This release main highlight is the introduction of the incremental
garbage collector, sponsored by the `Raspberry Pi Foundation`_.

This release also contains several bugfixes and performance improvements. 

You can download the PyPy 2.2 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. We showed quite a bit of progress on all three projects (see below)
and we're slowly running out of funds.
Please consider donating more so we can finish those projects!  The three
projects are:

* Py3k (supporting Python 3.x): the release PyPy3 2.2 is imminent.

* STM (software transactional memory): a preview will be released very soon,
  as soon as we fix a few bugs

* NumPy: the work done is included in the PyPy 2.2 release. More details below.

.. _`Raspberry Pi Foundation`: http://www.raspberrypi.org

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`pypy 2.2 and cpython 2.7.2`_ performance comparison)
due to its integrated tracing JIT compiler.

This release supports x86 machines running Linux 32/64, Mac OS X 64, Windows
32, or ARM (ARMv6 or ARMv7, with VFPv3).

Work on the native Windows 64 is still stalling, we would welcome a volunteer
to handle that.

.. _`pypy 2.2 and cpython 2.7.2`: http://speed.pypy.org

Highlights
==========

* Our Garbage Collector is now "incremental".  It should avoid almost
  all pauses due to a major collection taking place.  Previously, it
  would pause the program (rarely) to walk all live objects, which
  could take arbitrarily long if your process is using a whole lot of
  RAM.  Now the same work is done in steps.  This should make PyPy
  more responsive, e.g. in games.  There are still other pauses, from
  the GC and the JIT, but they should be on the order of 5
  milliseconds each.

* The JIT counters for hot code were never reset, which meant that a
  process running for long enough would eventually JIT-compile more
  and more rarely executed code.  Not only is it useless to compile
  such code, but as more compiled code means more memory used, this
  gives the impression of a memory leak.  This has been tentatively
  fixed by decreasing the counters from time to time.

* NumPy has been split: now PyPy only contains the core module, called
  ``_numpypy``.  The ``numpy`` module itself has been moved to
  ``https://bitbucket.org/pypy/numpy``.  You need to install it
  separately in a virtualenv with ``pip install
  git+https://bitbucket.org/pypy/numpy.git``.

* improvements to non-inlined calls

* sys.set_trace is now JITted (think coverage)

* faster json

* improvements in buffer copying

* tk is supported (XXX was already in pypy 2.1 it seems?? maybe not
  correctly packaged?)

* We finally wrote all the missing ``os.xxx()`` functions.  There are
  a lot of strange ones that nobody ever heard about, except those who
  really need them.

* numpy C API


 the core module is included in PyPy 2.2, but you must now install an
  external fork of numpy from https://bitbucket.org/pypy/numpy


removed in favor of an external numpy fork at
https://bitbucket.org/pypy/numpy
