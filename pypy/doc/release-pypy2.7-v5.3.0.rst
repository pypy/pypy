============
PyPy2.7 v5.3
============

We have released PyPy2.7 v5.3, about six weeks after PyPy 5.1. 
This release includes further improvements for the CAPI compatibility layer
which we call cpyext. In addtion to complete support for lxml, we now pass
most (more than 90%) of the upstream numpy test suite, and much of SciPy is
supported as well.

We also improved the speed of ... and ...

We updated cffi_ to ...

You can download the PyPy2.7 v5.3 release here:

    http://pypy.org/download.html

We would like to thank our donors for the continued support of the PyPy
project.

We would also like to thank our contributors and
encourage new people to join the project. PyPy has many
layers and we need help with all of them: `PyPy`_ and `RPython`_ documentation
improvements, tweaking popular `modules`_ to run on pypy, or general `help`_
with making RPython's JIT even better.

.. _`PyPy`: http://doc.pypy.org
.. _`RPython`: https://rpython.readthedocs.org
.. _`modules`: http://doc.pypy.org/en/latest/project-ideas.html#make-more-python-modules-pypy-friendly
.. _`help`: http://doc.pypy.org/en/latest/project-ideas.html
.. _`numpy`: https://bitbucket.org/pypy/numpy
.. _cffi: https://cffi.readthedocs.org
.. _`fully support for the IBM s390x`: http://morepypy.blogspot.com/2016/04/pypy-enterprise-edition.html
.. _`blog post`: http://morepypy.blogspot.com/2016/04/warmup-improvements-more-efficient.html

What is PyPy?
=============

PyPy is a very compliant Python interpreter, almost a drop-in replacement for
CPython 2.7. It's fast (`PyPy and CPython 2.7.x`_ performance comparison)
due to its integrated tracing JIT compiler.

We also welcome developers of other
`dynamic languages`_ to see what RPython can do for them.

This release supports: 

  * **x86** machines on most common operating systems
    (Linux 32/64, Mac OS X 64, Windows 32, OpenBSD, FreeBSD),
  
  * newer **ARM** hardware (ARMv6 or ARMv7, with VFPv3) running Linux,
  
  * big- and little-endian variants of **PPC64** running Linux,

  * **s390x** running Linux

.. _`PyPy and CPython 2.7.x`: http://speed.pypy.org
.. _`dynamic languages`: http://pypyjs.org

Other Highlights (since 5.1 released in April 2016)
=========================================================

* New features:

  * Merge a major expansion of the C-API support in cpyext, here are some of
    the highlights:
      - allow c-snippet tests to be run with -A so we can verify we are compatible
      - fix many edge cases exposed by fixing tests to run with -A
      - issequence() logic matches cpython
      - make PyStringObject and PyUnicodeObject field names compatible with cpython
      - add prelminary support for PyDateTime_*
      - support PyComplexObject, PyFloatObject, PyDict_Merge, PyDictProxy,
        PyMemoryView_*, _Py_HashDouble, PyFile_AsFile, PyFile_FromFile,
      - PyAnySet_CheckExact, PyUnicode_Concat
      - improve support for PyGILState_Ensure, PyGILState_Release, and thread
        primitives, also find a case where CPython will allow thread creation
        before PyEval_InitThreads is run, dissallow on PyPy 
      - create a PyObject-specific list strategy
      - rewrite slot assignment for typeobjects
      - improve tracking of PyObject to rpython object mapping
      - support tp_as_{number, sequence, mapping, buffer} slots

  * CPyExt tweak: instead of "GIL not held when a CPython C extension module
    calls PyXxx", we now silently acquire/release the GIL.  Helps with
    CPython C extension modules that call some PyXxx() functions without
    holding the GIL (arguably, they are theorically buggy).

  * Add rgc.FinalizerQueue, documented in pypy/doc/discussion/finalizer-order.rst.
    It is a more flexible way to make RPython finalizers. Use this mechanism to
    clean up handling of ``__del__`` methods, fixing issue #2287

  * Generalize cpyext old-style buffers to more than just str/buffer, add
    support for mmap

* Bug Fixes

  * Issues reported with our previous release were resolved_ after reports from users on
    our issue tracker at https://bitbucket.org/pypy/pypy/issues or on IRC at
    #pypy

* Numpy_:

  * Implement ufunc.outer on numpypy

* Performance improvements:

  * Use bitstrings to compress lists of descriptors that are attached to an
    EffectInfo

  * Remove most of the _ovf, _zer and _val operations from RPython.  Kills
    quite some code internally, and allows the JIT to do better
    optimizations: for example, app-level code like ``x / 2`` or ``x % 2``
    can now be turned into ``x >> 1`` or ``x & 1``, even if x is possibly
    negative.


* Internal refactorings:

  * Reduce the size of generated C sources during translation by 
    refactoring function declarations

  * Remove a number of translation-time options that were not tested and
    never used. Also fix a performance bug in the method cache

  * Reduce the size of generated code by using the same function objects in
    all generated subclasses

  * Compile c snippets with -Werror, and fix warnings it exposed

.. _resolved: http://doc.pypy.org/en/latest/whatsnew-5.3.0.html
.. _Numpy: https://bitbucket.org/pypy/numpy

Please update, and continue to help us make PyPy better.

Cheers

The PyPy Team

