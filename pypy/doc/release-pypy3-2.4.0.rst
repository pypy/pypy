=================================================
PyPy3 2.4 - Snow White
=================================================

We're pleased to announce PyPy3 2.4, which contains significant performance
enhancements and bug fixes.

You can download the PyPy3 2.4.0 release here:

    https://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project, and for those who donate to our three sub-projects.
We've shown quite a bit of progress, but we're slowly running out of funds.
Please consider donating more, or even better convince your employer to donate,
so we can finish those projects! The three sub-projects are:

* `Py3k`_ (supporting Python 3.x): This is a Python 3.2.5 compatible
   version we call PyPy3 2.4, and we are working toward a Python 3.3
   compatible version

* `STM`_ (software transactional memory): We have released a first working version,
  and continue to try out new promising paths of achieving a fast multithreaded Python

* `NumPy`_ which requires installation of our fork of upstream numpy,
  available `on bitbucket`_

.. _`Py3k`: https://pypy.org/py3donate.html
.. _`STM`: https://pypy.org/tmdonate2.html
.. _`NumPy`: https://pypy.org/numpydonate.html
.. _`on bitbucket`: https://www.bitbucket.org/pypy/numpy

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7 or 3.2.5. It's fast (`pypy 2.4 and cpython 2.7.x`_ performance
comparison) due to its integrated tracing JIT compiler.

This release supports **x86** machines on most common operating systems
(Linux 32/64, Mac OS X 64, Windows, and OpenBSD),
as well as newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux.

While we support 32 bit python on Windows, work on the native Windows 64
bit python is still stalling, we would welcome a volunteer
to `handle that`_.

.. _`pypy 2.4 and cpython 2.7.x`: https://speed.pypy.org
.. _`handle that`: https://doc.pypy.org/en/latest/windows.html#what-is-missing-for-a-full-64-bit-translation

PyPy3 Highlights
================

Issues reported with our previous release were fixed after reports from users on
our new issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
#pypy. Here is a summary of the user-facing PyPy3 specific changes:

* Better Windows compatibility, e.g. the nt module functions _getfinalpathname
  & _getfileinformation are now supported (the former is required for the
  popular pathlib library for example)

* Various fsencode PEP 383 related fixes to the posix module (readlink, uname,
  ttyname and ctermid) and improved locale handling

* Switched default binary name os POSIX distributions to 'pypy3' (which
  symlinks to to 'pypy3.2')

* Fixed a couple different crashes related to parsing Python 3 source code

Further Highlights (shared w/ PyPy2)
====================================

Benchmarks improved after internal enhancements in string and
bytearray handling, and a major rewrite of the GIL handling. This means
that external calls are now a lot faster, especially the CFFI ones. It also
means better performance in a lot of corner cases with handling strings or
bytearrays. The main bugfix is handling of many socket objects in your
program which in the long run used to "leak" memory.

We fixed a memory leak in IO in the sandbox_ code

We welcomed more than 12 new contributors, and conducted two Google
Summer of Code projects, as well as other student projects not
directly related to Summer of Code.

* Reduced internal copying of bytearray operations

* Tweak the internal structure of StringBuilder to speed up large string
  handling, which becomes advantageous on large programs at the cost of slightly
  slower small *benchmark* type programs.

* Boost performance of thread-local variables in both unjitted and jitted code,
  this mostly affects errno handling on linux, which makes external calls
  faster.

* Move to a mixed polling and mutex GIL model that make multithreaded jitted
  code run *much* faster

* Optimize errno handling in linux (x86 and x86-64 only)

* Remove ctypes pythonapi and ctypes.PyDLL, which never worked on PyPy

* Classes in the ast module are now distinct from structures used by
  the compiler, which simplifies and speeds up translation of our
  source code to the PyPy binary interpreter

* Win32 now links statically to zlib, expat, bzip, and openssl-1.0.1i.
  No more missing DLLs

* Many issues were resolved_ since the 2.3.1 release in June

.. _`whats-new`: https://doc.pypy.org/en/latest/whatsnew-2.4.0.html
.. _resolved: https://bitbucket.org/pypy/pypy/issues?status=resolved
.. _sandbox: https://doc.pypy.org/en/latest/sandbox.html

We have further improvements on the way: rpython file handling,
numpy linalg compatibility, as well
as improved GC and many smaller improvements.

Please try it out and let us know what you think. We especially welcome
success stories, we know you are using PyPy, please tell us about it!

Cheers

The PyPy Team

