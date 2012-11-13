===============
PyPy 2.0 beta 1
===============

We're pleased to announce the 2.0 beta 1 release of PyPy. This release is
not a typical beta, in a sense the stability is the same or better than 1.9
and can be used in production. It does however include a few performance
regressions documented below that don't quite make it 2.0 final.

The main features of this release is ARM processor support and the first
release of CFFI-capable PyPy. It also includes numerous improvements
to the numpy in pypy effort, cpyext and performance.

You can download the PyPy 2.0 beta 1 release here:

    http://pypy.org/download.html 

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`pypy 2.0 beta 1 and cpython 2.7.3`_
performance comparison) due to its integrated tracing JIT compiler.

This release supports x86 machines running Linux 32/64, Mac OS X 64 or
Windows 32. It also supports ARM machines running Linux.
Windows 64 work is still stalling, we would welcome a volunteer
to handle that.

.. XXX link

XXX donors info?

Regressions
===========

Reasons why this is not PyPy 2.0:

* ``ctypes`` fast path is now slower than it used to be. ``ctypes`` in PyPy
  1.9 was either incredibly fast or slower than CPython depending whether
  you hit the fast path or not. Right now it's usually simply slower. We're
  probably going to rewrite ``ctypes`` using ``cffi`` which will make it
  universally faster.

* ``cffi``, while very fast is missing one optimization that will make
  it as fast as a native call from C.

* ``numpypy`` lazy computation was disabled in the sake of simplicity. We should
  reenable this for the final 2.0 release.

Highlights
==========

* ``cffi`` is officially supported by PyPy. You can install it normally by
  using ``pip install cffi`` once you have PyPy installed. Corresponding
  ``0.4`` version of ``cffi`` has been released.

* ARM is not an officially supported processor architecture.
  XXX write down few words here

* This release contains the latest Python standard library 2.7.3 and is fully
  compatible with Python 2.7.3.

* It does not however contain hash randomization, since the solution present
  in CPython is not solving the problem anyway. The reason why can be
  found on the `CPython issue tracker`_.

* ``gc.get_referrers`` is not faster.

* Various numpy improvements. List include:

  * axis argument support in many places

  * full support for fancy indexing

  * ``complex128`` and ``complex64`` dtypes

* `JIT hooks`_ are now powerful tool to introspect the JITting process that
  PyPy performs.

* ``**kwds`` usage is much faster in a typical scenario

* ``long`` builtin type is now as fast as CPython's (from roughly 2x slower)

* Unicodes stored in ``dict``/``set``/``list`` are now faster.

