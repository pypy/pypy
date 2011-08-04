===========================
PyPy 1.6 - faster than ever
===========================

We're pleased to announce the 1.6 release of PyPy. This release brings a lot
of bugfixes and performance improvements over 1.5 as well as improved platform
support for Windows 32bit and OS X 64bit. This version fully supports
Python 2.7.1 (XXX .2?) as well as beta level support for C extensions.
You can download it here:

    http://pypy.org/download.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7.1. It's fast (`pypy 1.5 and cpython 2.6.2`_ performance comparison)
due to its integrated tracing JIT compiler.

Highlights
==========

* Numerous bugfixes

* Numerous performance improvements, overall giving a nice speedups

* JitViewer, first official release (XXX)

* multibyte encoding support (XXX which ones)

* faster ctypes, now jitted

* better handling of memory pressure from raw allocated blocks (arrays)

* some rudimentary numpy support

* JIT support for single floats
