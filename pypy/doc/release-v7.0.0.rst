===========================================
PyPy2.7, PyPy3.5. PyPy3.6alpha v7.0 release
===========================================

The PyPy team is proud to release PyPy2.7 (supporting Python 2.7 syntax),
PyPy3.5 (supporting Python 3.5 syntax with f-strings from 3.6), and our first
alpha release of PyPy3.6 for 64-bit linux only (supporting Python 3.6 syntax).
The releases are based on much the same codebase.

This release is a feature release following our previous 6.0 release in April
2018. Our C-API compatibility layer ``cpyext`` is more mature, as more projects
use PyPy3.5 in their CI testing. Since these changes affect the included python
development header files, all c-extension modules must be recompiled for this
version.

Until we can work with downstream providers to distribute builds with PyPy, we
have made packages for some common packages `available as wheels`_.

The GC now has `hooks`_ to gain more insights into its performance, and it is
now possible to manually manage the GC by using a combination of
``gc.disable`` and ``gc.collect_step``. See the `GC blog post`_.


We updated the `cffi`_ module included in PyPy to version 1.12, and the
`cppyy`_ backend to 1.4. Please use these to wrap your C and C++ code,
respectively, for a JIT friendly experience.

As always, this release is 100% compatible with the previous one and fixed
several issues and bugs raised by the growing community of PyPy users.
We strongly recommend updating.

The PyPy3.6 release and the Windows PyPy3.5 release are still not production
quality so your mileage may vary. There are open issues with incomplete
compatibility and c-extension support.

The utf8 branch that changes internal representation of unicode to utf8 did not
make it into the release, so there is still more goodness coming.

You can download the v7.0 releases here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
direct consulting work.

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: `PyPy`_
and `RPython`_ documentation improvements, tweaking popular `modules`_ to run
on pypy, or general `help`_ with making RPython's JIT even better.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _`cffi`: http://cffi.readthedocs.io
.. _`cppyy`: https://cppyy.readthedocs.io
.. _`available as wheels`: https://github.com/antocuni/pypy-wheels
.. _`GC blog post`: https://morepypy.blogspot.com/2019/01/pypy-for-low-latency-systems.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7, 3.5 and 3.6. It's fast (`PyPy and CPython 2.7.x`_ performance comparison)
due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

The PyPy release supports:

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 32 bits, OpenBSD, FreeBSD)

  * newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux,

  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://rpython.readthedocs.io/en/latest/examples.html

Changelog
=========

If not specified, the changes are shared across versions

* Support ``__set_name__``, ``__init_subclass__`` (Py3.6)
* Support ``cppyy`` in Py3.5 and Py3.6
* Use implementation-specific site directories in ``sysconfig`` (Py3.5, Py3.6)
* Adding detection of gcc to ``sysconfig`` (Py3.5, Py3.6)
* Fix multiprocessing regression on newer glibcs
* Make sure 'blocking-ness' of socket is set along with default timeout
* Include ``crypt.h`` for ``crypt()`` on Linux
* Improve and re-organize the contributing_ documentation
* Make the ``__module__`` attribute writable, fixing an incompatibility with
  NumPy 1.16
* Implement ``Py_ReprEnter``, ``Py_ReprLeave(), ``PyMarshal_ReadObjectFromString``,
  ``PyMarshal_WriteObjectToString``, ``PyObject_DelItemString``,
  ``PyMapping_DelItem``, ``PyMapping_DelItemString``, ``PyEval_GetFrame``,
  ``PyOS_InputHook``, ``PyErr_FormatFromCause`` (Py3.6),
* Implement new wordcode instruction encoding (Py3.6)
* Log additional gc-minor and gc-collect-step info in the PYPYLOG
* Set ``reverse-debugger`` active by default. For more information, see
  https://bitbucket.org/pypy/revdb
* Support underscores in numerical literals like ``'4_2'`` (Py3.6)
* Pre-emptively raise MemoryError if the size of dequeue in ``_collections.deque``
  is too large (Py3.5)
* Fix multithreading issues in calls to ``os.setenv``
* Add missing defines and typedefs for numpy and pandas on MSVC
* Add CPython macros like ``Py_NAN`` to header files
* Rename the ``MethodType`` to ``instancemethod``, like CPython
* Better support for `async with` in generators (Py3.5, Py3.6)
* Improve the performance of ``pow(a, b, c)`` if ``c`` is a large integer
* Now ``vmprof`` works on FreeBSD
* Support GNU Hurd, fixes for FreeBSD
* Add deprecation warning if type of result of ``__float__`` is float inherited
  class (Py3.6)
* Fix async generator bug when yielding a ``StopIteration`` (Py3.6)
* Speed up ``max(list-of-int)`` from non-jitted code
* Fix Windows ``os.listdir()`` for some cases (see CPython #32539)
* Add ``select.PIPE_BUF``
* Use ``subprocess`` to avoid shell injection in ``shutil`` module
* Rename ``_Py_ZeroStruct`` to ``_Py_FalseStruct`` (Py3.5, Py3.6)
* Remove some cpyext names for Py3.5, Py3.6
* Enable use of unicode file names in ``dlopen``
* Backport CPython fix for ``thread.RLock``
* Make GC hooks measure time in seconds (as opposed to an opaque unit)
* Refactor and reorganize tests in ``test_lib_pypy``
* Check error values in ``socket.setblocking`` (Py3.6)
* Add support for FsPath to os.unlink() (Py3.6)
* Fix freezing builtin modules at translation
* Tweak ``W_UnicodeDictionaryStrategy`` which speeds up dictionaries with only
  unicode keys

We also refactored many parts of the JIT bridge optimizations, as well as cpyext
internals, and together with new contributors fixed issues, added new
documentation, and cleaned up the codebase.

.. _contributing: http://doc.pypy.org/en/latest/contributing.html
