====================================
PyPy v7.3.0: release of 2.7, and 3.6
====================================

The PyPy team is proud to release the version 7.3.0 of PyPy, which includes
two different interpreters:

  - PyPy2.7, which is an interpreter supporting the syntax and the features of
    Python 2.7 including the stdlib for CPython 2.7.13

  - PyPy3.6: which is an interpreter supporting the syntax and the features of
    Python 3.6, including the stdlib for CPython 3.6.9.
    
The interpreters are based on much the same codebase, thus the double
release.

We have worked with the python packaging group to support tooling around
building third party packages for python, so this release changes the ABI tag
for PyPy.

The `CFFI`_ backend has been updated to version 1.13.1. We recommend using CFFI
rather than c-extensions to interact with C.

The built-in ``_cppyy`` module was upgraded to 1.10.6, which
provides, among others, better template resolution, stricter ``enum`` handling,
anonymous struct/unions, cmake fragments for distribution, optimizations for
PODs, and faster wrapper calls. We reccomend using cppyy_ for performant
wrapping of C++ code for Python.

The vendored pyrepl package for interaction inside the REPL was updated.

Support for codepage encoding and decoding was added for Windows.

As always, this release fixed several issues and bugs raised by the growing
community of PyPy users.  We strongly recommend updating. Many of the fixes are
the direct result of end-user bug reports, so please continue reporting issues
as they crop up.

You can download the v7.3 releases here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project. If PyPy is not quite good enough for your needs, we are available for
direct consulting work.

We would also like to thank our contributors and encourage new people to join
the project. PyPy has many layers and we need help with all of them: `PyPy`_
and `RPython`_ documentation improvements, tweaking popular modules to run
on pypy, or general `help`_ with making RPython's JIT even better. Since the
previous release, we have accepted contributions from 3 new contributors,
thanks for pitching in.

.. _`PyPy`: index.html
.. _`RPython`: https://rpython.readthedocs.org
.. _`help`: project-ideas.html
.. _`CFFI`: http://cffi.readthedocs.io
.. _`cppyy`: https://cppyy.readthedocs.io
.. _`available as wheels`: https://github.com/antocuni/pypy-wheels

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7, 3.6. It's fast (`PyPy and CPython 2.7.x`_ performance
comparison) due to its integrated tracing JIT compiler.

We also welcome developers of other `dynamic languages`_ to see what RPython
can do for them.

This PyPy release supports:

  * **x86** machines on most common operating systems
    (Linux 32/64 bits, Mac OS X 64 bits, Windows 32 bits, OpenBSD, FreeBSD)

  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

  * 64-bit **ARM** machines running Linux.

Unfortunately at the moment of writing our ARM buildbots are out of service,
so for now we are **not** releasing any binary for the ARM architecture (32
bit), although PyPy does support ARM 32 bit processors. 

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://rpython.readthedocs.io/en/latest/examples.html


Changelog
=========

Changes shared across versions
------------------------------

* Fix segfault when calling descr-methods with no arguments
* Change the SOABI and subsequently change the reported ABI tag.
* Update the builtin ``_cppyy`` backend to 1.10.6
* Performance improvements in string/unicode handling
* Fix compilation error when building `revdb`_ (`issue 3084`_, actually
  released in PyPy 7.2 but not mentioned in the release notes)
* Add JIT options to documentation and an option for JIT help via ``pypy --jit
  help``
* Fix regex escapes in pyrepl (`issue 3097`_)
* Allow reloading of subclasses of module (`issue 3099`_)
* Work around a gcc bug, which was reported to them and fixed (`issue 3086`_)
* Fix (again) faulty logic when decoding invalid UTF-8 (`issue 2389`_)
* Fix up LICENSE file
* Turn all ``http`` links in the documentation to ``https``
* Update the bndled pip and setuptools (used in ``pypy -mensurepip`` to version
  that support `manylinux2010`_ wheels
* Link the ``DEFAULT_SOABI`` to the ``PYPY_VERSION``
* Workaround for programs calling ``sys.setrecursionlimit(huge_value)`` (`issue
  3094`_)
* Set minimal ``MACOSX_DEPLOYMENT_TARGET`` to 10.7 on macOS; cpython uses 10.5
* Fix a JIT bug causing rare register corruption on aarch64
* Add discovery of ``ncursesw`` when building ``_minimal_curses`` and improve
  handling of old curses versions (`issue 2970`_)
* Improve the error message for ``class X(random_object)`` (`issue 3109`_)
* Deal with json dicts containing repeated keys in the new map based parser
  (`issue 3108`_)
* Port parts of the `portable pypy`_ repackaging scripts to add an option for
  ``RPATH`` manipulation on linux
* Check for overflow in ctypes array creation
* Better support and report MSVC versions used to compile on windows
* Allow any kind of buffer in socket.setsockopt(), like CPython (`issue 3114`_)

C-API (cpyext) and c-extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Add ``_PySet_Next``, ``_PySet_NextEntry``
* Correctly swallow exceptions happening inside ``PyDict_GetItem()`` (`issue
  3098`_)
* Respect tp_dict on PyType_Ready (`issue XXX`_)
* Allow calling ``PyType_Ready`` on a subclass with a partially built
  ``tp_base`` (issue 3117`_)
* Rename ``tuple_new`` to ``_PyPy_tuple_new`` to follow the naming convention of
  exported symbols in ``libpypy-c.so``
* Actually restore the traceback in ``PyErr_Restore`` (`issue 3120`_)

Python 3.6 only
---------------

* Don't grow the ``lzma.decompress()`` buffer past ``max_length`` (`issue 3088`_)
* Backport fix from CPython for failure of ``lzma`` to decompress a file
  (`issue 3090`_)
* Fix ``asyncgen_hooks`` and refactor ``coroutine execution``
* Fix range checking in GB18030 decoder (CPython issue `29990`_)
* Fix handling escape characters in HZ codec (CPython issue `30003`_)
* Reject null characters in a few more functions (CPython issue `13617`_)
* Fix build on macOS without ``clock_gettime`` (before 10.12 and xcode 8,
  released 2016)
* Backport 3.7.5 changes to ``timedelta.__eq__`` and ``time.__eq__`` (CPython
  issue `37579`_)
* Backport more fixes to comparisons in ``datetime.py`` (CPython issue `37985`_)
* Use the python tag in ``pyc`` file names, not the abi tag
* Handle string formatting with a single ``[`` in the format string (`issue
  3100`_)
* Backport some of the patches in `macports pypy`_
* Add missing ``HAVE_FACCESSAT`` to ``posix._have_functions``
* Update pyrepl from upstream package (`issue 2971`_)
* Fix ``PyFrame._guess_function_name_parens()``
* Fix range of allowed years in ``time.mktime`` to match CPython `13312`_
* Generators need to store the old current ``exc_info`` in a place that is
  visible, because in one corner case a call to ``sys.exc_info()`` might need
  it.  (`issue 3096`_)
* Remove incorrect clobbering of the ``locals`` after running ``exec()``
* Adds encoding, decoding codepages on win32

Python 3.6 C-API
~~~~~~~~~~~~~~~~

* Add ``PyObject_GenericGetDict``, ``PyObject_GenericSetDict``, ``_Py_strhex``,
  ``_Py_strhex_bytes``, ``PyUnicodeNew``, ``_PyFinalizing``,
  ``PySlice_Unpack``, ``PySlice_AdjustIndices``
* Implement ``pystrhex.h`` (`issue 2687`_)
* Make ``PyUnicodeObject`` slightly more compact
* Fix memory leak when releasing a ``PyUnicodeObject``

.. _`revdb`: fix broken link
.. _`portable pypy`: fix broken link
.. _`manylinux2010`: fix broken link
.. _`macports pypy`: https://github.com/macports/macports-ports/blob/master/lang/pypy/files/darwin.py.diff

.. _`issue 2389`: https://bitbucket.com/pypy/pypy/issues/2389
.. _`issue 2687`: https://bitbucket.com/pypy/pypy/issues/2687
.. _`issue 2970`: https://bitbucket.com/pypy/pypy/issues/2970
.. _`issue 2971`: https://bitbucket.com/pypy/pypy/issues/2971
.. _`issue 3084`: https://bitbucket.com/pypy/pypy/issues/3084
.. _`issue 3086`: https://bitbucket.com/pypy/pypy/issues/3086
.. _`issue 3088`: https://bitbucket.com/pypy/pypy/issues/3088
.. _`issue 3090`: https://bitbucket.com/pypy/pypy/issues/3090
.. _`issue 3094`: https://bitbucket.com/pypy/pypy/issues/3094
.. _`issue 3096`: https://bitbucket.com/pypy/pypy/issues/3096
.. _`issue 3097`: https://bitbucket.com/pypy/pypy/issues/3097
.. _`issue 3098`: https://bitbucket.com/pypy/pypy/issues/3098
.. _`issue 3099`: https://bitbucket.com/pypy/pypy/issues/3099
.. _`issue 3100`: https://bitbucket.com/pypy/pypy/issues/3100
.. _`issue 3108`: https://bitbucket.com/pypy/pypy/issues/3108
.. _`issue 3109`: https://bitbucket.com/pypy/pypy/issues/3109
.. _`issue 3114`: https://bitbucket.com/pypy/pypy/issues/3114
.. _`issue 3117`: https://bitbucket.com/pypy/pypy/issues/3117
.. _`issue 3120`: https://bitbucket.com/pypy/pypy/issues/3120

.. _13312: https://bugs.python.org/issue13312
.. _13617: https://bugs.python.org/issue13617
.. _29990: https://bugs.python.org/issue29990
.. _30003: https://bugs.python.org/issue30003
.. _37579: https://bugs.python.org/issue37579
.. _37985: https://bugs.python.org/issue37985
.. _37985: https://bugs.python.org/issue37985


